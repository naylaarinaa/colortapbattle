# Color Tap Battle - Permainan Multiplayer

## Deskripsi

Color Tap Battle adalah permainan multiplayer berbasis **Stroop Color Game** yang menggunakan server Flask dan client pygame. Server mengelola koneksi pemain, state permainan, dan logika soal secara real-time. Pemain dapat bermain bersama-sama dalam sesi yang tersinkronisasi.

## Struktur Proyek

```
colortapbattle/
├── assets/
│   ├── instructions.png          # Gambar instruksi permainan
│   ├── waiting_lobby.png         # Background lobby menunggu
│   ├── LuckiestGuy-Regular.ttf   # Font utama
│   └── BalsamiqSans-Regular.ttf  # Font tambahan
├── src/
│   ├── client.py                 # Aplikasi client pygame (permainan)
│   ├── server.py                 # Server multiplayer utama
│   ├── game_logic.py            # Logika soal dan validasi jawaban
│   └── utils.py                 # Utility untuk serialisasi data
├── requirements.txt             # Daftar dependensi Python
├── .vscode/
│   └── tasks.json              # Konfigurasi VS Code tasks
└── README.md                   # Dokumentasi proyek (file ini)
```

## Cara Menjalankan Permainan Multiplayer

### 1. Instalasi Dependensi

Install semua dependensi yang diperlukan:

```bash
pip install -r requirements.txt
```

### 2. Menjalankan Server

Jalankan server di terminal:

```bash
cd src
python server.py [jumlah_pemain]
```

**Opsi jumlah pemain:**

- Tanpa parameter: Default 2 pemain
- Dengan parameter: `python server.py 4` (untuk 4 pemain)
- Minimum: 2 pemain
- Maksimum: 10 pemain

Server akan berjalan di `http://127.0.0.1:8080` dan menampilkan:

```
Task Processing Model: Multi-threaded Flask
Server running on http://127.0.0.1:8080
Waiting for 2 players to start the game...
```

### 3. Menjalankan Client (Pemain)

Buka beberapa terminal baru dan jalankan:

```bash
cd src
python client.py
```

Setiap pemain akan diminta memasukkan username mereka:

```
Masukkan Username Anda: Pemain1
```

### 4. Alur Permainan

1. **Lobby**: Pemain akan masuk ke lobby dan menunggu pemain lain bergabung
2. **Menunggu**: Layar lobby menampilkan berapa pemain yang sudah bergabung
3. **Mulai Otomatis**: Permainan dimulai otomatis ketika pemain minimum tercapai
4. **Bermain**: Semua pemain melihat soal yang sama dengan timer tersinkronisasi
5. **Hasil Akhir**: Skor final ditampilkan kepada semua pemain

## Aturan Permainan

### Dasar Permainan

- Permainan memerlukan **minimal 2 pemain** untuk dimulai
- Pemain akan melihat layar lobby sampai cukup pemain bergabung
- Setelah 2+ pemain terhubung, permainan dimulai otomatis
- Semua pemain melihat soal dan timer yang tersinkronisasi
- Setiap soal berlangsung **10 detik**
- Pemain bersaing menjawab 10 soal dengan benar

### Sistem Poin

- **Jawaban Benar**: +100 poin
- **Jawaban Pertama yang Benar**: +150 poin (100 + bonus 50)
- **Jawaban Salah**: 0 poin
- **Tidak Menjawab**: 0 poin
- Leaderboard real-time menampilkan skor semua pemain

### Fitur Cerdas

- **Lanjut Otomatis**: Soal berikutnya muncul ketika SEMUA pemain sudah menjawab
- **Pesan "Waktu Habis!"**: Muncul ketika timer habis untuk pemain yang belum menjawab
- **Indikator Visual**: Menampilkan status "Semua pemain sudah menjawab! Lanjut ke berikutnya..."

## Perbaikan Terbaru

### ✅ Sinkronisasi Timer

