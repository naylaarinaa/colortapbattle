# Stroop Color Game - Multiplayer Real-Time

## 🔧 **Modes dan Deployment**

Game ini mendukung 2 mode deployment:

### **Mode 1: Dengan Redis (Scalable, Multi-server)**

- ✅ Mendukung load balancer
- ✅ Multiple server instances
- ✅ Shared state across servers
- ✅ Auto-scaling untuk banyak pemain

### **Mode 2: Tanpa Redis (Simple, Single server)**

- ✅ Single server dengan in-memory state
- ✅ Tidak memerlukan Redis installation
- ✅ Cocok untuk development atau game kecil
- ❌ Tidak mendukung load balancer

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
- pygame
- Redis Server (hanya untuk Mode 1)

### 2. Instalasi Dependensi

```bash
pip install -r requirements.txt
```

### 3. Setup Redis Server (Hanya untuk Mode 1)

**Windows:**

```bash
# Option 1: Download Redis dari https://redis.io/download
# Option 2: Gunakan Docker
docker run -d -p 6379:6379 redis:latest

# Option 3: Windows Subsystem for Linux (WSL)
sudo apt update && sudo apt install redis-server
sudo service redis-server start
```

**Linux/macOS:**

```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis
```

### 4. Verifikasi Setup

```bash
# Test Redis (hanya untuk Mode 1)
redis-cli ping  # Expected: PONG

# Test assets
ls assets/      # Pastikan semua asset tersedia
```

## 🚀 **Cara Menjalankan Game**

---

## **MODE 1: DENGAN REDIS** (Scalable)

### Skenario A: Load Balancer + Multi Server (Production)

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Server 1
cd src
python server_thread_http.py --port 8889 --server-id server1 --required-players 2

# Terminal 3: Start Server 2
cd src
python server_thread_http.py --port 8890 --server-id server2

# Terminal 4: Start Server 3
cd src
python server_thread_http.py --port 8891 --server-id server3

# Terminal 5: Start Load Balancer
cd src
python load_balancer.py --port 8888 --backends 8889,8890,8891

# Terminal 6+: Start Clients (via Load Balancer)
cd src
python client.py
# Jalankan di terminal berbeda untuk client tambahan
```

### Skenario B: Single Server dengan Redis

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Single Server
cd src
python server_thread_http.py --port 8889 --required-players 2

# Terminal 3+: Start Clients (Direct Connection)
cd src
python client.py --direct-connection --server-ports 8889
```

---

## **MODE 2: TANPA REDIS** (Simple)

### Single Server In-Memory Mode

```bash
# Terminal 1: Start Server (Tanpa Redis)
cd src
python server_thread_http.py --port 8889 --required-players 2
# Server akan otomatis fallback ke in-memory mode

# Terminal 2+: Start Clients
cd src
python client.py --direct-connection --server-ports 8889
```

**Output yang diharapkan:**

```
🔗 Testing Redis connection...
⚠️ Redis connection failed: Error 10061 connecting to 127.0.0.1:6379
🔄 Falling back to in-memory mode...
💾 Running with in-memory backend
🚀 server1 started on 0.0.0.0:8889
💾 Mode: In-memory fallback
🎯 Required players: 2 (from config)
```

---

## Parameter & Opsi

### Server Options

```bash
python server_thread_http.py [OPTIONS]

--port INTEGER              # Port server (default: 8889)
--redis-host TEXT           # Redis host (default: 127.0.0.1)
--redis-port INTEGER        # Redis port (default: 6379)
--required-players INTEGER  # Jumlah pemain untuk mulai game
--server-id TEXT            # ID server untuk logging (default: server1)
```

### Load Balancer Options

```bash
python load_balancer.py [OPTIONS]

--port INTEGER    # Port load balancer (default: 8888)
--backends TEXT   # Port backend servers (default: 8889,8890,8891)
--host TEXT       # Host backend server (default: 127.0.0.1)
```

### Client Options

```bash
python client.py [OPTIONS]

# Load Balancer Mode (default)
python client.py

# Direct Connection Mode
python client.py --direct-connection --server-ports 8889

# Multiple Server Ports (Round Robin)
python client.py --direct-connection --server-ports 8889,8890,8891

# Custom Server Host
python client.py --direct-connection --server-host 192.168.1.100 --server-ports 8889
```

## Alur Permainan

```
Input Username → Instructions → Lobby → Countdown → Game → Final Score → Restart/Exit
```

