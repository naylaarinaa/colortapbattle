# Stroop Color Game - Multiplayer Real-Time

## 🔧 **Versi dan Branch**

### **Branch Utama: Redis Version**
Branch `main` ini menggunakan **Redis sebagai backend database** untuk state management.

### **Alternative: Non-Redis Version**
Jika Anda tidak ingin menggunakan Redis atau ingin implementasi yang lebih sederhana, tersedia versi **tanpa Redis** di branch terpisah:

```bash
# Pindah ke branch non-redis
git checkout non-redis

# Atau clone langsung branch non-redis
git clone -b non-redis https://github.com/your-username/colortapbattle.git
```


## Deskripsi

**Stroop Color Game** adalah permainan multiplayer real-time berbasis **Stroop Effect** yang dibangun dengan Python. Game ini menggunakan arsitektur terdistribusi: Redis untuk state sharing, load balancer untuk distribusi client, dan client pygame untuk pengalaman bermain yang sinkron.

## Struktur Proyek

```
stroopcolorgame/
├── assets/
│   ├── BalsamiqSans-Regular.ttf     # Font untuk UI dan text
│   ├── LuckiestGuy-Regular.ttf      # Font utama untuk judul
│   ├── main.png                     # Background gameplay utama
│   ├── username.png                 # Background input username
│   ├── instructions.png             # Gambar instruksi permainan
│   ├── waiting_lobby.png            # Background lobby menunggu
│   ├── correct.png                  # Popup jawaban benar
│   ├── wrong.png                    # Popup jawaban salah
│   ├── timesup.png                  # Popup waktu habis
│   ├── roundcompleted.png           # Popup ronde selesai
│   ├── final_score.png              # Background halaman skor akhir
│   └── winner.png                   # Popup pemenang
├── src/
│   ├── client.py                    # Client pygame (UI & koneksi)
│   ├── http.py                      # HTTP server & game logic
│   ├── server_thread_http.py        # Multi-threaded HTTP server
│   ├── game_state.py                # Manajemen state game di Redis
│   └── load_balancer.py             # Load balancer untuk multi-server
├── requirements.txt                 # Dependensi Python (pygame, redis)
├── .gitignore                       # Git ignore file
└── README.md                        # Dokumentasi proyek
```

## Instalasi & Setup

### 1. Persyaratan Sistem

- Python 3.7+
- Redis Server
- pygame
- Koneksi internet (untuk multiplayer)

### 2. Instalasi Dependensi

```bash
pip install -r requirements.txt
```

### 3. Setup Redis Server

**Windows:**

```bash
# Download Redis dari https://redis.io/download
# Atau gunakan Docker:
docker run -d -p 6379:6379 redis:latest
```

**Linux/macOS:**

```bash
sudo apt install redis-server
sudo systemctl start redis-server
# atau
brew install redis
brew services start redis
```

### 4. Verifikasi Setup

```bash
redis-cli ping  # Harusnya: PONG
ls assets/      # Pastikan semua asset tersedia
```

## Cara Menjalankan Game

### Mode 1: Load Balancer (Direkomendasikan)

1. **Start Redis Server**
   ```bash
   redis-server
   # atau
   sudo systemctl start redis-server
   ```
2. **Start Beberapa Game Server**
   ```bash
   cd src
   python server_thread_http.py --port 8889 --server-id server1 --required-players 2
   python server_thread_http.py --port 8890 --server-id server2
   python server_thread_http.py --port 8891 --server-id server3
   ```
3. **Start Load Balancer**
   ```bash
   python load_balancer.py --port 8888 --backends 8889,8890,8891
   ```
4. **Start Client**
   ```bash
   python client.py
   # Jalankan di terminal berbeda untuk client lain
   ```

### Mode 2: Direct Connection

1. **Start Single Server**
   ```bash
   cd src
   python server_thread_http.py --port 8889 --required-players 2
   ```
2. **Start Client**
   ```bash
   python client.py --direct-connection --server-host 127.0.0.1 --server-ports 8889
   ```

### Parameter Server

```bash
python server_thread_http.py [OPTIONS]
--port INTEGER              # Port server (default: 8889)
--redis-host TEXT           # Redis host (default: 127.0.0.1)
--redis-port INTEGER        # Redis port (default: 6379)
--required-players INTEGER  # Jumlah pemain untuk mulai game
--server-id TEXT            # ID server (untuk logging)
```

### Parameter Load Balancer

