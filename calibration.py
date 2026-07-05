import threading
import io
import os
import subprocess
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image, ImageDraw

CONFIG_FILE = "config_device.json"
WEB_PORT = 8765


def _clamp(value, lower, upper):
    return max(lower, min(value, upper))


def _baca_int(prompt, default=None, lower=None, upper=None):
    while True:
        nilai = input(prompt).strip()

        if not nilai and default is not None:
            return default

        try:
            angka = int(nilai)
        except ValueError:
            print("❌ Masukkan angka bulat yang valid.")
            continue

        if lower is not None and angka < lower:
            print(f"❌ Nilai minimal {lower}.")
            continue

        if upper is not None and angka > upper:
            print(f"❌ Nilai maksimal {upper}.")
            continue

        return angka


def _normalisasi_crop_box(left, top, right, bottom, width, height):
    left = _clamp(left, 0, width - 1)
    top = _clamp(top, 0, height - 1)
    right = _clamp(right, left + 1, width)
    bottom = _clamp(bottom, top + 1, height)
    return [left, top, right, bottom]


def _profil_default_calibration(width, height):
    if width == 1220 and height == 2712:
        return {
            "click_x": 610,
            "click_y": 759,
            "crop_box": [150, 495, 1050, 655],
        }

    return {
        "click_x": int(width * 0.5),
        "click_y": int(height * 0.28),
        "crop_box": _normalisasi_crop_box(
            int(width * 0.08),
            int(height * 0.13),
            int(width * 0.92),
            int(height * 0.35),
            width,
            height,
        ),
    }


def _simpan_preview(img, crop_box, prefix="calib"):
    cropped = img.crop(tuple(crop_box))
    cropped.save(f"{prefix}_crop.png")

    preview = img.copy()
    draw = ImageDraw.Draw(preview)
    draw.rectangle(tuple(crop_box), outline="red", width=6)
    preview.save(f"{prefix}_overlay.png")