1. **Input username** (max 16 karakter)
2. **Baca instruksi** permainan
3. **Masuk lobby** menunggu pemain lain
4. **Countdown otomatis** jika pemain cukup
5. **Main 10 soal** Stroop Color
6. **Lihat skor akhir** & ranking
7. **Pilih restart** atau exit

## Aturan Permainan

- **Objektif:** Pilih warna dari teks yang ditampilkan, **BUKAN arti katanya**.
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
- **First correct:** +50 poin bonus

## Arsitektur Teknis

### Dengan Redis (Scalable)

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

### Tanpa Redis (Simple)

```
        ┌─────────────┐
        │   Client 1  │
        └─────┬───────┘
              │
        ┌─────▼───────┐    ┌─────────────────┐
        │   Client 2  ├───►│  Single Server  │
        └─────────────┘    │   Port 8889     │
                           │  In-Memory      │
        ┌─────────────┐    │     State       │
        │   Client N  │    └─────────────────┘
        └─────┬───────┘
              │
              └────────────┘
```

### Komponen Utama

- **game_state.py**: State game di Redis, thread-safe, heartbeat, scalable
- **load_balancer.py**: Round robin, health check, failover, proxy
- **http.py**: Game logic, REST API, **auto-fallback** ke in-memory jika Redis down
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

## Quick Start Examples

### 🎯 **Development (2 pemain, tanpa Redis)**

```bash
# Terminal 1
cd src && python server_thread_http.py --port 8889 --required-players 2

# Terminal 2-3
cd src && python client.py --direct-connection --server-ports 8889
```

### 🏭 **Production (dengan Redis, Load Balancer)**

```bash
# Terminal 1: Redis
redis-server

# Terminal 2-4: Servers
cd src
python server_thread_http.py --port 8889 --server-id server1 --required-players 3
python server_thread_http.py --port 8890 --server-id server2
python server_thread_http.py --port 8891 --server-id server3

# Terminal 5: Load Balancer
cd src && python load_balancer.py --port 8888 --backends 8889,8890,8891

# Terminal 6+: Clients
cd src && python client.py
```

## Troubleshooting

| Problem                       | Solusi                                            |
| ----------------------------- | ------------------------------------------------- |
| "Failed to connect to server" | Pastikan server jalan di port yang benar          |
| Font/asset not found          | Cek file di folder `assets/`                      |
| Game lag/desync               | Cek jaringan, restart server                      |
| Server crash                  | Cek log untuk error detail                        |
| **Redis connection failed**   | **Server otomatis fallback ke in-memory mode** ✅ |
| Port already in use           | Ganti port atau kill proses lama                  |
| No healthy backend servers    | Start backend server sebelum load balancer        |
| Load balancer not working     | **Gunakan `--direct-connection` untuk bypass**    |

## Performance & Scalability

### Mode Redis (Scalable)

- **Max players:** 100+ concurrent (tergantung hardware)
- **Servers:** 1-10 instances dengan load balancer
- **Response time:** <50ms (local), <200ms (remote)
- **Memory:** ~20MB per server + Redis

### Mode In-Memory (Simple)

- **Max players:** 10-20 concurrent (per server)
- **Servers:** 1 instance saja
- **Response time:** <30ms (local)
- **Memory:** ~30MB per server

## Monitoring & Logging

```bash
# Check server health
curl http://127.0.0.1:8889/server-stats

# Check load balancer
curl http://127.0.0.1:8888/server-stats

# Monitor Redis (jika digunakan)
redis-cli monitor
```

## Contributing

- Ikuti PEP 8
- Nama variabel bahasa Inggris, komentar bahasa Indonesia
- Logging terstruktur
- Test multi-client sebelum PR
- Test both Redis and non-Redis modes

---

## 🎯 **Rekomendasi Deployment**

| Scenario                       | Mode                  | Command                                             |
| ------------------------------ | --------------------- | --------------------------------------------------- |
| **Development**                | In-memory             | `python server_thread_http.py --port 8889`          |
| **Small Game (2-5 players)**   | In-memory             | `python server_thread_http.py --required-players 5` |
| **Medium Game (5-20 players)** | Redis + Single Server | `redis-server` + `python server_thread_http.py`     |
| **Large Game (20+ players)**   | Redis + Load Balancer | Full setup dengan multiple servers                  |

**🎮 Selamat bermain Stroop Color Game!**

Untuk support atau bug report, silakan buka issue di repository ini.
