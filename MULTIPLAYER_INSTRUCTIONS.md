# Color Tap Battle - Multiplayer Game

## How to Run the Multiplayer Game

1. **Start the Server**

   ```bash
   cd src
   python server.py
   ```

   The server will start on `http://127.0.0.1:8080`

2. **Start Client Players**
   Open multiple terminal windows and run:
   ```bash
   cd src
   python client.py
   ```
   Each player will be prompted to enter their player ID.

## Game Rules

- The game requires **at least 2 players** to start
- Players will see a lobby screen until enough players join
- Once 2+ players are connected, the game starts automatically
- All players see synchronized questions and timers
- Each question lasts **10 seconds** (now properly synchronized!)
- Players compete to answer 10 questions correctly
- Scoring: 100 points per correct answer
- Real-time leaderboard shows all players' scores

## Recent Fixes

### Timer Synchronization ✅

- Fixed timer countdown from 10 seconds properly synchronized across all clients
- Timer now counts down smoothly from 10 to 0 seconds
- Timer color changes to red when ≤3 seconds remaining

### Game Restart ✅

- After game finishes, starting new clients automatically resets the game
- No more "game already finished" errors
- Clean slate for each new game session

### Task Processing Model ✅

- **Multi-threaded Flask Server**: Uses `threaded=True` for concurrent request handling
- **Thread-per-request**: Each client request handled in separate thread
- **Shared game state**: Thread-safe access to centralized game state
- **No process pools**: Simple threading model for this application scale

### First Answer Bonus ✅

- First player to answer correctly gets **+150 points** (100 base + 50 bonus)
- Other correct answers still get **+100 points**
- Visual feedback shows "First!" with golden color popup

### Smart Question Progression ✅

- **Auto-advance**: Game moves to next question when ALL players have answered
- **Time's Up!**: Shows message when timer expires for players who didn't answer
- **Visual indicators**: Shows "All players answered! Moving to next..." status

## Technical Details

- **Server**: Multi-threaded Flask with thread-per-request model
- **Client**: Pygame with HTTP polling for real-time updates
- **Synchronization**: Server-side timing with client polling every frame
- **State Management**: Centralized game state with automatic reset
- **Concurrency**: Thread-safe operations for multiple simultaneous players

## Architecture

```
[Client 1] ←→ HTTP ←→ [Flask Server] ←→ HTTP ←→ [Client 2]
                          ↓
                    [Game State]
                    (Thread-safe)
```

## Testing the Fixes

1. Start the server (you'll see "Task Processing Model: Multi-threaded")
2. Start 2+ clients in separate terminals
3. Watch the synchronized 10-second countdown timer
4. After game ends, start new clients - game will auto-reset
5. Timer should count down smoothly: 10→9→8→7→6→5→4→3→2→1→0
