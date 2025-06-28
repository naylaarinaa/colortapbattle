import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import json
import threading
import time

class HttpServer:
    def __init__(self, required_players=2):
        self.sessions = {}
        self.types = {}
        self.types['.pdf'] = 'application/pdf'
        self.types['.jpg'] = 'image/jpeg'
        self.types['.txt'] = 'text/plain'
        self.types['.html'] = 'text/html'
        
        # Game state initialization
        self.REQUIRED_PLAYERS = required_players
        self.COLOR_NAMES = [
            "RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK",
            "GRAY", "ORANGE", "PINK", "BROWN"
        ]
        self.game_state = {
            'question_id_counter': 0,
            'current_question': None,
            'current_correct_answer': None,
            'player_scores': {},
            'connected_players': set(),
            'game_started': False,
            'countdown_started': False,
            'countdown_start_time': None,
            'countdown_duration': 3,
            'game_start_time': None,
            'question_start_time': None,
            'current_question_number': 0,
            'max_questions': 10,
            'question_duration': 10,
            'players_ready': set(),
            'game_finished': False,
            'first_correct_answer': None,
            'answered_players': set(),
            'last_heartbeat': {},
            'heartbeat_timeout': 30,  # Increased timeout
            'timesup_state': False,
            'timesup_start_time': None,
            'timesup_duration': 3,
            'round_completed_state': False,
            'round_completed_start_time': None,
            'round_completed_duration': 1.0,
        }
        
        # Add thread lock for preventing race conditions
        self.question_lock = threading.Lock()
        
        # Add flag to prevent multiple question advances
        self.game_state['advancing_question'] = False

        # Start heartbeat monitor thread
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_monitor, daemon=True)
        self.heartbeat_thread.start()

    def heartbeat_monitor(self):
        """Background thread to monitor player heartbeats"""
        while True:
            try:
                time.sleep(5)  # Check every 5 seconds
                with self.question_lock:
                    self.check_disconnected_players()
            except Exception as e:
                print(f"Heartbeat monitor error: {e}")

    def check_disconnected_players(self):
        """Check for disconnected players based on heartbeat timeout"""
        current_time = time.time()
        disconnected_players = []
        
        for player in list(self.game_state['connected_players']):
            last_seen = self.game_state['last_heartbeat'].get(player, current_time)
            if current_time - last_seen > self.game_state['heartbeat_timeout']:
                disconnected_players.append(player)
        
        # Remove disconnected players
        for player in disconnected_players:
            print(f"Player {player} disconnected (timeout)")
            self.game_state['connected_players'].discard(player)
            self.game_state['last_heartbeat'].pop(player, None)
            self.game_state['answered_players'].discard(player)
        
        # If all players disconnected during game, reset
        if (len(self.game_state['connected_players']) == 0 and 
            (self.game_state['game_started'] or self.game_state['countdown_started'])):
            print("All players disconnected! Resetting game...")
            self.reset_game_internal()
            return True
        
        return len(disconnected_players) > 0

    def reset_game_internal(self):
        """Internal method to reset game state"""
        connected_players = self.game_state['connected_players'].copy()
        
        self.game_state.update({
            'question_id_counter': 0,
            'current_question': None,
            'current_correct_answer': None,
            'player_scores': {player: 0 for player in connected_players},
            'connected_players': connected_players,
            'game_started': False,
            'countdown_started': False,
            'countdown_start_time': None,
            'game_start_time': None,
            'question_start_time': None,
            'current_question_number': 0,
            'players_ready': set(),
            'game_finished': False,
            'first_correct_answer': None,
            'answered_players': set(),
            'last_heartbeat': {player: time.time() for player in connected_players},
            'timesup_state': False,
            'timesup_start_time': None,
            'timesup_duration': 3,
            'round_completed_state': False,
            'round_completed_start_time': None,
            'round_completed_duration': 2.0,  # 2 seconds to show round completed
            'advancing_question': False,
        })
        print(f"🔄 Game reset - ready for {len(connected_players)} players!")

    def get_question(self):
        """Get current question endpoint"""
        if not self.game_state['game_started']:
            return {'error': 'Game not started'}, 400
        
        if not self.game_state['current_question']:
            return {'error': 'No current question'}, 400
        
        current_time = time.time()
        question_elapsed = current_time - self.game_state['question_start_time']
        time_remaining = max(0, self.game_state['question_duration'] - question_elapsed)
        
        response_data = self.game_state['current_question'].copy()
        response_data['time_remaining'] = time_remaining
        response_data['question_number'] = self.game_state['current_question_number']
        response_data['max_questions'] = self.game_state['max_questions']
        
        return response_data, 200

    def response(self, kode=404, message='Not Found', messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime('%c')
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append("Content-Length: {}\r\n".format(len(messagebody)))
        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n")

        response_headers = ''
        for i in resp:
            response_headers = "{}{}".format(response_headers, i)
        if (type(messagebody) is not bytes):
            messagebody = messagebody.encode()
        response = response_headers.encode() + messagebody
        return response

    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]
        all_headers = [n for n in requests[1:] if n != '']
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            if (method == 'GET'):
                object_address = j[1].strip()
                return self.http_get(object_address, all_headers)
            if (method == 'POST'):
                object_address = j[1].strip()
                # POST body is after the blank line
                body = ""
                if "" in requests:
                    idx = requests.index("")
                    body = "\r\n".join(requests[idx+1:])
                return self.http_post(object_address, all_headers, body)
            else:
                return self.response(400, 'Bad Request', '', {})
        except IndexError:
            return self.response(400, 'Bad Request', '', {})

    def http_get(self, object_address, headers):
        # API endpoints
        if object_address.startswith('/status'):
            # Parse player_id from query string
            player_id = 'heartbeat'
            if '?' in object_address:
                path, qs = object_address.split('?', 1)
                for param in qs.split('&'):
                    if param.startswith('player_id='):
                        player_id = param.split('=', 1)[1]
            else:
                path = object_address
            result = self.get_game_status(player_id)
            return self.response(200, 'OK', json.dumps(result), {'Content-type': 'application/json'})
        if object_address == '/question':
            result, code = self.get_question()
            return self.response(code, 'OK' if code == 200 else 'Bad Request', json.dumps(result), {'Content-type': 'application/json'})
        
        # Static file serving
        files = glob('./*')
        thedir = './'
        if (object_address == '/'):
            return self.response(200, 'OK', 'Ini Adalah web Server percobaan', dict())
        if (object_address == '/video'):
            return self.response(302, 'Found', '', dict(location='https://youtu.be/katoxpnTf04'))
        if (object_address == '/santai'):
            return self.response(200, 'OK', 'santai saja', dict())
        object_address = object_address[1:]
        if thedir + object_address not in files:
            return self.response(404, 'Not Found', '', {})
        fp = open(thedir + object_address, 'rb')
        isi = fp.read()
        fext = os.path.splitext(thedir + object_address)[1]
        content_type = self.types.get(fext, 'application/octet-stream')
        headers = {}
        headers['Content-type'] = content_type
        return self.response(200, 'OK', isi, headers)

    def http_post(self, object_address, headers, body):
        # API endpoints
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
        
        # Default
        headers = {}
        isi = "kosong"
        return self.response(200, 'OK', isi, headers)

    def generate_new_question(self):
        """Generate a new random question"""
        print(f"🎲 Generating question #{self.game_state['question_id_counter'] + 1}")
        
        self.game_state['question_id_counter'] += 1
        
        # Use modulo to cycle through colors but add randomness
        import random
        
        # Pick random text and color (different from each other)
        question_text = random.choice(self.COLOR_NAMES)
        available_colors = [c for c in self.COLOR_NAMES if c != question_text]
        correct_color_name = random.choice(available_colors)
        
        # Generate 4 wrong options + 1 correct option
        wrong_options = random.sample([c for c in self.COLOR_NAMES if c != correct_color_name], k=4)
        options = wrong_options + [correct_color_name]
        random.shuffle(options)  # Randomize order
        
        # Set game state
        self.game_state['current_correct_answer'] = correct_color_name
        self.game_state['first_correct_answer'] = None
        self.game_state['answered_players'] = set()
        
        question_data = {
            "question_id": self.game_state['question_id_counter'],
            "text": question_text,
            "text_color": correct_color_name,
            "options": options
        }
        
        print(f"✨ Generated Q{self.game_state['question_id_counter']}: '{question_text}' in {correct_color_name}")
        return question_data

    def start_countdown(self):
        self.game_state['countdown_started'] = True
        self.game_state['countdown_start_time'] = time.time()
        print(f"🔻 Starting countdown with {len(self.game_state['connected_players'])} players")

    def start_game(self):
        self.game_state['game_started'] = True
        self.game_state['countdown_started'] = False
        self.game_state['game_start_time'] = time.time()
        self.game_state['current_question_number'] = 1
        self.game_state['current_question'] = self.generate_new_question()
        self.game_state['question_start_time'] = time.time()
        print(f"🎮 Game started! First question generated.")

    def check_and_start_game(self):
        if (not self.game_state['countdown_started'] and 
            not self.game_state['game_started'] and 
            len(self.game_state['connected_players']) >= self.REQUIRED_PLAYERS):
            self.start_countdown()

    def join_game(self, data):
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        
        print(f"Player {player_id} attempting to join...")
        
        if self.game_state['game_finished']:
            print("Previous game finished, resetting for new players...")
            self.reset_game_internal()
        
        self.game_state['connected_players'].add(player_id)
        self.game_state['player_scores'][player_id] = 0
        self.game_state['last_heartbeat'][player_id] = time.time()
        
        print(f"Player {player_id} joined. Total players: {len(self.game_state['connected_players'])}")
        
        self.check_and_start_game()
        
        return {
            'status': 'joined',
            'player_count': len(self.game_state['connected_players']),
            'required_players': self.REQUIRED_PLAYERS
        }

    def get_game_status(self, player_id):
        # Use lock to prevent race conditions
        with self.question_lock:
            if player_id != 'heartbeat' and player_id in self.game_state['connected_players']:
                self.game_state['last_heartbeat'][player_id] = time.time()
            
            self.check_disconnected_players()
            
            # Handle countdown phase
            if self.game_state['countdown_started'] and not self.game_state['game_started']:
                current_time = time.time()
                countdown_elapsed = current_time - self.game_state['countdown_start_time']
                countdown_remaining = max(0, self.game_state['countdown_duration'] - countdown_elapsed)
                if countdown_remaining <= 0:
                    self.start_game()
                else:
                    return {
                        'status': 'countdown',
                        'countdown_remaining': countdown_remaining,
                        'player_count': len(self.game_state['connected_players']),
                        'required_players': self.REQUIRED_PLAYERS,
                        'game_started': False,
                        'countdown_started': True
                    }
            
            if not self.game_state['game_started']:
                return {
                    'status': 'waiting',
                    'player_count': len(self.game_state['connected_players']),
                    'players_needed': max(0, self.REQUIRED_PLAYERS - len(self.game_state['connected_players'])),
                    'required_players': self.REQUIRED_PLAYERS,
                    'game_started': False,
                    'countdown_started': self.game_state['countdown_started']
                }
            
            current_time = time.time()
            all_answered = len(self.game_state['answered_players']) >= len(self.game_state['connected_players'])
            question_elapsed = current_time - self.game_state['question_start_time']
            
            # Check if this specific player has answered
            player_has_answered = player_id in self.game_state['answered_players'] if player_id != 'heartbeat' else False
            
            # **UPDATED LOGIC FOR ROUND COMPLETED**
            should_advance = False
            advance_reason = None
            
            # Check if we should advance to next question
            if question_elapsed >= self.game_state['question_duration']:
                if not all_answered:
                    # Time's up, show different screens based on whether player answered
                    if not self.game_state['timesup_state']:
                        print(f"⏰ Time's up for question {self.game_state['current_question_number']}")
                        self.game_state['timesup_state'] = True
                        self.game_state['timesup_start_time'] = current_time
                    
                    # Check if timesup duration is over
                    timesup_elapsed = current_time - self.game_state['timesup_start_time']
                    timesup_remaining = max(0, self.game_state['timesup_duration'] - timesup_elapsed)
                    
                    if timesup_remaining <= 0:
                        should_advance = True
                        advance_reason = "timesup_finished"
                        self.game_state['timesup_state'] = False
                        self.game_state['timesup_start_time'] = None
                    else:
                        # **DIFFERENT STATUS BASED ON PLAYER ANSWER**
                        if player_has_answered:
                            # Player answered, show roundcompleted during time's up
                            return {
                                'status': 'roundcompleted_waiting',
                                'timesup_remaining': timesup_remaining,
                                'current_question_number': self.game_state['current_question_number'],
                                'max_questions': self.game_state['max_questions'],
                                'game_started': True,
                                'player_answered': True,
                                'answered_players': list(self.game_state['answered_players']),
                                'waiting_for_players': list(self.game_state['connected_players'] - self.game_state['answered_players'])
                            }
                        else:
                            # Player didn't answer, show timesup
                            return {
                                'status': 'timesup',
                                'timesup_remaining': timesup_remaining,
                                'current_question_number': self.game_state['current_question_number'],
                                'max_questions': self.game_state['max_questions'],
                                'game_started': True,
                                'player_answered': False,
                                'answered_players': list(self.game_state['answered_players']),
                                'waiting_for_players': list(self.game_state['connected_players'] - self.game_state['answered_players'])
                            }
                else:
                    # Time's up but everyone answered
                    should_advance = True
                    advance_reason = "time_and_all_answered"
            elif all_answered:
                # **Everyone answered before time's up - show roundcompleted for ALL players**
                if not self.game_state.get('round_completed_state', False):
                    print(f"🎉 All players answered question {self.game_state['current_question_number']}! Showing round completed...")
                    self.game_state['round_completed_state'] = True
                    self.game_state['round_completed_start_time'] = current_time
                
                # Check if round completed duration is over
                round_completed_elapsed = current_time - self.game_state['round_completed_start_time']
                round_completed_remaining = max(0, self.game_state['round_completed_duration'] - round_completed_elapsed)
                
                if round_completed_remaining <= 0:
                    should_advance = True
                    advance_reason = "all_answered_completed"
                    self.game_state['round_completed_state'] = False
                    self.game_state['round_completed_start_time'] = None
                else:
                    # **ALL PLAYERS GET ROUND COMPLETED**
                    return {
                        'status': 'roundcompleted_all',
                        'roundcompleted_remaining': round_completed_remaining,
                        'current_question_number': self.game_state['current_question_number'],
                        'max_questions': self.game_state['max_questions'],
                        'game_started': True,
                        'all_answered': True,
                        'answered_players': list(self.game_state['answered_players']),
                        'total_players': len(self.game_state['connected_players'])
                    }
        
        # **ADVANCE QUESTION (ONLY ONCE)**
        if should_advance and not self.game_state.get('advancing_question', False):
            return self._advance_question_safely(current_time, advance_reason)
        
        # **NORMAL PLAYING STATE**
        return {
            'status': 'playing',
            'game_started': True,
            'current_question_number': self.game_state['current_question_number'],
            'max_questions': self.game_state['max_questions'],
            'question_time_remaining': max(0, self.game_state['question_duration'] - question_elapsed),
            'players': list(self.game_state['connected_players']),
            'scores': self.game_state['player_scores'],
            'all_answered': all_answered,
            'player_answered': player_has_answered
        }

    def _advance_question_safely(self, current_time, reason):
        """Single function to handle question advancement"""
        # Prevent multiple simultaneous advances
        self.game_state['advancing_question'] = True
        
        try:
            print(f"🔄 Advancing question from {self.game_state['current_question_number']} (reason: {reason})")
            
            # Check if game should end
            if self.game_state['current_question_number'] >= self.game_state['max_questions']:
                print(f"🏁 Game finished after {self.game_state['max_questions']} questions!")
                self.game_state['game_finished'] = True
                return {
                    'status': 'finished',
                    'game_started': True,
                    'final_scores': self.game_state['player_scores']
                }
            
            # Advance to next question
            self.game_state['current_question_number'] += 1
            self.game_state['current_question'] = self.generate_new_question()
            self.game_state['question_start_time'] = current_time
            
            # Reset question state
            self.game_state['answered_players'] = set()
            self.game_state['first_correct_answer'] = None
            self.game_state['timesup_state'] = False
            self.game_state['timesup_start_time'] = None
            
            print(f"✅ Advanced to question {self.game_state['current_question_number']}")
            
            return {
                'status': 'playing',
                'game_started': True,
                'current_question_number': self.game_state['current_question_number'],
                'max_questions': self.game_state['max_questions'],
                'question_time_remaining': self.game_state['question_duration'],
                'players': list(self.game_state['connected_players']),
                'scores': self.game_state['player_scores'],
                'all_answered': False
            }
        
        finally:
            # Always reset the advancing flag
            self.game_state['advancing_question'] = False

    def post_answer(self, data):
        """Thread-safe answer submission"""
        with self.question_lock:
            player_id = data.get('player_username', data.get('player_id', 'anonymous'))
            question_id = data.get('question_id')
            user_answer = data.get('answer')
            
            print(f"📝 Player {player_id} answered: {user_answer} for question {question_id}")
            
            # Validation checks
            if not self.game_state['game_started'] or self.game_state['game_finished']:
                print(f"❌ Game not active for {player_id}")
                return {'status': 'game_not_active'}
            
            if question_id != self.game_state['question_id_counter']:
                print(f"❌ Question expired for {player_id}: received {question_id}, current {self.game_state['question_id_counter']}")
                return {'status': 'question_expired'}
            
            if player_id in self.game_state['answered_players']:
                print(f"❌ Player {player_id} already answered")
                return {'status': 'already_answered'}
            
            # Calculate scoring
            current_time = time.time()
            elapsed_time = current_time - self.game_state['question_start_time']
            time_remaining = max(0, self.game_state['question_duration'] - elapsed_time)
            time_based_points = int(time_remaining * 10)
            
            # Record answer
            self.game_state['answered_players'].add(player_id)
            
            is_correct = user_answer == self.game_state['current_correct_answer']
            
            if is_correct:
                is_first_correct = self.game_state['first_correct_answer'] is None
                if is_first_correct:
                    self.game_state['first_correct_answer'] = player_id
                    
                base_points = time_based_points
                bonus_points = 50 if is_first_correct else 0
                total_points = base_points + bonus_points
                
                self.game_state['player_scores'][player_id] = self.game_state['player_scores'].get(player_id, 0) + total_points
                
                print(f"✅ Correct! Player {player_id} earned {total_points} points (base: {base_points}, bonus: {bonus_points})")
                
                return {
                    'status': 'correct',
                    'correct': True,
                    'new_score': self.game_state['player_scores'][player_id],
                    'points_earned': total_points,
                    'time_points': base_points,
                    'bonus_points': bonus_points,
                    'first_correct': is_first_correct,
                    'time_remaining': time_remaining
                }
            else:
                print(f"❌ Wrong! Player {player_id} answered {user_answer}, correct was {self.game_state['current_correct_answer']}")
                
                return {
                    'status': 'incorrect',
                    'correct': False,
                    'new_score': self.game_state['player_scores'].get(player_id, 0),
                    'points_earned': 0,
                    'time_remaining': time_remaining
                }

    def reset_game(self):
        """Reset game state"""
        with self.question_lock:
            self.reset_game_internal()