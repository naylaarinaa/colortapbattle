# Color Tap Battle - Multiplayer Game

## Deskripsi

Color Tap Battle adalah permainan multiplayer real-time berbasis **Stroop Color Game** yang dibangun dengan Python. Permainan menggunakan server HTTP custom dan client pygame untuk pengalaman gaming yang tersinkronisasi dengan sempurna.

## Struktur Proyek

```
colortapbattle/
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
│   └── roundcompleted.png           # Popup ronde selesai
├── src/
│   ├── client.py                    # Aplikasi client pygame
│   ├── http.py                      # Server HTTP dan game logic
│   ├── server_thread_http.py        # Multi-threaded HTTP server
├── requirements.txt                 # Dependensi Python
├── .gitignore                      # Git ignore file
└── README.md                       # Dokumentasi proyek
```

## Instalasi dan Setup

### 1. Persyaratan Sistem

- Python 3.7 atau lebih baru
- pygame untuk rendering client
- Koneksi internet untuk multiplayer

### 2. Instalasi Dependensi

```bash
pip install -r requirements.txt
```

### 3. Verifikasi Asset

Pastikan semua file asset berada di folder `assets/`:

- Font files: `BalsamiqSans-Regular.ttf`, `LuckiestGuy-Regular.ttf`
- Background images: `main.png`, `username.png`, `instructions.png`, `waiting_lobby.png`,`finalscore.png`
- Popup images: `correct.png`, `wrong.png`, `timesup.png`, `roundcompleted.png`, `winner.png`

## Cara Menjalankan Game

### 1. Start Server

Jalankan server HTTP di terminal:

```bash
cd src
python server_thread_http.py [jumlah_pemain]
```

**Parameter jumlah pemain:**

- Default (tanpa parameter): 2 pemain
- Custom: `python server_thread_http.py 4` (untuk 4 pemain)
- Range: 2-10 pemain

**Output server yang berhasil:**

```
Starting Color Tap Battle Server...
Required players to start: 2
Press Ctrl+C to stop the server
2024-06-29 14:30:15 [INFO] Color Tap Battle Server started on 0.0.0.0:8889
```

### 2. Start Client (Pemain)

Di terminal terpisah, jalankan client untuk setiap pemain:

```bash
cd src
python client.py
```

**Flow client:**

1. Input username (max 16 karakter)
2. Baca instruksi permainan
3. Masuk lobby menunggu pemain lain
4. Countdown otomatis ketika pemain cukup
5. Mulai bermain!

### 3. Gameplay Flow

```
Username Input → Instructions → Lobby → Countdown → Game → Results
```

## Aturan Permainan

### 🎯 Objektif

Pemain harus **mencocokkan nama warna dengan warna text** yang ditampilkan, bukan dengan makna kata.

**Contoh:**

- Text "RED" ditampilkan dalam warna BLUE
- Jawaban yang benar adalah "BLUE" (warna text-nya)
- Bukan "RED" (makna kata-nya)

### ⚡ Sistem Poin

| Kondisi                    | Poin                                |
| -------------------------- | ----------------------------------- |
| Jawaban benar              | Base points + Time bonus            |
| Jawaban pertama yang benar | Base points + Time bonus + 50 bonus |
| Jawaban salah              | 0 poin                              |
| Tidak menjawab             | 0 poin                              |

**Time bonus calculation:**

- Time remaining × 10 points
- Contoh: 7 detik tersisa = 70 poin
- First correct bonus: +50 poin tambahan

### 🎮 Mekanik Game

- **Timer per soal**: 10 detik
- **Total soal**: 10 pertanyaan
- **Auto advance**: Lanjut otomatis jika semua pemain sudah menjawab
- **Real-time leaderboard**: Update skor langsung
- **Synchronized gameplay**: Semua pemain melihat soal yang sama

### 🏆 Special Screens

- **Time's Up**: Muncul jika waktu habis
- **Round Completed**: Muncul jika semua pemain sudah menjawab
- **Popup Feedback**: Visual feedback untuk jawaban benar/salah

## Arsitektur Teknis

### 🌐 Network Architecture

```
Client 1 ←→ HTTP/JSON ←→ Multi-threaded Server ←→ HTTP/JSON ←→ Client N
                              ↓
                         Game State Manager
                         (Thread-safe)
```

### 🔧 Komponen Utama

#### Server Side (`http.py`)

- **HttpServer**: Core game logic dan state management
- **Thread-safe operations**: Concurrent player handling
- **Heartbeat monitoring**: Auto-disconnect idle players
- **Question generation**: Random color/text combinations
- **Score calculation**: Time-based + bonus points

#### Network Layer (`server_thread_http.py`)