```bash
python load_balancer.py [OPTIONS]
--port INTEGER    # Port load balancer (default: 8888)
--backends TEXT   # Port backend servers (default: 8889,8890,8891)
--host TEXT       # Host backend server (default: 127.0.0.1)
```

### Parameter Client

```bash
python client.py [OPTIONS]
--direct-connection      # Koneksi langsung ke server (tanpa load balancer)
--server-host TEXT       # Host server (default: 127.0.0.1)
--server-ports TEXT      # Port server (default: 8889)
```

## Alur Permainan

```
Input Username → Instructions → Lobby → Countdown → Game → Final Score → Restart/Exit
```

1. Input username (max 5 karakter)
2. Baca instruksi
3. Masuk lobby menunggu pemain lain
4. Countdown otomatis jika pemain cukup
5. Main 10 soal
6. Lihat skor akhir & ranking
7. Pilih restart atau exit

## Aturan Permainan

- **Objektif:** Pilih warna dari teks yang ditampilkan, BUKAN arti katanya.
  - Contoh: Teks "RED" berwarna biru → Jawaban benar: "BLUE"
- **Timer per soal:** 10 detik
- **Total soal:** 10
- **Auto advance:** Jika semua sudah jawab, lanjut otomatis
- **Leaderboard:** Skor real-time

### Sistem Poin

| Kondisi                    | Poin                         |
| -------------------------- | ---------------------------- |
| Jawaban benar              | Base + Time bonus            |
| Jawaban pertama yang benar | Base + Time bonus + 50 bonus |
| Jawaban salah/tidak jawab  | 0                            |

- **Time bonus:** Sisa detik × 10 poin
- **First correct:** +50 poin

## Arsitektur Teknis

```
                     ┌─────────────────┐
                     │  Load Balancer  │
                     │   (Port 8888)   │
                     └─────────┬───────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼─────┐    ┌─────▼─────┐    ┌─────▼─────┐
        │  Server 1 │    │  Server 2 │    │  Server 3 │
        │ Port 8889 │    │ Port 8890 │    │ Port 8891 │
        └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                      ┌────────▼────────┐
                      │  Redis Server   │
                      │   (Port 6379)   │
                      │  Shared State   │
                      └─────────────────┘
```

### Komponen Utama

- **game_state.py**: State game di Redis, thread-safe, heartbeat, scalable
- **load_balancer.py**: Round robin, health check, failover, proxy
- **http.py**: Game logic, REST API, fallback ke in-memory jika Redis down
- **server_thread_http.py**: Multi-threaded server, Redis integration, shutdown aman
- **client.py**: Pygame UI, auto connect ke load balancer/server, asset management

### API Endpoints

| Method | Endpoint            | Fungsi                  |
| ------ | ------------------- | ----------------------- |
| POST   | /join               | Join lobby              |
| GET    | /status?player_id=X | Status game (heartbeat) |
| GET    | /question           | Soal saat ini           |
| POST   | /answer             | Submit jawaban          |
| POST   | /reset              | Reset game (admin)      |
| GET    | /server-stats       | Statistik server        |

## Fitur Lanjutan

- **Auto-reset:** Game otomatis reset setelah selesai
- **Load balancing:** Distribusi client ke banyak server
- **Perfect sync:** Semua client sinkron soal & timer
- **Thread safety:** Redis lock, connection pooling
- **Disconnection handling:** Heartbeat, auto-remove player
- **Monitoring & logging:** Structured log, metrics

## Troubleshooting

| Problem                       | Solusi                                |
| ----------------------------- | ------------------------------------- |
| "Failed to connect to server" | Pastikan server jalan di port 8889    |
| Font/asset not found          | Cek file di folder `assets/`          |
| Game lag/desync               | Cek jaringan, restart server          |
| Server crash                  | Cek log untuk error detail            |
| Redis connection failed       | Jalankan `redis-server`               |
| Port already in use           | Ganti port atau kill proses lama      |
| No healthy backend servers    | Start backend server sebelum balancer |

## Performance & Scalability

- **Max players:** 10 concurrent
- **Response time:** <100ms (local)
- **Memory:** ~50MB per client
- **Optimizations:** Asset caching, polling efisien, JSON minim

## Contributing

- Ikuti PEP 8
- Nama variabel bahasa Inggris, komentar bahasa Indonesia
- Logging terstruktur
- Test multi-client sebelum PR

---

**🎮 Selamat bermain Stroop Color Game!**

Untuk support atau bug report, silakan buka issue di repository ini.
