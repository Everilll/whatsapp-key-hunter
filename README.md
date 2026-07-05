# WhatsApp Key Hunter Bot

![ADB](https://img.shields.io/badge/Automation-ADB%20Shell-3DDC84?style=for-the-badge&logo=android&logoColor=white)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue?style=flat-square&logo=python)
![Platform](https://img.shields.io/badge/platform-Android%20%7C%20Termux-orange?style=flat-square&logo=android)
![OCR Engine](https://img.shields.io/badge/OCR-Tesseract%20v4%2Fv5-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-informational?style=flat-square)
![Version](https://img.shields.io/badge/version-v1.0.0-6f42c1?style=flat-square)

Tool Python + ADB untuk mengotomasi pembacaan dan pengecekan kombinasi 4 digit angka pada layar WhatsApp. Pipeline utamanya dibuat ringan, berbasis **Dynamic Digit Slicing**, **Tesseract OCR**, dan calibration yang menyimpan koordinat asli perangkat, bukan sekadar nilai preview.

---

## ✨ Fitur Utama

- **Dynamic Digit Slicing:** Memisahkan angka dari screenshot lewat proyeksi kolom piksel putih, jadi pemotongan tetap jalan walau jarak antar-digit berubah-ubah.
- **Gap Merging di Dalam Bentuk Angka:** Celah hitam kecil di tubuh digit ikut dijembatani agar angka seperti `0`, `6`, atau `8` tidak gampang pecah saat diproses.
- **OCR yang Difokuskan ke Angka:** Potongan digit tunggal dikirim ke Tesseract dengan `--psm 8` dan whitelist numerik supaya hasil baca lebih konsisten.
- **Calibration yang Menyimpan Koordinat Asli:** UI calibration dipakai buat adjust visual, lalu hasil akhir disimpan kembali ke resolusi screenshot asli perangkat.
- **Preset + Fallback Manual:** Ada preset awal untuk device umum, tetapi tetap bisa dikoreksi lewat web UI interaktif atau mode terminal kalau layout perangkat beda.

---

## 🛠️ Persyaratan & Instalasi (Termux)

Pastikan Anda menggunakan Termux versi terbaru. **Jangan gunakan Termux dari Google Play Store** karena tidak lagi diperbarui dan dapat menyebabkan error.

### 1. Termux Resmi

1. **F-Droid (Rekomendasi):** [Download Termux via F-Droid](https://f-droid.org/en/packages/com.termux/)
   - Disarankan instal F-Droid terlebih dahulu, lalu cari `Termux` di dalamnya agar lebih mudah update.
2. **GitHub Resmi:** [Termux Releases v0.118+](https://github.com/termux/termux-app/releases)
   - Pilih file `.apk` yang sesuai dengan arsitektur HP Anda, biasanya `universal` atau `arm64-v8a`.

### 2. Update dan Upgrade Repositori Termux

```bash
pkg update && pkg upgrade -y
```

### 3. Install Paket Dependensi Utama

```bash
pkg install android-tools git python python-pillow tesseract -y
```

### 4. Install Library Python Pendukung

```bash
pip install Pillow
```

---

## 🚀 Cara Penggunaan

### Langkah 1: Siapkan ADB

Sebelum menjalankan skrip, pastikan **USB Debugging** atau **Wireless Debugging** di Opsi Pengembang HP sudah aktif.

#### Opsi A: Kabel USB

Colokkan HP ke laptop atau perangkat Termux, lalu cek apakah perangkat sudah terdeteksi:

```bash
adb devices
```

Pastikan status di sebelah ID perangkat bertuliskan `device`, bukan `unauthorized`.

#### Opsi B: Wi-Fi

Hubungkan HP dan laptop/Termux ke jaringan Wi-Fi yang sama, lalu aktifkan ADB Wi-Fi:

```bash
adb tcpip 5555
adb connect <IP_HP_ANDA>:5555
adb devices
```

### Langkah 2: Kalibrasi Layar HP

1. Buka halaman target pada aplikasi WhatsApp di HP.
2. Jalankan skrip kalibrasi:

```bash
python calibration.py
```

3. Ikuti calibration UI sampai kotak crop merah sudah pas membungkus angka target, lalu simpan konfigurasi.

### Langkah 3: Jalankan Bot Hunter

Setelah file `config_device.json` terbentuk dari hasil kalibrasi, jalankan bot utamanya:

```bash
python main.py
```

### Langkah 4: Berhenti Manual

Bot akan otomatis berhenti jika angka target sudah ditemukan di layar. Jika ingin menghentikannya di tengah jalan secara aman, tekan:

```bash
Ctrl + C
```

---

## 📂 Struktur Proyek

- `main.py` - Script loop utama yang mengatur alur logika jalannya bot.
- `ocr_handler.py` - Otak pemrosesan gambar, proyeksi vertikal kolom, dan eksekutor Tesseract OCR.
- `calibration.py` - Alat bantu interaktif untuk konfigurasi koordinat layar otomatis/manual.
- `config_device.json` - Menyimpan resolusi layar, koordinat klik tombol refresh, dan batas crop gambar.

---

## ⚠️ Catatan Penting

- **Suhu Perangkat:** Karena skrip melakukan pengambilan gambar secara terus-menerus, CPU HP akan bekerja aktif. Disarankan menurunkan kecerahan layar ke tingkat minimum dan menjaga suhu HP tetap adem selama proses berjalan lama.
- **Anti-Ghost Touch:** Bot ini menggunakan jalur simulasi perintah resmi Android tingkat software, sehingga tidak akan merusak komponen fisik layar atau memicu ghost touch.

---

## 📜 Lisensi

Proyek ini dirilis di bawah [MIT License](LICENSE).
