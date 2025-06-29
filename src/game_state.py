import redis
import json
import time
import threading
from typing import Dict, Any, Optional

class RedisGameState:
    def __init__(self, host='127.0.0.1', port=6379, db=0, required_players=None):
        self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK", "GRAY", "ORANGE", "PINK", "BROWN"]
        self.game_lock = threading.Lock()
        
        # Add connection pool for better performance
        self.redis_client.connection_pool.connection_kwargs['socket_keepalive'] = True
        self.redis_client.connection_pool.connection_kwargs['socket_keepalive_options'] = {}
        
        # Cache frequently accessed data
        self._config_cache = {}
        self._last_cache_time = 0
        self._cache_timeout = 5  # Cache config for 5 seconds
        
        # Redis keys
        self.GAME_KEY = "stroopcolor:game_state"
        self.PLAYERS_KEY = "stroopcolor:players"
        self.SCORES_KEY = "stroopcolor:scores"
        self.HEARTBEAT_KEY = "stroopcolor:heartbeat"
        self.CONFIG_KEY = "stroopcolor:config"
        
        # Initialize game configuration first
        self._init_game_config(required_players)
        
        # Initialize game state if not exists
        self._init_game_state()
        
        # Start heartbeat monitor with longer intervals
        threading.Thread(target=self.heartbeat_monitor, daemon=True).start()

    def _init_game_config(self, required_players=None):
        """Initialize game configuration in Redis"""
        # Check if config already exists
        if not self.redis_client.exists(self.CONFIG_KEY):
            # Set default config
            default_config = {
                'required_players': required_players or 2,
                'max_questions': 10,
                'question_duration': 10,
                'countdown_duration': 3,
                'timesup_duration': 3,
                'round_completed_duration': 2.0,
                'heartbeat_timeout': 30
            }
            self.redis_client.hset(self.CONFIG_KEY, mapping={k: json.dumps(v) for k, v in default_config.items()})
            print(f"🔧 Redis config initialized - Required players: {default_config['required_players']}")
        else:
            # Config exists, optionally update required_players if provided
            if required_players is not None:
                current_required = self.get_config_field('required_players')
                if current_required != required_players:
                    self.set_config_field('required_players', required_players)
                    print(f"🔧 Updated required players: {current_required} → {required_players}")
            
            current_required = self.get_config_field('required_players')
            print(f"🔧 Using existing Redis config - Required players: {current_required}")

    def get_config_field(self, field: str) -> Any:
        """Get a specific field from configuration with caching"""
        now = time.time()
        
        # Use cache if available and not expired
        if (field in self._config_cache and 
            now - self._last_cache_time < self._cache_timeout):
            return self._config_cache[field]
        
        # Refresh cache
        try:
            config = self.redis_client.hgetall(self.CONFIG_KEY)
            self._config_cache = {k: json.loads(v) for k, v in config.items()}
            self._last_cache_time = now
        except Exception as e:
            print(f"Redis config error: {e}")
            return self._config_cache.get(field)
        
        return self._config_cache.get(field)

    def set_config_field(self, field: str, value: Any):
        """Set a specific field in configuration"""
        self.redis_client.hset(self.CONFIG_KEY, field, json.dumps(value))

    def get_required_players(self) -> int:
        """Get required players from cached config"""
        return self.get_config_field('required_players') or 2

    def _init_game_state(self):
        """Initialize game state in Redis if not exists"""
        if not self.redis_client.exists(self.GAME_KEY):
            initial_state = {
                'question_id_counter': 0,
                'current_question': None,
                'current_correct_answer': None,
                'game_started': False,
                'countdown_started': False,
                'countdown_start_time': None,
                'game_start_time': None,
                'question_start_time': None,
                'current_question_number': 0,
                'game_finished': False,
                'first_correct_answer': None,
                'timesup_state': False,
                'timesup_start_time': None,
                'round_completed_state': False,
                'round_completed_start_time': None,
                'advancing_question': False
            }
            self.redis_client.hset(self.GAME_KEY, mapping={k: json.dumps(v) for k, v in initial_state.items()})
            print("🔄 Redis game state initialized")

    def get_game_state_field(self, field: str) -> Any:
        """Get a specific field from game state with error handling"""
        try:
            value = self.redis_client.hget(self.GAME_KEY, field)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"❌ Error getting game state field '{field}': {e}")
            return None

    def set_game_state_field(self, field: str, value: Any):
        """Set a specific field in game state"""
        self.redis_client.hset(self.GAME_KEY, field, json.dumps(value))

    def get_game_state(self) -> Dict[str, Any]:
        """Get entire game state"""
        state = self.redis_client.hgetall(self.GAME_KEY)
        return {k: json.loads(v) for k, v in state.items()}

    def update_game_state(self, updates: Dict[str, Any]):
        """Update multiple game state fields atomically"""
        try:
            # Convert all values to JSON strings
            json_updates = {k: json.dumps(v) for k, v in updates.items()}
            self.redis_client.hset(self.GAME_KEY, mapping=json_updates)
            print(f"✅ Updated game state: {list(updates.keys())}")
        except Exception as e:
            print(f"❌ Error updating game state: {e}")
            raise

    def get_connected_players(self) -> set:
        """Get set of connected players"""
        try:
            return set(self.redis_client.smembers(self.PLAYERS_KEY))
        except Exception as e:
            print(f"❌ Error getting connected players: {e}")
            return set()

    def add_player(self, player_id: str):
        """Add player to connected players set"""
        self.redis_client.sadd(self.PLAYERS_KEY, player_id)
        self.redis_client.hset(self.SCORES_KEY, player_id, 0)
        self.redis_client.hset(self.HEARTBEAT_KEY, player_id, time.time())

    def remove_player(self, player_id: str):
        """Remove player from all sets"""
        self.redis_client.srem(self.PLAYERS_KEY, player_id)
        self.redis_client.hdel(self.SCORES_KEY, player_id)
        self.redis_client.hdel(self.HEARTBEAT_KEY, player_id)
        self.redis_client.srem("stroopcolor:answered_players", player_id)

    def get_player_scores(self) -> Dict[str, int]:
        """Get all player scores"""
        try:
            scores = self.redis_client.hgetall(self.SCORES_KEY)
            return {k: int(v) for k, v in scores.items()} if scores else {}
        except Exception as e:
            print(f"❌ Error getting player scores: {e}")
            return {}

    def update_player_score(self, player_id: str, score: int):
        """Update player score"""
        self.redis_client.hset(self.SCORES_KEY, player_id, score)

    def get_answered_players(self) -> set:
        """Get set of players who answered current question"""
        try:
            return set(self.redis_client.smembers("stroopcolor:answered_players"))
        except Exception as e:
            print(f"❌ Error getting answered players: {e}")
            return set()

    def add_answered_player(self, player_id: str):
        """Add player to answered players set"""
        self.redis_client.sadd("stroopcolor:answered_players", player_id)

    def clear_answered_players(self):
        """Clear answered players set"""
        self.redis_client.delete("stroopcolor:answered_players")

    def update_heartbeat(self, player_id: str):
        """Update player heartbeat timestamp"""
        self.redis_client.hset(self.HEARTBEAT_KEY, player_id, time.time())

    def heartbeat_monitor(self):
        """Monitor player heartbeats with longer intervals"""
        while True:
            time.sleep(10)  # Reduced frequency from 5 to 10 seconds
            try:
                with self.game_lock:
                    self.check_disconnected_players()
            except Exception as e:
                print(f"Heartbeat monitor error: {e}")

    def check_disconnected_players(self):
        """Optimized disconnection check"""
        try:
            now = time.time()
            timeout = self.get_config_field('heartbeat_timeout') or 30
            
            # Get all heartbeats in one call
            heartbeats = self.redis_client.hgetall(self.HEARTBEAT_KEY)
            
            disconnected = []
            for player_id, last_heartbeat in heartbeats.items():
                try:
                    if now - float(last_heartbeat) > timeout:
                        disconnected.append(player_id)
                except (ValueError, TypeError):
                    disconnected.append(player_id)  # Invalid heartbeat data
            
            # Batch remove disconnected players
            if disconnected:
                pipe = self.redis_client.pipeline()
                for player_id in disconnected:
                    pipe.srem(self.PLAYERS_KEY, player_id)
                    pipe.hdel(self.SCORES_KEY, player_id)
                    pipe.hdel(self.HEARTBEAT_KEY, player_id)
                    pipe.srem("stroopcolor:answered_players", player_id)
                    print(f"Player {player_id} disconnected (timeout)")
                pipe.execute()
            
            # Check if game should reset
            connected_players = self.get_connected_players()
            game_started = self.get_game_state_field('game_started')
            countdown_started = self.get_game_state_field('countdown_started')
            
            if not connected_players and (game_started or countdown_started):
                print("All players disconnected! Resetting game...")
                self.reset_game_internal()
                return True
            
            return bool(disconnected)
        except Exception as e:
            print(f"Error checking disconnected players: {e}")
            return False

    def reset_game_internal(self):
        """Reset game state while preserving connected players"""
        players = self.get_connected_players()
        now = time.time()
        
        # Reset game state
        reset_state = {
            'question_id_counter': 0,
            'current_question': None,
            'current_correct_answer': None,
            'game_started': False,
            'countdown_started': False,
            'countdown_start_time': None,
            'game_start_time': None,
            'question_start_time': None,
            'current_question_number': 0,
            'game_finished': False,
            'first_correct_answer': None,
            'timesup_state': False,
            'timesup_start_time': None,
            'round_completed_state': False,
            'round_completed_start_time': None,
            'advancing_question': False
        }
        self.update_game_state(reset_state)
        
        # Reset scores
        for player_id in players:
            self.redis_client.hset(self.SCORES_KEY, player_id, 0)
            self.redis_client.hset(self.HEARTBEAT_KEY, player_id, now)
        
        # Clear answered players
        self.clear_answered_players()
        
        print(f"🔄 Game reset - ready for {len(players)} players!")

    def generate_new_question(self):
        """Generate a new question and update game state"""
        import random
        
        # Increment question counter
        current_counter = self.get_game_state_field('question_id_counter') or 0
        new_counter = current_counter + 1
        self.set_game_state_field('question_id_counter', new_counter)
        
        # Generate question
        text = random.choice(self.COLOR_NAMES)
        correct = random.choice([c for c in self.COLOR_NAMES if c != text])
        options = random.sample([c for c in self.COLOR_NAMES if c != correct], 4) + [correct]
        random.shuffle(options)
        
        question = {
            "question_id": new_counter,
            "text": text,
            "text_color": correct,
            "options": options
        }
        
        # Update game state
        self.update_game_state({
            'current_question': question,
            'current_correct_answer': correct,
            'first_correct_answer': None
        })
        
        # Clear answered players for new question
        self.clear_answered_players()
        
        print(f"✨ Generated Q{new_counter}: '{text}' in {correct}")
        return question

    def cleanup(self):
        """Clean up Redis connections"""
        try:
            self.redis_client.close()
            print("Redis connection closed")
        except Exception as e:
            print(f"Error closing Redis connection: {e}")