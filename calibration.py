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
        cropped = img.crop(tuple(crop_box))
        cropped.save("test_crop_angka.png")

        preview = img.copy()
        draw = ImageDraw.Draw(preview)
        draw.rectangle(tuple(crop_box), outline="red", width=6)
        preview.save("test_crop_overlay.png")

        os.remove("calib.png")
        
        print("\n[!] File 'test_crop_angka.png' berhasil dibuat.")
        print("[!] File 'test_crop_overlay.png' juga dibuat untuk lihat posisi crop di screenshot penuh.")
        print("👉 Silakan cek foto tersebut di galeri/penyimpanan HP kamu.")
        verif = input("❓ Apakah angka 4 digit WA terlihat penuh di foto tersebut? (y/n): ").strip().lower()
        
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