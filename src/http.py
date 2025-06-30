import sys, os, threading, time, random, json
from glob import glob
from datetime import datetime
from game_state import RedisGameState

class HttpServer:
    def __init__(self, redis_host='127.0.0.1', redis_port=6379, required_players=None):
        self.types = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.txt': 'text/plain', '.html': 'text/html'}
        self.question_lock = threading.Lock()
        
        # Initialize Redis game state
        try:
            self.game_state = RedisGameState(
                host=redis_host, 
                port=redis_port, 
                required_players=required_players  # Only for initial setup
            )
            # Get required players from Redis (single source of truth)
            self.REQUIRED_PLAYERS = self.game_state.get_required_players()
            print(f"🔗 Connected to Redis at {redis_host}:{redis_port}")
            print(f"🎯 Required players (from Redis): {self.REQUIRED_PLAYERS}")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            print("🔄 Falling back to in-memory state...")
            self._init_fallback_state(required_players or 2)

    def _init_fallback_state(self, required_players):
        """Fallback to original in-memory state if Redis fails"""
        self.REQUIRED_PLAYERS = required_players
        self.game_state = {
            'question_id_counter': 0, 'current_question': None, 'current_correct_answer': None,
            'player_scores': {}, 'connected_players': set(), 'game_started': False,
            'countdown_started': False, 'countdown_start_time': None, 'countdown_duration': 3,
            'game_start_time': None, 'question_start_time': None, 'current_question_number': 0,
            'max_questions': 10, 'question_duration': 10, 'players_ready': set(),
            'game_finished': False, 'first_correct_answer': None, 'answered_players': set(),
            'last_heartbeat': {}, 'heartbeat_timeout': 30, 'timesup_state': False,
            'timesup_start_time': None, 'timesup_duration': 3, 'round_completed_state': False,
            'round_completed_start_time': None, 'round_completed_duration': 2.0, 'advancing_question': False,
        }
        self._use_redis = False

    def get_question(self):
        if hasattr(self.game_state, 'get_game_state_field'):  # Redis mode
            game_started = self.game_state.get_game_state_field('game_started')
            current_question = self.game_state.get_game_state_field('current_question')
            if not game_started or not current_question:
                return {'error': 'Game not started' if not game_started else 'No current question'}, 400
            
            question_start_time = self.game_state.get_game_state_field('question_start_time')
            question_duration = self.game_state.get_game_state_field('question_duration') or 10
            current_question_number = self.game_state.get_game_state_field('current_question_number') or 0
            max_questions = self.game_state.get_game_state_field('max_questions') or 10
        else:  # Fallback mode
            gs = self.game_state
            if not gs['game_started'] or not gs['current_question']:
                return {'error': 'Game not started' if not gs['game_started'] else 'No current question'}, 400
            current_question = gs['current_question']
            question_start_time = gs['question_start_time']
            question_duration = gs['question_duration']
            current_question_number = gs['current_question_number']
            max_questions = gs['max_questions']
        
        now, elapsed = time.time(), time.time() - question_start_time
        resp = current_question.copy()
        resp.update({
            'time_remaining': max(0, question_duration - elapsed),
            'question_number': current_question_number,
            'max_questions': max_questions
        })
        return resp, 200

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = [f"HTTP/1.0 {kode} {message}\r\n", f"Date: {tanggal}\r\n", "Connection: close\r\n",
                "Server: myserver/1.0\r\n", f"Content-Length: {len(messagebody)}\r\n"] + \
               [f"{k}:{headers[k]}\r\n" for k in headers] + ["\r\n"]
        messagebody = messagebody.encode() if not isinstance(messagebody, bytes) else messagebody
        return ''.join(resp).encode() + messagebody

    def proses(self, data):
        try:
            lines = data.split("\r\n")
            method, object_address = lines[0].split()[:2]
            headers = [n for n in lines[1:] if n]
            body = "\r\n".join(lines[lines.index("")+1:]) if "" in lines else ""
            method = method.upper()
            if method == 'GET': return self.http_get(object_address, headers)
            if method == 'POST': return self.http_post(object_address, headers, body)
            return self.response(400, 'Bad Request', '', {})
        except Exception:
            return self.response(400, 'Bad Request', '', {})

    def http_get(self, object_address, headers):
        if object_address.startswith('/status'):
            player_id = 'heartbeat'
            if '?' in object_address:
                for param in object_address.split('?', 1)[1].split('&'):
                    if param.startswith('player_id='):
                        player_id = param.split('=', 1)[1]
            result = self.get_game_status(player_id)
            return self.response(200, 'OK', json.dumps(result), {'Content-type': 'application/json'})
        
        # NEW: Server stats endpoint for load balancing
        if object_address == '/server-stats':
            stats = self.get_server_stats()
            return self.response(200, 'OK', json.dumps(stats), {'Content-type': 'application/json'})
        
        if object_address == '/question':
            result, code = self.get_question()
            return self.response(code, 'OK' if code == 200 else 'Bad Request', json.dumps(result), {'Content-type': 'application/json'})
        
        if object_address == '/': return self.response(200, 'OK', 'Ini Adalah web Server percobaan', {})
        if object_address == '/video': return self.response(302, 'Found', '', {'location': 'https://youtu.be/katoxpnTf04'})
        if object_address == '/santai': return self.response(200, 'OK', 'santai saja', {})
        
        files, thedir, fname = glob('./*'), './', object_address[1:]
        if thedir + fname not in files:
            return self.response(404, 'Not Found', '', {})
        with open(thedir + fname, 'rb') as fp:
            isi = fp.read()
        fext = os.path.splitext(thedir + fname)[1]
        content_type = self.types.get(fext, 'application/octet-stream')
        return self.response(200, 'OK', isi, {'Content-type': content_type})

    def http_post(self, object_address, headers, body):
        if object_address == '/join':
            data = json.loads(body) if body else {}
            result = self.join_game(data)
            return self.response(200, 'OK', json.dumps(result), {'Content-type': 'application/json'})
        if object_address == '/answer':
            data = json.loads(body) if body else {}
            result = self.post_answer(data)
            return self.response(200, 'OK', json.dumps(result), {'Content-type': 'application/json'})
        if object_address == '/reset':
            self.reset_game()
            return self.response(200, 'OK', json.dumps({'status': 'reset', 'message': 'Game has been reset'}), {'Content-type': 'application/json'})
        return self.response(200, 'OK', "kosong", {})

    def start_countdown(self):
        if hasattr(self.game_state, 'update_game_state'):  # Redis mode
            connected_players = self.game_state.get_connected_players()
            self.game_state.update_game_state({
                'countdown_started': True,
                'countdown_start_time': time.time()
            })
            print(f"🔻 Starting countdown with {len(connected_players)} players")
        else:  # Fallback mode
            gs = self.game_state
            gs['countdown_started'], gs['countdown_start_time'] = True, time.time()
            print(f"🔻 Starting countdown with {len(gs['connected_players'])} players")

    def start_game(self):
        now = time.time()
        if hasattr(self.game_state, 'update_game_state'):  # Redis mode
            new_question = self.game_state.generate_new_question()
            self.game_state.update_game_state({
                'game_started': True,
                'countdown_started': False,
                'game_start_time': now,
                'current_question_number': 1,
                'question_start_time': now
            })
            print("🎮 Game started! First question generated.")
        else:  # Fallback mode
            gs = self.game_state
            gs.update({
                'game_started': True, 'countdown_started': False, 'game_start_time': now,
                'current_question_number': 1, 'current_question': self.generate_new_question_fallback(),
                'question_start_time': now
            })
            print("🎮 Game started! First question generated.")

    def check_and_start_game(self):
        if hasattr(self.game_state, 'get_connected_players'):  # Redis mode
            connected_players = self.game_state.get_connected_players()
            countdown_started = self.game_state.get_game_state_field('countdown_started')
            game_started = self.game_state.get_game_state_field('game_started')
            # Get required players from Redis config
            required_players = self.game_state.get_required_players()
            if not countdown_started and not game_started and len(connected_players) >= required_players:
                self.start_countdown()
        else:  # Fallback mode
            gs = self.game_state
            if not gs['countdown_started'] and not gs['game_started'] and len(gs['connected_players']) >= self.REQUIRED_PLAYERS:
                self.start_countdown()

    def join_game(self, data):
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        print(f"Player {player_id} attempting to join...")
        
        if hasattr(self.game_state, 'add_player'):  # Redis mode
            game_finished = self.game_state.get_game_state_field('game_finished')
            if game_finished:
                print("Previous game finished, resetting for new players...")
                self.game_state.reset_game_internal()
            
            self.game_state.add_player(player_id)
            connected_players = self.game_state.get_connected_players()
            required_players = self.game_state.get_required_players()  # From Redis
            print(f"Player {player_id} joined. Total players: {len(connected_players)}")
            self.check_and_start_game()
            return {'status': 'joined', 'player_count': len(connected_players), 'required_players': required_players}
        else:  # Fallback mode
            gs = self.game_state
            if gs['game_finished']:
                print("Previous game finished, resetting for new players...")
                self.reset_game_internal_fallback()
            gs['connected_players'].add(player_id)
            gs['player_scores'][player_id] = 0
            gs['last_heartbeat'][player_id] = time.time()
            print(f"Player {player_id} joined. Total players: {len(gs['connected_players'])}")
            self.check_and_start_game()
            return {'status': 'joined', 'player_count': len(gs['connected_players']), 'required_players': self.REQUIRED_PLAYERS}

    def get_game_status(self, player_id):
        """Get game status - main entry point"""
        try:
            if hasattr(self.game_state, 'get_connected_players'):  # Redis mode
                return self._get_game_status_redis(player_id)
            else:  # Fallback mode
                return self._get_game_status_fallback(player_id)
        except Exception as e:
            print(f"❌ Fatal error in get_game_status: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error', 
                'message': f'Server error: {str(e)}',
                'player_count': 0,
                'required_players': 2,
                'players_needed': 2,
                'game_started': False,
                'countdown_started': False
            }

    def _get_game_status_redis(self, player_id):
        """Fixed game status using Redis backend with proper error handling"""
        now = time.time()
        
        # Test Redis connection first
        try:
            self.game_state.redis_client.ping()
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return {'status': 'error', 'message': f'Redis connection failed: {str(e)}'}
        
        # Batch get common fields with FIXED pipeline handling
        try:
            # Use individual calls instead of pipeline to avoid errors
            countdown_started = self.game_state.get_game_state_field('countdown_started') or False
            game_started = self.game_state.get_game_state_field('game_started') or False
            game_finished = self.game_state.get_game_state_field('game_finished') or False
            connected_players = self.game_state.get_connected_players()
            required_players = self.game_state.get_required_players()
            
            print(f"🔍 Redis data - Players: {len(connected_players)}, Required: {required_players}, Started: {game_started}, Countdown: {countdown_started}")
            
        except Exception as e:
            print(f"❌ Redis get error: {e}")
            # Return fallback data instead of error
            return {
                'status': 'waiting', 
                'player_count': 0, 
                'required_players': 2,
                'players_needed': 2,
                'game_started': False,
                'countdown_started': False,
                'message': f'Redis error (using fallback): {str(e)}'
            }
        
        # Update heartbeat only for real players, less frequently
        if (player_id != 'heartbeat' and 
            player_id in connected_players):
            try:
                # Update heartbeat every 5 seconds instead of every request
                last_update_key = f'_last_heartbeat_{player_id}'
                last_update = getattr(self, last_update_key, 0)
                if now - last_update > 5:
                    self.game_state.update_heartbeat(player_id)
                    setattr(self, last_update_key, now)
            except Exception as e:
                print(f"⚠️ Heartbeat update failed for {player_id}: {e}")
        
        # Early returns for non-game states
        if game_finished:
            try:
                final_scores = self.game_state.get_player_scores()
                return {'status': 'finished', 'game_started': True, 'final_scores': final_scores}
            except Exception as e:
                print(f"❌ Error getting final scores: {e}")
                return {'status': 'finished', 'game_started': True, 'final_scores': {}}
        
        # Countdown logic - FIXED
        if countdown_started and not game_started:
            try:
                countdown_start_time = self.game_state.get_game_state_field('countdown_start_time')
                countdown_duration = self.game_state.get_config_field('countdown_duration') or 3
                
                if countdown_start_time:
                    rem = max(0, countdown_duration - (now - countdown_start_time))
                    
                    if rem <= 0:
                        print("🚀 Countdown finished, starting game!")
                        self.start_game()
                        return {'status': 'playing', 'game_started': True}
                    else:
                        return {
                            'status': 'countdown', 
                            'countdown_remaining': rem,
                            'player_count': len(connected_players), 
                            'required_players': required_players,
                            'game_started': False, 
                            'countdown_started': True
                        }
                else:
                    print("❌ Countdown started but no start time found")
                    
            except Exception as e:
                print(f"❌ Countdown logic error: {e}")
        
        # Waiting for players
        if not game_started:
            return {
                'status': 'waiting', 
                'player_count': len(connected_players),
                'players_needed': max(0, required_players - len(connected_players)),
                'required_players': required_players, 
                'game_started': False,
                'countdown_started': countdown_started
            }
        
        # Game is running - get game state
        try:
            question_start_time = self.game_state.get_game_state_field('question_start_time') or now
            current_question_number = self.game_state.get_game_state_field('current_question_number') or 0
            timesup_state = self.game_state.get_game_state_field('timesup_state') or False
            round_completed_state = self.game_state.get_game_state_field('round_completed_state') or False
            answered_players = self.game_state.get_answered_players()
            player_scores = self.game_state.get_player_scores()
            
        except Exception as e:
            print(f"❌ Redis game state error: {e}")
            return {
                'status': 'playing', 'game_started': True, 
                'current_question_number': 1, 'max_questions': 10,
                'question_time_remaining': 10,
                'players': list(connected_players), 'scores': {},
                'all_answered': False, 'player_answered': False,
                'message': f'Game state error: {str(e)}'
            }
        
        all_answered = len(answered_players) >= len(connected_players) if connected_players else False
        question_duration = self.game_state.get_config_field('question_duration') or 10
        elapsed = now - question_start_time
        player_has_answered = player_id in answered_players if player_id != 'heartbeat' else False
        max_questions = self.game_state.get_config_field('max_questions') or 10
        
        # Time up logic
        if elapsed >= question_duration and not all_answered:
            if not timesup_state:
                print(f"⏰ Time's up for question {current_question_number}")
                self.game_state.update_game_state({
                    'timesup_state': True,
                    'timesup_start_time': now
                })
            
            timesup_start_time = self.game_state.get_game_state_field('timesup_start_time')
            timesup_duration = self.game_state.get_config_field('timesup_duration') or 3
            rem = max(0, timesup_duration - (now - timesup_start_time))
            
            if rem <= 0:
                return self._advance_question_safely_redis(now, "timesup_finished")
            
            status = 'roundcompleted_waiting' if player_has_answered else 'timesup'
            return {
                'status': status, 'timesup_remaining': rem,
                'current_question_number': current_question_number, 'max_questions': max_questions,
                'game_started': True, 'player_answered': player_has_answered,
                'scores': player_scores
            }
        
        # All answered logic
        elif all_answered and not round_completed_state:
            print(f"🎉 All players answered question {current_question_number}!")
            self.game_state.update_game_state({
                'round_completed_state': True,
                'round_completed_start_time': now
            })
            
            round_completed_duration = self.game_state.get_config_field('round_completed_duration') or 2.0
            return {
                'status': 'roundcompleted_all', 'roundcompleted_remaining': round_completed_duration,
                'current_question_number': current_question_number, 'max_questions': max_questions,
                'game_started': True, 'all_answered': True, 'scores': player_scores
            }
        
        elif round_completed_state:
            round_completed_start_time = self.game_state.get_game_state_field('round_completed_start_time')
            round_completed_duration = self.game_state.get_config_field('round_completed_duration') or 2.0
            rem = max(0, round_completed_duration - (now - round_completed_start_time))
            
            if rem <= 0:
                return self._advance_question_safely_redis(now, "all_answered_completed")
            
            return {
                'status': 'roundcompleted_all', 'roundcompleted_remaining': rem,
                'current_question_number': current_question_number, 'max_questions': max_questions,
                'game_started': True, 'all_answered': True, 'scores': player_scores
            }
        
        # Normal playing state
        return {
            'status': 'playing', 'game_started': True, 
            'current_question_number': current_question_number, 'max_questions': max_questions,
            'question_time_remaining': max(0, question_duration - elapsed),
            'players': list(connected_players), 'scores': player_scores,
            'all_answered': all_answered, 'player_answered': player_has_answered
        }

    def _advance_question_safely_redis(self, now, reason):
        """Advance to next question using Redis backend"""
        advancing_question = self.game_state.get_game_state_field('advancing_question')
        if advancing_question:
            return {'status': 'playing', 'game_started': True}
        
        self.game_state.set_game_state_field('advancing_question', True)
        
        try:
            current_question_number = self.game_state.get_game_state_field('current_question_number')
            max_questions = self.game_state.get_game_state_field('max_questions') or 10
            
            print(f"🔄 Advancing question from {current_question_number} (reason: {reason})")
            
            if current_question_number >= max_questions:
                print(f"🏁 Game finished after {max_questions} questions!")
                player_scores = self.game_state.get_player_scores()
                self.game_state.set_game_state_field('game_finished', True)
                return {'status': 'finished', 'game_started': True, 'final_scores': player_scores}
            
            # Generate new question and update state
            new_question = self.game_state.generate_new_question()
            self.game_state.update_game_state({
                'current_question_number': current_question_number + 1,
                'question_start_time': now,
                'timesup_state': False,
                'timesup_start_time': None,
                'round_completed_state': False,
                'round_completed_start_time': None
            })
            
            print(f"✅ Advanced to question {current_question_number + 1}")
            
            connected_players = self.game_state.get_connected_players()
            player_scores = self.game_state.get_player_scores()
            question_duration = self.game_state.get_game_state_field('question_duration') or 10
            
            return {
                'status': 'playing', 'game_started': True, 'current_question_number': current_question_number + 1,
                'max_questions': max_questions, 'question_time_remaining': question_duration,
                'players': list(connected_players), 'scores': player_scores, 'all_answered': False
            }
        finally:
            self.game_state.set_game_state_field('advancing_question', False)

    def post_answer(self, data):
        with self.question_lock:
            if hasattr(self.game_state, 'get_game_state_field'):  # Redis mode
                return self._post_answer_redis(data)
            else:  # Fallback mode
                return self._post_answer_fallback(data)

    def _post_answer_redis(self, data):
        """Handle answer submission using Redis backend"""
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        question_id = data.get('question_id')
        user_answer = data.get('answer')
        
        print(f"📝 Player {player_id} answered: {user_answer} for question {question_id}")
        
        game_started = self.game_state.get_game_state_field('game_started')
        game_finished = self.game_state.get_game_state_field('game_finished')
        if not game_started or game_finished:
            print(f"❌ Game not active for {player_id}")
            return {'status': 'game_not_active'}
        
        current_question_id = self.game_state.get_game_state_field('question_id_counter')
        if question_id != current_question_id:
            print(f"❌ Question expired for {player_id}: received {question_id}, current {current_question_id}")
            return {'status': 'question_expired'}
        
        answered_players = self.game_state.get_answered_players()
        if player_id in answered_players:
            print(f"❌ Player {player_id} already answered")
            return {'status': 'already_answered'}
        
        now = time.time()
        question_start_time = self.game_state.get_game_state_field('question_start_time')
        question_duration = self.game_state.get_game_state_field('question_duration') or 10
        time_remaining = max(0, question_duration - (now - question_start_time))
        time_points = int(time_remaining * 10)
        
        self.game_state.add_answered_player(player_id)
        
        current_correct_answer = self.game_state.get_game_state_field('current_correct_answer')
        is_correct = user_answer == current_correct_answer
        
        if is_correct:
            first_correct_answer = self.game_state.get_game_state_field('first_correct_answer')
            is_first = first_correct_answer is None
            if is_first:
                self.game_state.set_game_state_field('first_correct_answer', player_id)
            
            bonus = 50 if is_first else 0
            total = time_points + bonus
            
            # Update player score
            current_scores = self.game_state.get_player_scores()
            new_score = current_scores.get(player_id, 0) + total
            self.game_state.update_player_score(player_id, new_score)
            
            print(f"✅ Correct! Player {player_id} earned {total} points (base: {time_points}, bonus: {bonus})")
            return {
                'status': 'correct', 'correct': True, 'new_score': new_score,
                'points_earned': total, 'time_points': time_points, 'bonus_points': bonus,
                'first_correct': is_first, 'time_remaining': time_remaining
            }
        
        print(f"❌ Wrong! Player {player_id} answered {user_answer}, correct was {current_correct_answer}")
        current_scores = self.game_state.get_player_scores()
        return {
            'status': 'incorrect', 'correct': False, 'new_score': current_scores.get(player_id, 0),
            'points_earned': 0, 'time_remaining': time_remaining
        }

    def reset_game(self):
        with self.question_lock:
            if hasattr(self.game_state, 'reset_game_internal'):  # Redis mode
                self.game_state.reset_game_internal()
            else:  # Fallback mode
                self.reset_game_internal_fallback()

    # Fallback methods for when Redis is not available
    def _get_game_status_fallback(self, player_id):
        """Complete fallback game status logic"""
        now = time.time()
        gs = self.game_state
        
        # Update heartbeat for real players
        if player_id != 'heartbeat' and player_id in gs['connected_players']:
            gs['last_heartbeat'][player_id] = now
        
        # Check for disconnected players
        timeout = gs.get('heartbeat_timeout', 30)
        disconnected = []
        for pid, last_beat in list(gs['last_heartbeat'].items()):
            if now - last_beat > timeout:
                disconnected.append(pid)
        
        # Remove disconnected players
        for pid in disconnected:
            gs['connected_players'].discard(pid)
            gs['player_scores'].pop(pid, None)
            gs['last_heartbeat'].pop(pid, None)
            gs['answered_players'].discard(pid)
            print(f"Player {pid} disconnected (timeout)")
        
        # Reset game if no players
        if not gs['connected_players'] and (gs['game_started'] or gs['countdown_started']):
            print("All players disconnected! Resetting game...")
            self.reset_game_internal_fallback()
            return {'status': 'waiting', 'player_count': 0, 'required_players': self.REQUIRED_PLAYERS}
        
        # Game finished
        if gs['game_finished']:
            return {'status': 'finished', 'game_started': True, 'final_scores': gs['player_scores']}
        
        # Countdown logic
        if gs['countdown_started'] and not gs['game_started']:
            elapsed = now - gs['countdown_start_time']
            remaining = max(0, gs['countdown_duration'] - elapsed)
            
            if remaining <= 0:
                print("🚀 Countdown finished, starting game!")
                self.start_game()
                return {'status': 'playing', 'game_started': True}
            else:
                return {
                    'status': 'countdown',
                    'countdown_remaining': remaining,
                    'player_count': len(gs['connected_players']),
                    'required_players': self.REQUIRED_PLAYERS,
                    'game_started': False,
                    'countdown_started': True
                }
        
        # Waiting for players
        if not gs['game_started']:
            return {
                'status': 'waiting',
                'player_count': len(gs['connected_players']),
                'players_needed': max(0, self.REQUIRED_PLAYERS - len(gs['connected_players'])),
                'required_players': self.REQUIRED_PLAYERS,
                'game_started': False,
                'countdown_started': gs['countdown_started']
            }
        
        # Game running
        question_duration = gs.get('question_duration', 10)
        elapsed = now - gs['question_start_time']
        all_answered = len(gs['answered_players']) >= len(gs['connected_players'])
        player_has_answered = player_id in gs['answered_players']
        
        # Time up logic
        if elapsed >= question_duration and not all_answered:
            if not gs['timesup_state']:
                print(f"⏰ Time's up for question {gs['current_question_number']}")
                gs['timesup_state'] = True
                gs['timesup_start_time'] = now
            
            timesup_elapsed = now - gs['timesup_start_time']
            timesup_remaining = max(0, gs['timesup_duration'] - timesup_elapsed)
            
            if timesup_remaining <= 0:
                return self._advance_question_safely_fallback(now, "timesup_finished")
            
            status = 'roundcompleted_waiting' if player_has_answered else 'timesup'
            return {
                'status': status,
                'timesup_remaining': timesup_remaining,
                'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'],
                'game_started': True,
                'player_answered': player_has_answered,
                'scores': gs['player_scores']
            }
        
        # All answered logic
        elif all_answered and not gs['round_completed_state']:
            print(f"🎉 All players answered question {gs['current_question_number']}!")
            gs['round_completed_state'] = True
            gs['round_completed_start_time'] = now
            
            return {
                'status': 'roundcompleted_all',
                'roundcompleted_remaining': gs['round_completed_duration'],
                'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'],
                'game_started': True,
                'all_answered': True,
                'scores': gs['player_scores']
            }
        
        elif gs['round_completed_state']:
            round_elapsed = now - gs['round_completed_start_time']
            round_remaining = max(0, gs['round_completed_duration'] - round_elapsed)
            
            if round_remaining <= 0:
                return self._advance_question_safely_fallback(now, "all_answered_completed")
            
            return {
                'status': 'roundcompleted_all',
                'roundcompleted_remaining': round_remaining,
                'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'],
                'game_started': True,
                'all_answered': True,
                'scores': gs['player_scores']
            }
        
        # Normal playing state
        return {
            'status': 'playing',
            'game_started': True,
            'current_question_number': gs['current_question_number'],
            'max_questions': gs['max_questions'],
            'question_time_remaining': max(0, question_duration - elapsed),
            'players': list(gs['connected_players']),
            'scores': gs['player_scores'],
            'all_answered': all_answered,
            'player_answered': player_has_answered
        }

    def _advance_question_safely_fallback(self, now, reason):
        """Advance to next question using fallback state"""
        gs = self.game_state
        
        if gs['advancing_question']:
            return {'status': 'playing', 'game_started': True}
        
        gs['advancing_question'] = True
        
        try:
            print(f"🔄 Advancing question from {gs['current_question_number']} (reason: {reason})")
            
            if gs['current_question_number'] >= gs['max_questions']:
                print(f"🏁 Game finished after {gs['max_questions']} questions!")
                gs['game_finished'] = True
                return {'status': 'finished', 'game_started': True, 'final_scores': gs['player_scores']}
            
            # Generate new question and update state
            gs['current_question_number'] += 1
            gs['current_question'] = self.generate_new_question_fallback()
            gs['question_start_time'] = now
            gs['timesup_state'] = False
            gs['timesup_start_time'] = None
            gs['round_completed_state'] = False
            gs['round_completed_start_time'] = None
            gs['answered_players'].clear()
            gs['first_correct_answer'] = None
            
            print(f"✅ Advanced to question {gs['current_question_number']}")
            
            return {
                'status': 'playing',
                'game_started': True,
                'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'],
                'question_time_remaining': gs['question_duration'],
                'players': list(gs['connected_players']),
                'scores': gs['player_scores'],
                'all_answered': False
            }
        finally:
            gs['advancing_question'] = False

    def _post_answer_fallback(self, data):
        """Handle answer submission using fallback state"""
        gs = self.game_state
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        question_id = data.get('question_id')
        user_answer = data.get('answer')
        
        print(f"📝 Player {player_id} answered: {user_answer} for question {question_id}")
        
        if not gs['game_started'] or gs['game_finished']:
            print(f"❌ Game not active for {player_id}")
            return {'status': 'game_not_active'}
        
        if question_id != gs['question_id_counter']:
            print(f"❌ Question expired for {player_id}: received {question_id}, current {gs['question_id_counter']}")
            return {'status': 'question_expired'}
        
        if player_id in gs['answered_players']:
            print(f"❌ Player {player_id} already answered")
            return {'status': 'already_answered'}
        
        now = time.time()
        elapsed = now - gs['question_start_time']
        time_remaining = max(0, gs['question_duration'] - elapsed)
        time_points = int(time_remaining * 10)
        
        gs['answered_players'].add(player_id)
        
        is_correct = user_answer == gs['current_correct_answer']
        
        if is_correct:
            is_first = gs['first_correct_answer'] is None
            if is_first:
                gs['first_correct_answer'] = player_id
            
            bonus = 50 if is_first else 0
            total = time_points + bonus
            gs['player_scores'][player_id] = gs['player_scores'].get(player_id, 0) + total
            
            print(f"✅ Correct! Player {player_id} earned {total} points (base: {time_points}, bonus: {bonus})")
            return {
                'status': 'correct',
                'correct': True,
                'new_score': gs['player_scores'][player_id],
                'points_earned': total,
                'time_points': time_points,
                'bonus_points': bonus,
                'first_correct': is_first,
                'time_remaining': time_remaining
            }
        
        print(f"❌ Wrong! Player {player_id} answered {user_answer}, correct was {gs['current_correct_answer']}")
        return {
            'status': 'incorrect',
            'correct': False,
            'new_score': gs['player_scores'].get(player_id, 0),
            'points_earned': 0,
            'time_remaining': time_remaining
        }

    def generate_new_question_fallback(self):
        """Generate new question for fallback mode"""
        import random
        
        gs = self.game_state
        gs['question_id_counter'] += 1
        
        COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK", "GRAY", "ORANGE", "PINK", "BROWN"]
        
        text = random.choice(COLOR_NAMES)
        correct = random.choice([c for c in COLOR_NAMES if c != text])
        options = random.sample([c for c in COLOR_NAMES if c != correct], 4) + [correct]
        random.shuffle(options)
        
        question = {
            "question_id": gs['question_id_counter'],
            "text": text,
            "text_color": correct,
            "options": options
        }
        
        gs['current_correct_answer'] = correct
        gs['first_correct_answer'] = None
        
        print(f"✨ Generated Q{gs['question_id_counter']}: '{text}' in {correct}")
        return question

    def reset_game_internal_fallback(self):
        """Reset game state for fallback mode"""
        gs = self.game_state
        players = gs['connected_players'].copy()
        now = time.time()
        
        # Reset game state while preserving players
        gs.update({
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
            'answered_players': set(),
            'timesup_state': False,
            'timesup_start_time': None,
            'round_completed_state': False,
            'round_completed_start_time': None,
            'advancing_question': False
        })
        
        # Reset scores and heartbeats
        for player_id in players:
            gs['player_scores'][player_id] = 0
            gs['last_heartbeat'][player_id] = now
        
        print(f"🔄 Game reset - ready for {len(players)} players!")

    def get_server_stats(self):
        """Get server statistics for load balancing"""
        try:
            # Get active connections count
            import threading
            active_connections = threading.active_count() - 2  # Exclude main and heartbeat threads
            
            # Get game state info
            if hasattr(self.game_state, 'get_connected_players'):  # Redis mode
                connected_players = self.game_state.get_connected_players()
                player_count = len(connected_players)
                game_started = self.game_state.get_game_state_field('game_started') or False
                required_players = self.game_state.get_required_players()
            else:  # Fallback mode
                player_count = len(self.scores)
                game_started = self.game_started
                required_players = self.REQUIRED_PLAYERS
            
            # Calculate load score (higher = more loaded)
            load_score = active_connections * 1.0 + player_count * 0.5
            
            return {
                'active_connections': active_connections,
                'player_count': player_count,
                'required_players': required_players,
                'game_started': game_started,
                'load_score': load_score,
                'server_healthy': True,
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"Error getting server stats: {e}")
            return {
                'active_connections': 0,
                'player_count': 0,
                'required_players': 2,
                'game_started': False,
                'load_score': 0,
                'server_healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }

if __name__=="__main__":
    httpserver = HttpServer()
    d = httpserver.proses('GET testing.txt HTTP/1.0')
    print(d)
    d = httpserver.proses('GET donalbebek.jpg HTTP/1.0')
    print(d)