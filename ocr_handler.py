import subprocess
import os
from PIL import Image, ImageOps


def _gabungkan_segmen(kolom_berisi, min_width=5, gap_maks=2):
    segmen_kasar = []
    start_x = None

    for x, berisi in enumerate(kolom_berisi):
        if berisi and start_x is None:
            start_x = x
        elif not berisi and start_x is not None:
            segmen_kasar.append((start_x, x))
            start_x = None

    if start_x is not None:
        segmen_kasar.append((start_x, len(kolom_berisi)))

    if not segmen_kasar:
        return []

    segmen = [segmen_kasar[0]]

    for left, right in segmen_kasar[1:]:
        prev_left, prev_right = segmen[-1]
        if left - prev_right <= gap_maks:
            segmen[-1] = (prev_left, right)
        else:
            segmen.append((left, right))

    return [(left, right) for left, right in segmen if right - left > min_width]

def dapatkan_angka_layar(crop_box):
    """Mengambil screenshot, memisahkan angka secara dinamis berbasis kolom, dan membaca per digit"""
    # 1. Ambil screenshot via ADB
    subprocess.run("adb shell screencap -p /sdcard/wa_frame.png", shell=True, stdout=subprocess.DEVNULL)
    subprocess.run("adb pull /sdcard/wa_frame.png .", shell=True, stdout=subprocess.DEVNULL)
    
    if not os.path.exists("wa_frame.png"):
        print("❌ Gagal mengambil screenshot!")
        return ""
        
    img = Image.open("wa_frame.png")
    cropped_img = img.crop(tuple(crop_box)).convert('L')
    
    # Pre-processing agar kontras tajam (Bilinear + Binerisasi)
    w, h = cropped_img.size
    cropped_img = cropped_img.resize((w * 2, h * 2), Image.Resampling.BILINEAR)
    binary_img = cropped_img.point(lambda p: 255 if p > 140 else 0)
    
    binary_img.save("clean_angka.png")
    binary_img.save("/sdcard/hasil_potong_bot.png")
    
    # 2. PROYEKSI VERTIKAL: Cari kolom mana saja yang berisi piksel putih (angka)
    bw_data = binary_img.load()
    width, height = binary_img.size
    
    # Cek setiap kolom dari kiri ke kanan, apakah ada piksel putihnya
    kolom_berisi = []
    for x in range(width):
        ada_putih = False
        for y in range(height):
            if bw_data[x, y] == 255:
                ada_putih = True
                break
        kolom_berisi.append(ada_putih)
    
    # Kelompokkan kolom putih menjadi segmen-segmen angka terpisah.
    # Gap kecil di dalam bentuk angka digabung agar digit tidak terpecah.
    segmen = _gabungkan_segmen(kolom_berisi)

    # 3. KIRIM SETIAP SEGMEN ANGKA KE TESSERACT (--psm 10)
    teks_clean = ""
    
    # Ambil maksimal 4 segmen dari kiri ke kanan (format target 4 digit)
    for idx, (left, right) in enumerate(segmen[:4]):
        # Potong pas di koordinat angka tersebut
        digit_crop = binary_img.crop((left, 0, right, height))
        
        # Beri padding border hitam di sekelilingnya agar Tesseract fokus di tengah
        padded_digit = ImageOps.expand(digit_crop, border=30, fill=0)
        padded_digit.save(f"digit_{idx}.png")
        
        # Eksekusi Tesseract Single Character
        cmd = f"tesseract digit_{idx}.png hasil_digit_{idx} --psm 8 -c tessedit_char_whitelist=0123456789"
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(f"hasil_digit_{idx}.txt"):
            with open(f"hasil_digit_{idx}.txt", "r") as f:
                char = f.read().strip()
                char_clean = "".join(filter(str.isdigit, char))
                if char_clean:
                    teks_clean += char_clean[0]
            os.remove(f"hasil_digit_{idx}.txt")
            
        if os.path.exists(f"digit_{idx}.png"): os.remove(f"digit_{idx}.png")
        
    if os.path.exists("wa_frame.png"): os.remove("wa_frame.png")
    
    return teks_clean

def klik_refresh(x, y):
    """Simulasi tap layar pada tombol 'Dapatkan kunci yang berbeda'"""
    subprocess.run(f"adb shell input tap {x} {y}", shell=True, stdout=subprocess.DEVNULL)