def _interactive_adjust_crop(img, crop_box, width, height):
    while True:
        _simpan_preview(img, crop_box, "test")

        print("\n[!] File 'test_crop.png' dan 'test_overlay.png' sudah dibuat.")
        print("[!] Buka overlay untuk cek posisi crop, lalu sesuaikan jika belum pas.")
        print(f"[!] Crop saat ini: {crop_box}")

        aksi = input(
            "Pilih aksi: [y] simpan, [w] atas, [s] bawah, [a] kiri, [d] kanan, [i] kecilkan, [o] besarkan: "
        ).strip().lower()

        if aksi == "y":
            return crop_box

        step_x = max(5, width // 60)
        step_y = max(5, height // 60)

        if aksi == "w":
            crop_box[1] = _clamp(crop_box[1] - step_y, 0, height - 1)
            crop_box[3] = _clamp(crop_box[3] - step_y, crop_box[1] + 1, height)
        elif aksi == "s":
            crop_box[1] = _clamp(crop_box[1] + step_y, 0, height - 1)
            crop_box[3] = _clamp(crop_box[3] + step_y, crop_box[1] + 1, height)
        elif aksi == "a":
            crop_box[0] = _clamp(crop_box[0] - step_x, 0, width - 1)
            crop_box[2] = _clamp(crop_box[2] - step_x, crop_box[0] + 1, width)
        elif aksi == "d":
            crop_box[0] = _clamp(crop_box[0] + step_x, 0, width - 1)
            crop_box[2] = _clamp(crop_box[2] + step_x, crop_box[0] + 1, width)
        elif aksi == "i":
            crop_box[0] = _clamp(crop_box[0] + step_x, 0, width - 1)
            crop_box[1] = _clamp(crop_box[1] + step_y, 0, height - 1)
            crop_box[2] = _clamp(crop_box[2] - step_x, crop_box[0] + 1, width)
            crop_box[3] = _clamp(crop_box[3] - step_y, crop_box[1] + 1, height)
        elif aksi == "o":
            crop_box[0] = _clamp(crop_box[0] - step_x, 0, width - 1)
            crop_box[1] = _clamp(crop_box[1] - step_y, 0, height - 1)
            crop_box[2] = _clamp(crop_box[2] + step_x, crop_box[0] + 1, width)
            crop_box[3] = _clamp(crop_box[3] + step_y, crop_box[1] + 1, height)
        else:
            print("❌ Aksi tidak dikenal. Coba lagi.")

        crop_box = _normalisasi_crop_box(crop_box[0], crop_box[1], crop_box[2], crop_box[3], width, height)


def _build_preview_png(image_path, max_width=920):
    with Image.open(image_path) as image:
        if image.width > max_width:
            new_height = int(image.height * max_width / image.width)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue(), image.size


def _build_web_html(width, height, defaults):
        defaults_json = json.dumps(defaults)
        return f"""<!doctype html>
<html lang="id">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Calibration Crop UI</title>
    <style>
        :root {{
            color-scheme: dark;
            --bg: #0f1115;
            --panel: #161a22;
            --border: #2b3240;
            --text: #e7ebf3;
            --muted: #9aa4b2;
            --accent: #ff4d4f;
            --accent-soft: rgba(255, 77, 79, 0.14);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: Segoe UI, Arial, sans-serif;
            background: radial-gradient(circle at top, #1a1f2a, var(--bg));
            color: var(--text);
        }}
        .wrap {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .card {{
            background: rgba(22, 26, 34, 0.94);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 18px;
            box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
        }}
        h1 {{ margin: 0 0 8px; font-size: 24px; }}
        p {{ margin: 6px 0 0; color: var(--muted); }}
        .layout {{
            display: grid;
            gap: 18px;
            grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.8fr);
            align-items: start;
            margin-top: 18px;
        }}
        .preview {{
            position: relative;
            display: inline-block;
            width: 100%;
            overflow: hidden;
            border-radius: 16px;
            border: 1px solid var(--border);
            background: #0b0d12;
        }}
        .preview img {{
            display: block;
            width: 100%;
            height: auto;
            user-select: none;
            -webkit-user-drag: none;
        }}
        #overlay {{
            position: absolute;
            border: 3px solid var(--accent);
            background: var(--accent-soft);
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.28);
            pointer-events: none;
            border-radius: 8px;
        }}
        .controls {{
            display: grid;
            gap: 12px;
        }}
        .group {{
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 14px;
            background: rgba(12, 15, 20, 0.5);
        }}
        .group h2 {{
            margin: 0 0 10px;
            font-size: 16px;
        }}
        .field {{ margin-bottom: 12px; }}
        .field:last-child {{ margin-bottom: 0; }}
        .field label {{
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: var(--muted);
            margin-bottom: 6px;
        }}
        input[type="range"] {{ width: 100%; }}
        input[type="number"] {{
            width: 100%;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: #0f131b;
            color: var(--text);
        }}
        .row {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }}
        .actions {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}
        button {{
            padding: 10px 14px;
            border: 0;
            border-radius: 10px;
            background: var(--accent);
            color: white;
            font-weight: 700;
            cursor: pointer;
        }}
        button.secondary {{ background: #2d3442; }}
        .status {{
            margin-top: 10px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
            white-space: pre-line;
        }}
        .meta {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 10px;
            font-size: 13px;
            color: var(--muted);
        }}
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 10px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
        }}
        @media (max-width: 980px) {{
            .layout {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <div class="card">
            <h1>Interactive Crop Calibration</h1>
            <p>Geser batas crop sampai area angka 4 digit pas. Setelah itu klik Simpan.</p>

            <div class="layout">
                <div>
                    <div class="preview">
                        <img id="shot" src="/shot.png" alt="Screenshot calibration" />
                        <div id="overlay"></div>
                    </div>
                    <div class="meta">
                        <div class="pill">Resolusi: <span id="metaResolution">__WIDTH__x__HEIGHT__</span></div>
                        <div class="pill">Crop: <span id="metaCrop"></span></div>
                    </div>
                </div>

                <div class="controls">
                    <div class="group">
                        <h2>Crop Box</h2>
                        <div class="field">
                            <label><span>Kiri</span><span id="leftValue"></span></label>
                            <input id="leftRange" type="range" min="0" max="__WIDTH__" step="1" />
                        </div>
                        <div class="field">
                            <label><span>Atas</span><span id="topValue"></span></label>
                            <input id="topRange" type="range" min="0" max="__HEIGHT__" step="1" />
                        </div>
                        <div class="field">
                            <label><span>Kanan</span><span id="rightValue"></span></label>
                            <input id="rightRange" type="range" min="0" max="__WIDTH__" step="1" />
                        </div>
                        <div class="field">
                            <label><span>Bawah</span><span id="bottomValue"></span></label>
                            <input id="bottomRange" type="range" min="0" max="__HEIGHT__" step="1" />
                        </div>
                    </div>

                    <div class="group">
                        <h2>Tap Refresh</h2>
                        <div class="row">
                            <div class="field">
                                <label><span>X</span></label>
                                <input id="clickX" type="number" min="0" max="__WIDTH__" step="1" />
                            </div>
                            <div class="field">
                                <label><span>Y</span></label>
                                <input id="clickY" type="number" min="0" max="__HEIGHT__" step="1" />
                            </div>
                        </div>
                    </div>

                    <div class="group">
                        <div class="actions">
                            <button id="saveBtn">Simpan</button>
                            <button class="secondary" id="resetBtn" type="button">Reset Preset</button>
                        </div>
                        <div class="status" id="status">__STATUS__</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const defaults = __DEFAULTS__;
        const naturalWidth = __WIDTH__;
        const naturalHeight = __HEIGHT__;
        const shot = document.getElementById('shot');
        const overlay = document.getElementById('overlay');
        const status = document.getElementById('status');
        const leftRange = document.getElementById('leftRange');
        const topRange = document.getElementById('topRange');
        const rightRange = document.getElementById('rightRange');
        const bottomRange = document.getElementById('bottomRange');
        const clickX = document.getElementById('clickX');
        const clickY = document.getElementById('clickY');
        const metaCrop = document.getElementById('metaCrop');
        const leftValue = document.getElementById('leftValue');
        const topValue = document.getElementById('topValue');
        const rightValue = document.getElementById('rightValue');
        const bottomValue = document.getElementById('bottomValue');
        const resetBtn = document.getElementById('resetBtn');
        const saveBtn = document.getElementById('saveBtn');

        let state = {{
            click_x: defaults.click_x,
            click_y: defaults.click_y,
            crop_box: defaults.crop_box.slice(),
        }};

        function clamp(value, lower, upper) {{
            return Math.max(lower, Math.min(upper, value));
        }}

        function normalizeCrop() {{
            let [left, top, right, bottom] = state.crop_box;
            left = clamp(parseInt(left, 10) || 0, 0, naturalWidth - 1);
            top = clamp(parseInt(top, 10) || 0, 0, naturalHeight - 1);
            right = clamp(parseInt(right, 10) || naturalWidth, left + 1, naturalWidth);
            bottom = clamp(parseInt(bottom, 10) || naturalHeight, top + 1, naturalHeight);
            state.crop_box = [left, top, right, bottom];
            state.click_x = clamp(parseInt(state.click_x, 10) || 0, 0, naturalWidth);
            state.click_y = clamp(parseInt(state.click_y, 10) || 0, 0, naturalHeight);
        }}

        function readInputs() {{
            state.crop_box = [
                parseInt(leftRange.value, 10),
                parseInt(topRange.value, 10),
                parseInt(rightRange.value, 10),
                parseInt(bottomRange.value, 10),
            ];
            state.click_x = parseInt(clickX.value, 10);
            state.click_y = parseInt(clickY.value, 10);
            normalizeCrop();
        }}

        function syncInputs() {{
            leftRange.value = state.crop_box[0];
            topRange.value = state.crop_box[1];
            rightRange.value = state.crop_box[2];
            bottomRange.value = state.crop_box[3];
            clickX.value = state.click_x;
            clickY.value = state.click_y;

            leftValue.textContent = state.crop_box[0];
            topValue.textContent = state.crop_box[1];
            rightValue.textContent = state.crop_box[2];
            bottomValue.textContent = state.crop_box[3];
            metaCrop.textContent = '[' + state.crop_box.join(', ') + ']';
        }}

        function updateOverlay() {{
            const scale = shot.clientWidth / naturalWidth;
            overlay.style.left = (state.crop_box[0] * scale) + 'px';
            overlay.style.top = (state.crop_box[1] * scale) + 'px';
            overlay.style.width = ((state.crop_box[2] - state.crop_box[0]) * scale) + 'px';
            overlay.style.height = ((state.crop_box[3] - state.crop_box[1]) * scale) + 'px';
            syncInputs();
        }}

        function resetPreset() {{
            state.click_x = defaults.click_x;
            state.click_y = defaults.click_y;
            state.crop_box = defaults.crop_box.slice();
            updateOverlay();
            status.textContent = 'Preset awal dipulihkan.';
        }}

        leftRange.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        topRange.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        rightRange.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        bottomRange.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        clickX.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        clickY.addEventListener('input', () => {{ readInputs(); updateOverlay(); }});
        resetBtn.addEventListener('click', resetPreset);

        saveBtn.addEventListener('click', async () => {{
            readInputs();
            const payload = {{
                resolution: naturalWidth + 'x' + naturalHeight,
                click_x: state.click_x,
                click_y: state.click_y,
                crop_box: state.crop_box,
            }};

            status.textContent = 'Menyimpan...';
            const response = await fetch('/save', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload),
            }});

            const data = await response.json();
            if (data.ok) {{
                status.textContent = data.message;
                saveBtn.disabled = true;
            }} else {{
                status.textContent = data.message || 'Gagal menyimpan.';
            }}
        }});

        shot.addEventListener('load', updateOverlay);
        window.addEventListener('resize', updateOverlay);

        normalizeCrop();
        updateOverlay();
    </script>
</body>
</html>""".replace("__DEFAULTS__", defaults_json).replace("__WIDTH__", str(width)).replace("__HEIGHT__", str(height)).replace("__STATUS__", "Buka page ini di browser HP/PC, atur crop, lalu klik Simpan.")


class _CalibrationRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send_text(self, status_code, content, content_type="text/html; charset=utf-8"):
        encoded = content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send_text(200, self.server.page_html)
            return

        if self.path == "/shot.png":
            with open(self.server.preview_png_path, "rb") as file:
                data = file.read()

            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if self.path == "/health":
            self._send_text(200, "ok", "text/plain; charset=utf-8")
            return

        self._send_text(404, "Not Found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/save":
            self._send_text(404, json.dumps({"ok": False, "message": "Not Found"}), "application/json; charset=utf-8")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            resolution = payload.get("resolution", "")
            click_x = int(payload.get("click_x", 0))
            click_y = int(payload.get("click_y", 0))
            crop_box = payload.get("crop_box", [0, 0, 1, 1])
            width, height = self.server.screen_size

            if not isinstance(crop_box, list) or len(crop_box) != 4:
                raise ValueError("crop_box harus berisi 4 angka")

            crop_box = _normalisasi_crop_box(int(crop_box[0]), int(crop_box[1]), int(crop_box[2]), int(crop_box[3]), width, height)
            click_x = _clamp(click_x, 0, width)
            click_y = _clamp(click_y, 0, height)

            config_data = {
                "resolution": resolution or f"{width}x{height}",
                "click_x": click_x,
                "click_y": click_y,
                "crop_box": crop_box,
            }

            with open(CONFIG_FILE, "w") as file:
                json.dump(config_data, file, indent=4)

            self.server.saved_config = config_data
            self.server.save_event.set()

            self._send_text(200, json.dumps({"ok": True, "message": f"Kalibrasi tersimpan ke {CONFIG_FILE}"}), "application/json; charset=utf-8")
        except Exception as error:
            self._send_text(400, json.dumps({"ok": False, "message": f"Gagal menyimpan: {error}"}), "application/json; charset=utf-8")


def _start_web_server(page_html, screen_size, port=WEB_PORT):
    server = ThreadingHTTPServer(("0.0.0.0", port), _CalibrationRequestHandler)
    server.page_html = page_html
    server.screen_size = screen_size
    server.saved_config = None
    server.save_event = threading.Event()
    server.preview_png_path = None

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def run_web_calibration():
        print("\n--- MEMULAI WEB CALIBRATION ---")
        print("Pastikan layar HP kamu sedang membuka menu 'Kunci nama pengguna' di WA.")
        input("Tekan ENTER jika layar WA sudah siap...")

        width, height = get_screen_resolution()
        print(f"📱 Deteksi Resolusi Layar: {width} x {height}")

        print("📸 Mengambil screenshot percobaan...")
        subprocess.run("adb shell screencap -p /sdcard/calib.png", shell=True)
        subprocess.run("adb pull /sdcard/calib.png .", shell=True)

        if not os.path.exists("calib.png"):
                raise RuntimeError("Gagal mengambil screenshot untuk calibration")

        defaults = _profil_default_calibration(width, height)
        preview_png, preview_size = _build_preview_png("calib.png")
        preview_path = "calib_preview.png"

        with open(preview_path, "wb") as file:
            file.write(preview_png)

        page_html = _build_web_html(preview_size[0], preview_size[1], defaults)
        server = _start_web_server(page_html, (width, height))
        server.preview_png_path = preview_path

        try:
                subprocess.run(f"adb reverse tcp:{WEB_PORT} tcp:{WEB_PORT}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
                pass

        web_url = f"http://127.0.0.1:{WEB_PORT}"
        opened = False

        try:
                subprocess.run(
                        f'adb shell am start -a android.intent.action.VIEW -d "{web_url}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                )
                opened = True
                print(f"📲 Web UI dibuka di HP: {web_url}")
        except Exception:
                pass

        if not opened:
                webbrowser.open(web_url)
                print(f"🖥️ Web UI dibuka di browser: {web_url}")

        print("Atur crop di browser, lalu klik Simpan.")
        server.save_event.wait()

        config_data = server.saved_config
        server.shutdown()
        server.server_close()

        if os.path.exists("calib.png"):
                os.remove("calib.png")

        if os.path.exists(preview_path):
            os.remove(preview_path)

        print(f"\n✅ Kalibrasi Sukses! Konfigurasi disimpan di '{CONFIG_FILE}'\n")
        return config_data

def get_screen_resolution():
    """Mengambil resolusi asli layar HP via ADB"""
    print("🔄 Mengambil informasi resolusi layar...")
    result = subprocess.run("adb shell wm size", shell=True, capture_output=True, text=True)
    output = result.stdout.strip()
    
    if "Physical size" in output:
        res_str = output.split(":")[-1].strip()
        width, height = map(int, res_str.split("x"))
        return width, height
    return 1080, 2400  # Standar fallback

def run_terminal_calibration():
    print("\n--- MEMULAI AUTO-CALIBRATION ---")
    print("Pastikan layar HP kamu sedang membuka menu 'Kunci nama pengguna' di WA.")
    input("Tekan ENTER jika layar WA sudah siap...")
    
    width, height = get_screen_resolution()
    print(f"📱 Deteksi Resolusi Layar: {width} x {height}")
    
    print("📸 Mengambil screenshot percobaan...")
    subprocess.run("adb shell screencap -p /sdcard/calib.png", shell=True)
    subprocess.run("adb pull /sdcard/calib.png .", shell=True)
    
    defaults = _profil_default_calibration(width, height)
    click_x = defaults["click_x"]
    click_y = defaults["click_y"]
    crop_box = defaults["crop_box"]
    
    # Uji coba crop untuk verifikasi kecocokan layar
    if os.path.exists("calib.png"):
        img = Image.open("calib.png")
        crop_box = _interactive_adjust_crop(img, crop_box, width, height)

        _simpan_preview(img, crop_box, "test")

        os.remove("calib.png")
        
        print("\n[!] Final preview: 'test_crop.png' dan 'test_overlay.png' berhasil dibuat.")
        print("👉 Kalau sudah pas, hasil ini akan disimpan sebagai konfigurasi.")
        verif = input("❓ Simpan hasil calibration ini? (y/n): ").strip().lower()
        
        if verif != 'y':
            print("\n⚠️ Mode Manual Diaktifkan (Gunakan Pointer Location di Opsi Pengembang):")
            click_x = _baca_int(f"Masukkan koordinat X tombol refresh (Rekomendasi: {int(width / 2)}): ", default=int(width / 2), lower=0, upper=width)
            click_y = _baca_int(f"Masukkan koordinat Y tombol refresh (Rekomendasi: {int(height * 0.28)}): ", default=int(height * 0.28), lower=0, upper=height)
            crop_left = _baca_int("Masukkan batas kiri crop (X1): ", lower=0, upper=width)
            crop_top = _baca_int("Masukkan batas atas crop (Y1): ", lower=0, upper=height)
            crop_right = _baca_int("Masukkan batas kanan crop (X2): ", lower=0, upper=width)
            crop_bottom = _baca_int("Masukkan batas bawah crop (Y2): ", lower=0, upper=height)
            crop_box = _normalisasi_crop_box(crop_left, crop_top, crop_right, crop_bottom, width, height)

    config_data = {
        "resolution": f"{width}x{height}",
        "click_x": _clamp(click_x, 0, width),
        "click_y": _clamp(click_y, 0, height),
        "crop_box": crop_box
    }
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)
    
    print(f"\n✅ Kalibrasi Sukses! Konfigurasi disimpan di '{CONFIG_FILE}'\n")
    return config_data


def run_calibration():
    try:
        return run_web_calibration()
    except Exception as error:
        print(f"⚠️ Web calibration gagal: {error}")
        print("↩️ Jatuh ke mode terminal manual.")
        return run_terminal_calibration()

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return run_calibration()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)