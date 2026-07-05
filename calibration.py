import os
import subprocess
import json
from PIL import Image, ImageDraw

CONFIG_FILE = "config_device.json"


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

def run_calibration():
    print("\n--- MEMULAI AUTO-CALIBRATION ---")
    print("Pastikan layar HP kamu sedang membuka menu 'Kunci nama pengguna' di WA.")
    input("Tekan ENTER jika layar WA sudah siap...")
    
    width, height = get_screen_resolution()
    print(f"📱 Deteksi Resolusi Layar: {width} x {height}")
    
    print("📸 Mengambil screenshot percobaan...")
    subprocess.run("adb shell screencap -p /sdcard/calib.png", shell=True)
    subprocess.run("adb pull /sdcard/calib.png .", shell=True)
    
    # Estimasi posisi Box Angka & Tombol berdasarkan persentase layar standar
    crop_left = int(width * 0.08)
    crop_top = int(height * 0.13)
    crop_right = int(width * 0.92)
    crop_bottom = int(height * 0.35)
    
    click_x = int(width * 0.5)       # Tengah layar horizontal
    click_y = int(height * 0.28)      # Area tombol refresh
    crop_box = _normalisasi_crop_box(crop_left, crop_top, crop_right, crop_bottom, width, height)
    
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

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return run_calibration()
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)