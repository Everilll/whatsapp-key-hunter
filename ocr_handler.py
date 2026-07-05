import subprocess
import os
from PIL import Image

def dapatkan_angka_layar(crop_box):
    """Mengambil screenshot, memotong area angka, dan membaca teksnya dengan Tesseract"""
    # 1. Ambil screenshot via ADB lokal
    subprocess.run("adb shell screencap -p /sdcard/wa_frame.png", shell=True, stdout=subprocess.DEVNULL)
    subprocess.run("adb pull /sdcard/wa_frame.png .", shell=True, stdout=subprocess.DEVNULL)
    
    if not os.path.exists("wa_frame.png"):
        print("❌ Gagal mengambil screenshot dari ADB. Periksa koneksi!")
        return ""
        
    # 2. Potong Gambar sesuai box konfigurasi hasil kalibrasi
    img = Image.open("wa_frame.png")
    cropped_img = img.crop(tuple(crop_box))
    
    # Mengubah gambar ke hitam-putih (Grayscale) agar OCR jauh lebih akurat
    cropped_img = cropped_img.convert('L')
    cropped_img.save("clean_angka.png")
    
    # 3. Jalankan Tesseract OCR mode khusus angka (--psm 6 digits)
    subprocess.run("tesseract clean_angka.png hasil_ocr --psm 6 digits", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    teks_bersih = ""
    if os.path.exists("hasil_ocr.txt"):
        with open("hasil_ocr.txt", "r") as f:
            raw_text = f.read().strip()
            # Ambil karakter angka saja (buang spasi atau baris baru)
            teks_bersih = ''.join(filter(str.isdigit, raw_text))
            
        os.remove("hasil_ocr.txt")
        
    # Hapus file temporary agar memori tidak penuh
    if os.path.exists("wa_frame.png"): os.remove("wa_frame.png")
    if os.path.exists("clean_angka.png"): os.remove("clean_angka.png")
        
    return teks_bersih

def klik_refresh(x, y):
    """Simulasi tap layar pada tombol 'Dapatkan kunci yang berbeda'"""
    subprocess.run(f"adb shell input tap {x} {y}", shell=True, stdout=subprocess.DEVNULL)