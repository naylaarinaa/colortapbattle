# Color Tap Server & Client

## Deskripsi

Color Tap Server adalah server multiplayer untuk game **Stroop Color Game** (Color Tap Battle). Server ini mengelola koneksi pemain, state permainan, dan logika soal. Client pygame akan terhubung ke server untuk bermain secara interaktif.

## Struktur Proyek

```
color-tap-server/
├── assets/
│   ├── instructions.png
│   ├── howtoplay.png
│   └── LuckiestGuy-Regular.ttf
├── src/
│   ├── client.py         # Aplikasi client pygame (game)
│   ├── server.py         # Server utama
│   ├── game_logic.py     # Logika soal dan validasi jawaban
│   └── utils.py          # Utility untuk serialisasi data
├── requirements.txt      # Daftar dependensi Python
└── README.md             # Dokumentasi proyek
```

## Cara Menjalankan

### 1. Instalasi Dependensi

Install semua dependensi:

```bash
pip install -r requirements.txt
```

### 2. Menjalankan Server

Jalankan server di terminal:

```bash
python src/server.py
```

Server akan berjalan di `127.0.0.1:55555` dan siap menerima koneksi client.

### 3. Menjalankan Client (Game)

Buka terminal baru (pastikan venv aktif), lalu jalankan:

```bash
python src/client.py
```

Ikuti instruksi pada layar untuk memasukkan nomor pemain dan mulai bermain.

### 4. Catatan

- Pastikan file gambar instruksi (`instructions.png` atau `howtoplay.png`) dan font (`LuckiestGuy-Regular.ttf`) ada di folder `assets`.
- Untuk multiplayer, jalankan beberapa client di komputer berbeda (atau sama) yang terhubung ke server.

## Kontribusi

Silakan ajukan pull request atau issue jika ingin berkontribusi atau menemukan bug.