- Timer countdown dari 10 detik tersinkronisasi dengan benar di semua client
- Timer sekarang hitung mundur lancar dari 10 ke 0 detik
- Warna timer berubah merah ketika ≤3 detik tersisa

### ✅ Reset Permainan

- Setelah permainan selesai, menjalankan client baru otomatis mereset permainan
- Tidak ada lagi error "permainan sudah selesai"
- State bersih untuk setiap sesi permainan baru

### ✅ Model Pemrosesan Tugas

- **Server Flask Multi-threaded**: Menggunakan `threaded=True` untuk menangani request concurrent
- **Thread-per-request**: Setiap request client ditangani dalam thread terpisah
- **Shared game state**: Akses thread-safe ke state permainan terpusat
- **Tanpa process pools**: Model threading sederhana untuk skala aplikasi ini

### ✅ Bonus Jawaban Pertama

- Pemain pertama yang menjawab dengan benar mendapat **+150 poin** (100 dasar + 50 bonus)
- Jawaban benar lainnya tetap mendapat **+100 poin**
- Feedback visual menampilkan "Pertama!" dengan popup warna emas

### ✅ Progres Soal Cerdas

- **Lanjut Otomatis**: Permainan pindah ke soal berikutnya ketika SEMUA pemain sudah menjawab
- **Waktu Habis!**: Menampilkan pesan ketika timer habis untuk pemain yang tidak menjawab
- **Indikator Visual**: Menampilkan status "Semua pemain sudah menjawab! Lanjut ke berikutnya..."

## Detail Teknis

### Arsitektur Sistem

```
[Client 1] ←→ HTTP ←→ [Flask Server] ←→ HTTP ←→ [Client 2]
                          ↓
                    [Game State]
                    (Thread-safe)
```

### Teknologi yang Digunakan

- **Server**: Flask multi-threaded dengan model thread-per-request
- **Client**: Pygame dengan HTTP polling untuk update real-time
- **Sinkronisasi**: Timing server-side dengan client polling setiap frame
- **Manajemen State**: State permainan terpusat dengan reset otomatis
- **Concurrency**: Operasi thread-safe untuk beberapa pemain simultan

### Endpoint API

- `POST /join` - Bergabung ke lobby permainan
- `GET /status` - Mendapatkan status permainan dan info pemain
- `GET /question` - Mendapatkan soal saat ini
- `POST /answer` - Mengirim jawaban pemain
- `POST /reset` - Reset permainan (manual)

## Menguji Perbaikan

1. **Mulai server** (Anda akan melihat "Task Processing Model: Multi-threaded")
2. **Mulai 2+ client** di terminal terpisah
3. **Perhatikan timer countdown 10 detik** yang tersinkronisasi
4. **Setelah permainan berakhir**, mulai client baru - permainan akan auto-reset
5. **Timer harus hitung mundur lancar**: 10→9→8→7→6→5→4→3→2→1→0

## Troubleshooting

### Masalah Koneksi

- Pastikan server berjalan sebelum menjalankan client
- Periksa firewall tidak memblokir port 8080
- Pastikan tidak ada aplikasi lain yang menggunakan port 8080

### Masalah Font/Asset

- Pastikan file font `LuckiestGuy-Regular.ttf` dan `BalsamiqSans-Regular.ttf` ada di folder `assets/`
- Pastikan file gambar `instructions.png` dan `waiting_lobby.png` ada di folder `assets/`

### Masalah Pygame

- Pastikan pygame terinstall dengan benar: `pip install pygame`
- Untuk Linux, mungkin perlu install dependensi tambahan: `sudo apt-get install python3-pygame`

## Kontribusi

Silakan ajukan pull request atau issue jika ingin berkontribusi atau menemukan bug. Pastikan untuk:

1. Test fitur baru dengan multiple client
2. Dokumentasikan perubahan dalam bahasa Indonesia
3. Pastikan kompatibilitas dengan sistem multiplayer yang ada

## Lisensi

Proyek ini dibuat untuk keperluan pembelajaran Pemrograman Jaringan Semester 6.
