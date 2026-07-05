import os
import subprocess
import json
from PIL import Image

CONFIG_FILE = "config_device.json"

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
    crop_left = int(width * 0.10)
    crop_top = int(height * 0.15)
    crop_right = int(width * 0.90)
    crop_bottom = int(height * 0.32)
    
    click_x = int(width * 0.5)       # Tengah layar horizontal
    click_y = int(height * 0.28)      # Area tombol refresh
    
    # Uji coba crop untuk verifikasi kecocokan layar
    if os.path.exists("calib.png"):
        img = Image.open("calib.png")
        cropped = img.crop((crop_left, crop_top, crop_right, crop_bottom))
        cropped.save("test_crop_angka.png")
        os.remove("calib.png")
        
        print("\n[!] File 'test_crop_angka.png' berhasil dibuat.")
        print("👉 Silakan cek foto tersebut di galeri/penyimpanan HP kamu.")
        verif = input("❓ Apakah angka 4 digit WA terlihat penuh di foto tersebut? (y/n): ").strip().lower()
        
        if verif != 'y':
            print("\n⚠️ Mode Manual Diaktifkan (Gunakan Pointer Location di Opsi Pengembang):")
            click_x = int(input(f"Masukkan koordinat X tombol refresh (Rekomendasi: {int(width/2)}): "))
            click_y = int(input("Masukkan koordinat Y tombol refresh: "))
            crop_left = int(input("Masukkan batas kiri crop (X1): "))
            crop_top = int(input("Masukkan batas atas crop (Y1): "))
            crop_right = int(input("Masukkan batas kanan crop (X2): "))
            crop_bottom = int(input("Masukkan batas bawah crop (Y2): "))

    config_data = {
        "resolution": f"{width}x{height}",
        "click_x": click_x,
        "click_y": click_y,
        "crop_box": [crop_left, crop_top, crop_right, crop_bottom]
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