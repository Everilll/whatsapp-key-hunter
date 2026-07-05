import time
import sys
import calibration
import ocr_handler

def main():
    print("===============================================")
    print("    🟩 WA USERNAME KEY HUNTER by EVERILL 🟩     ")
    print("===============================================")
    
    # 1. Muat konfigurasi perangkat (Otomatis kalibrasi jika belum ada)
    config = calibration.load_config()
    
    # 2. Meminta input target angka dari user
    target = input("Masukkan 4 digit angka target yang kamu cari: ").strip()
    
    if len(target) != 4 or not target.isdigit():
        print("❌ Error: Target harus berupa 4 digit angka!")
        sys.exit()
        
    # 3. Input jeda waktu dinamis berdasarkan spesifikasi HP pengguna
    print("\nSet Jeda Waktu (Semakin tinggi spesifikasi HP, bisa semakin cepat)")
    print("Saran: 0.8 (HP Flagship), 1.3 (HP Menengah), 2.0 (HP Entry-level)")
    jeda = float(input("Masukkan jeda waktu antar reset dalam detik (Default 1.3): ") or 1.3)
        
    print(f"\n🚀 Memulai perburuan angka {target} dengan jeda {jeda}s...")
    print("Tekan Ctrl + C di Termux kapan saja untuk menghentikan program.\n")
    
    attempt = 0
    
    try:
        while True:
            attempt += 1
            
            # 4. Membaca angka yang muncul di layar WA saat ini
            angka_sekarang = ocr_handler.dapatkan_angka_layar(config["crop_box"])
            
            # Jika Tesseract gagal membaca (hasil kosong), skip dan langsung refresh
            if not angka_sekarang:
                print(f"[{attempt}] ⚠️ Angka tidak terbaca, mencoba refresh...")
                ocr_handler.klik_refresh(config["click_x"], config["click_y"])
                time.sleep(jeda)
                continue
                
            print(f"[{attempt}] Terbaca di layar: {angka_sekarang} | Target: {target}")
            
            # 5. Cek apakah angka yang terbaca sudah sesuai target
            if angka_sekarang == target:
                print(f"\n🎉 KETEMU KUNCI CANTIKNYA!")
                print(f"👉 Angka {target} didapatkan pada percobaan ke-{attempt}.")
                print("Silakan klik 'Simpan kunci' secara manual di HP kamu! 😉")
                break
                
            # 6. Jika belum cocok, klik tombol dapatkan kunci baru
            ocr_handler.klik_refresh(config["click_x"], config["click_y"])
            
            # Jeda waktu tunggu transisi animasi angka baru di WA
            time.sleep(jeda)
            
    except KeyboardInterrupt:
        print("\n🛑 Program dihentikan secara manual oleh pengguna. Sampai jumpa!")

if __name__ == "__main__":
    main()