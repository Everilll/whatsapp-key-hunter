import subprocess
import os
from PIL import Image

def dapatkan_angka_layar(crop_box):
    """Mengambil screenshot, memotong per digit, dan membaca dengan Tesseract"""
    # 1. Ambil screenshot via ADB lokal
    subprocess.run("adb shell screencap -p /sdcard/wa_frame.png", shell=True, stdout=subprocess.DEVNULL)
    subprocess.run("adb pull /sdcard/wa_frame.png .", shell=True, stdout=subprocess.DEVNULL)
    
    if not os.path.exists("wa_frame.png"):
        print("❌ Gagal mengambil screenshot dari ADB. Periksa koneksi!")
        return ""
        
    # 2. Potong Gambar secara utuh dulu
    img = Image.open("wa_frame.png")
    cropped_img = img.crop(tuple(crop_box))
    
    # Pre-processing dasar
    cropped_img = cropped_img.convert('L')
    w, h = cropped_img.size
    cropped_img = cropped_img.resize((w * 2, h * 2), Image.Resampling.BILINEAR)
    cropped_img = cropped_img.point(lambda p: 255 if p > 127 else 0)
    
    # 3. POTONG MENJADI 4 KOTAK DIGIT SECARA VERTIKAL
    new_w, new_h = cropped_img.size
    lebar_per_digit = new_w // 4
    
    teks_bersih = ""
    
    for i in range(4):
        # Hitung koordinat kotak per angka
        left = i * lebar_per_digit
        right = (i + 1) * lebar_per_digit
        
        # Potong satu angka saja
        digit_img = cropped_img.crop((left, 0, right, new_h))
        
        # Tambahkan border hitam di sekelilingnya agar Tesseract fokus di tengah
        padded_img = Image.new("L", (digit_img.width + 40, digit_img.height + 40), 0)
        padded_img.paste(digit_img, (20, 20))
        padded_img.save(f"digit_{i}.png")
        
        # Panggil Tesseract khusus mode SINGLE CHARACTER (--psm 10)
        cmd = f"tesseract digit_{i}.png hasil_digit_{i} --psm 10 -c tessedit_char_whitelist=0123456789"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Baca hasilnya
        if os.path.exists(f"hasil_digit_{i}.txt"):
            with open(f"hasil_digit_{i}.txt", "r") as f:
                char = f.read().strip()
                # Ambil karakter angka pertama yang valid
                char_clean = "".join(filter(str.isdigit, char))
                if char_clean:
                    teks_bersih += char_clean[0]
            os.remove(f"hasil_digit_{i}.txt")
            
        if os.path.exists(f"digit_{i}.png"): os.remove(f"digit_{i}.png")

    # Bersihkan sisa file sampah
    if os.path.exists("wa_frame.png"): os.remove("wa_frame.png")
    
    return teks_bersih

def klik_refresh(x, y):
    """Simulasi tap layar pada tombol 'Dapatkan kunci yang berbeda'"""
    subprocess.run(f"adb shell input tap {x} {y}", shell=True, stdout=subprocess.DEVNULL)