- **Multi-threaded HTTP server**: Handle multiple connections
- **Request routing**: HTTP method dan endpoint handling
- **Connection management**: Graceful client connect/disconnect
- **Error handling**: Network timeouts dan failures

#### Client Side (`client.py`)

- **Pygame rendering**: 60 FPS smooth gameplay
- **HTTP communication**: RESTful API calls ke server
- **UI/UX components**: Animated buttons, input fields, popups
- **Asset management**: Font dan image loading dengan fallbacks
- **State synchronization**: Real-time game state updates

### 📡 API Endpoints

| Method | Endpoint              | Purpose                     |
| ------ | --------------------- | --------------------------- |
| `POST` | `/join`               | Join game lobby             |
| `GET`  | `/status?player_id=X` | Get game status (heartbeat) |
| `GET`  | `/question`           | Get current question        |
| `POST` | `/answer`             | Submit answer               |
| `POST` | `/reset`              | Reset game (admin)          |

### 🎨 Asset System

- **Fallback mechanism**: Jika asset tidak ditemukan, gunakan rendering manual
- **Scalable graphics**: Images di-scale sesuai resolusi game
- **Font loading**: Custom fonts dengan system font sebagai backup

## Fitur Lanjutan

### 🔄 Auto-Reset System

- Game otomatis reset setelah selesai
- Client baru bisa langsung join tanpa restart server
- Clean state untuk setiap session baru

### ⏱️ Perfect Synchronization

- Server-side timing authority
- Client polling untuk real-time updates
- Consistent countdown di semua client

### 🧵 Thread Safety

- Mutex locks untuk shared game state
- Atomic operations untuk score updates
- Safe concurrent player management

### 💔 Disconnection Handling

- Auto-detect player timeouts
- Graceful player removal
- Game continues dengan remaining players

### 📊 Logging System

- Structured logging untuk debugging
- Network communication tracking
- Game event monitoring
- Performance metrics

## Development & Debugging

### 🔍 Logs

**Server logs:**

```
2024-06-29 14:30:15 [INFO] 🎮 Game started - Question 1
2024-06-29 14:30:15 [INFO] ✨ Generated Q1: 'RED' in BLUE
2024-06-29 14:30:17 [INFO] 📝 Player Alice answered: BLUE for question 1
2024-06-29 14:30:17 [INFO] ✅ Correct! Player Alice earned 85 points
```

**Client logs:**

```
14:30:15 [INFO] 🎮 Color Tap Battle Client Starting...
14:30:16 [INFO] 🔗 Client initialized for player: Alice
14:30:17 [INFO] ✅ Joined successfully! Players: 1/2
14:30:19 [INFO] ⏰ Countdown started (3s)
14:30:22 [INFO] 🎮 Game started - Question 1
```

### 🛠️ Testing

**Multi-player testing:**

```bash
# Terminal 1: Start server
python server_thread_http.py 3

# Terminal 2-4: Start clients
python client.py  # Player 1
python client.py  # Player 2
python client.py  # Player 3
```

### 🐛 Common Issues

| Problem                       | Solution                              |
| ----------------------------- | ------------------------------------- |
| "Failed to connect to server" | Pastikan server running di port 8889  |
| Font/asset not found          | Check files di folder `assets/`       |
| Game lag/desync               | Check network latency, restart server |
| Server crash                  | Check logs untuk error details        |

## Performance & Scalability

### 📈 Specifications

- **Max players**: 10 concurrent
- **Response time**: <100ms for local network
- **Memory usage**: ~50MB per client
- **CPU usage**: Minimal (single-threaded game logic)

### ⚡ Optimizations

- **Efficient polling**: 60 FPS client, smart server requests
- **Asset caching**: Images loaded once, reused
- **Network optimization**: JSON compression, minimal payloads
- **Memory management**: Proper cleanup dan garbage collection

## Contributing

### 📝 Code Style

- Python PEP 8 compliance
- Meaningful variable names dalam bahasa Inggris
- Comments dalam bahasa Indonesia untuk clarity
- Structured logging dengan emoji indicators

### 🔄 Development Workflow

1. Fork repository
2. Create feature branch
3. Test dengan multiple clients
4. Update documentation
5. Submit pull request

### 🧪 Testing Checklist

- [ ] Server starts tanpa error
- [ ] Multiple clients dapat connect
- [ ] Game synchronization berfungsi
- [ ] Scoring system akurat
- [ ] Disconnection handling
- [ ] Asset loading dengan fallbacks

## License

Proyek ini dibuat untuk keperluan pembelajaran **Pemrograman Jaringan Semester 6**.

---

**🎮 Selamat bermain Color Tap Battle!**

Untuk support atau bug reports, silakan buka issue di repository ini.
