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
            'heartbeat_timeout': 10,
            'timesup_state': False,
            'timesup_start_time': None,
            'timesup_duration': 3,
            'round_completed_state': False,
            'round_completed_start_time': None,
            'round_completed_duration': 1.0,  # 1 detik
        }
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_monitor, daemon=True)
        self.heartbeat_thread.start()

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

    # --- Game Logic Functions (adapted from Flask version) ---

    def generate_new_question(self):
        self.game_state['question_id_counter'] += 1
        question_text = self.COLOR_NAMES[self.game_state['question_id_counter'] % len(self.COLOR_NAMES)]
        correct_color_name = self.COLOR_NAMES[(self.game_state['question_id_counter'] + 3) % len(self.COLOR_NAMES)]
        options = [self.COLOR_NAMES[(self.game_state['question_id_counter'] + i) % len(self.COLOR_NAMES)] for i in range(5)]
        if correct_color_name not in options:
            options[-1] = correct_color_name
        self.game_state['current_correct_answer'] = correct_color_name
        self.game_state['first_correct_answer'] = None
        self.game_state['answered_players'] = set()
        return {
            "question_id": self.game_state['question_id_counter'],
            "text": question_text,
            "text_color": correct_color_name,
            "options": options
        }

    def start_countdown(self):
        self.game_state['countdown_started'] = True
        self.game_state['countdown_start_time'] = time.time()

    def start_game(self):
        self.game_state['game_started'] = True
        self.game_state['countdown_started'] = False
        self.game_state['game_start_time'] = time.time()
        self.game_state['current_question_number'] = 1
        self.game_state['current_question'] = self.generate_new_question()
        self.game_state['question_start_time'] = time.time()

    def check_and_start_game(self):
        if not self.game_state['countdown_started'] and not self.game_state['game_started'] and len(self.game_state['connected_players']) >= self.REQUIRED_PLAYERS:
            self.start_countdown()

    def join_game(self, data):
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        if self.game_state['game_finished']:
            self.reset_game()
        self.game_state['connected_players'].add(player_id)
        self.game_state['player_scores'][player_id] = 0
        self.game_state['last_heartbeat'][player_id] = time.time()
        self.check_and_start_game()
        return {
            'status': 'joined',
            'player_count': len(self.game_state['connected_players']),
            'required_players': self.REQUIRED_PLAYERS
        }

    def get_game_status(self, player_id):
        if player_id != 'heartbeat' and player_id in self.game_state['connected_players']:
            self.game_state['last_heartbeat'][player_id] = time.time()
        self.check_disconnected_players()
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
        # Tambahan: round_completed untuk pemain yang sudah jawab
        all_answered = len(self.game_state['answered_players']) >= len(self.game_state['connected_players'])

        # ROUND COMPLETED STATE
        if self.game_state.get('round_completed_state', False):
            current_time = time.time()
            elapsed = current_time - self.game_state.get('round_completed_start_time', 0)
            if elapsed < self.game_state.get('round_completed_duration', 1.0):
                if player_id in self.game_state['answered_players']:
                    return {
                        'status': 'round_completed',
                        'current_question_number': self.game_state['current_question_number'],
                        'max_questions': self.game_state['max_questions'],
                        'scores': self.game_state['player_scores'],
                        'players': list(self.game_state['connected_players']),
                        'game_started': True
                    }
            else:
                self.game_state['round_completed_state'] = False
                self.game_state['round_completed_start_time'] = None
                # Lanjut ke pertanyaan berikutnya
                if self.game_state['current_question_number'] < self.game_state['max_questions']:
                    self.game_state['current_question_number'] += 1
                    self.game_state['current_question'] = self.generate_new_question()
                    self.game_state['question_start_time'] = current_time
                    self.game_state['answered_players'] = set()
                else:
                    self.game_state['game_finished'] = True
                    return {
                        'status': 'finished',
                        'game_started': True,
                        'final_scores': self.game_state['player_scores']
                    }

        # Jika semua pemain sudah menjawab, mulai round_completed_state
        if all_answered and not self.game_state.get('round_completed_state', False):
            self.game_state['round_completed_state'] = True
            self.game_state['round_completed_start_time'] = time.time()
            if player_id in self.game_state['answered_players']:
                return {
                    'status': 'round_completed',
                    'current_question_number': self.game_state['current_question_number'],
                    'max_questions': self.game_state['max_questions'],
                    'scores': self.game_state['player_scores'],
                    'players': list(self.game_state['connected_players']),
                    'game_started': True
                }

        if self.game_state['timesup_state']:
            current_time = time.time()
            timesup_elapsed = current_time - self.game_state['timesup_start_time']
            timesup_remaining = max(0, self.game_state['timesup_duration'] - timesup_elapsed)
            if timesup_remaining <= 0:
                self.game_state['timesup_state'] = False
                self.game_state['timesup_start_time'] = None
                if self.game_state['current_question_number'] < self.game_state['max_questions']:
                    self.game_state['current_question_number'] += 1
                    self.game_state['current_question'] = self.generate_new_question()
                    self.game_state['question_start_time'] = time.time()
                else:
                    self.game_state['game_finished'] = True
                    return {
                        'status': 'finished',
                        'game_started': True,
                        'final_scores': self.game_state['player_scores']
                    }
            else:
                return {
                    'status': 'timesup',
                    'timesup_remaining': timesup_remaining,
                    'current_question_number': self.game_state['current_question_number'],
                    'max_questions': self.game_state['max_questions'],
                    'game_started': True
                }
        current_time = time.time()
        question_elapsed = current_time - self.game_state['question_start_time']
        if question_elapsed >= self.game_state['question_duration']:
            if not all_answered:
                self.game_state['timesup_state'] = True
                self.game_state['timesup_start_time'] = time.time()
                return {
                    'status': 'timesup',
                    'timesup_remaining': self.game_state['timesup_duration'],
                    'current_question_number': self.game_state['current_question_number'],
                    'max_questions': self.game_state['max_questions'],
                    'game_started': True
                }
            else:
                if self.game_state['current_question_number'] < self.game_state['max_questions']:
                    self.game_state['current_question_number'] += 1
                    self.game_state['current_question'] = self.generate_new_question()
                    self.game_state['question_start_time'] = current_time
                    question_elapsed = 0
                else:
                    self.game_state['game_finished'] = True
                    return {
                        'status': 'finished',
                        'game_started': True,
                        'final_scores': self.game_state['player_scores']
                    }
        elif all_answered:
            if self.game_state['current_question_number'] < self.game_state['max_questions']:
                self.game_state['current_question_number'] += 1
                self.game_state['current_question'] = self.generate_new_question()
                self.game_state['question_start_time'] = current_time
                question_elapsed = 0
            else:
                self.game_state['game_finished'] = True
                return {
                    'status': 'finished',
                    'game_started': True,
                    'final_scores': self.game_state['player_scores']
                }
        return {
            'status': 'playing',
            'game_started': True,
            'current_question_number': self.game_state['current_question_number'],
            'max_questions': self.game_state['max_questions'],
            'question_time_remaining': max(0, self.game_state['question_duration'] - question_elapsed),
            'players': list(self.game_state['connected_players']),
            'scores': self.game_state['player_scores'],
            'all_answered': all_answered
        }

    def get_question(self):
        if not self.game_state['game_started']:
            return {'error': 'Game not started'}, 400
        if not self.game_state['current_question']:
            return {'error': 'No current question'}, 400
        current_time = time.time()
        question_elapsed = current_time - self.game_state['question_start_time']
        time_remaining = max(0, self.game_state['question_duration'] - question_elapsed)
        response = self.game_state['current_question'].copy()
        response['time_remaining'] = time_remaining
        response['question_number'] = self.game_state['current_question_number']
        response['max_questions'] = self.game_state['max_questions']
        return response, 200

    def post_answer(self, data):
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        question_id = data.get('question_id')
        user_answer = data.get('answer')
        if not self.game_state['game_started'] or self.game_state['game_finished']:
            return {'status': 'game_not_active'}
        if question_id != self.game_state['question_id_counter']:
            return {'status': 'question_expired'}
        if player_id in self.game_state['answered_players']:
            return {'status': 'already_answered'}
        current_time = time.time()
        elapsed_time = current_time - self.game_state['question_start_time']
        time_remaining = max(0, self.game_state['question_duration'] - elapsed_time)
        time_based_points = int(time_remaining * 10)
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
            return {
                'status': 'incorrect',
                'correct': False,
                'new_score': self.game_state['player_scores'].get(player_id, 0),
                'points_earned': 0,
                'time_remaining': time_remaining
            }

    def reset_game(self):
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
            'round_completed_duration': 1.0,  # 1 detik
        })

    def check_disconnected_players(self):
        current_time = time.time()
        disconnected_players = []
        for player in list(self.game_state['connected_players']):
            last_seen = self.game_state['last_heartbeat'].get(player, current_time)
            if current_time - last_seen > self.game_state['heartbeat_timeout']:
                disconnected_players.append(player)
        for player in disconnected_players:
            self.game_state['connected_players'].discard(player)
            self.game_state['last_heartbeat'].pop(player, None)
            self.game_state['answered_players'].discard(player)
        if len(self.game_state['connected_players']) == 0 and (self.game_state['game_started'] or self.game_state['countdown_started']):
            self.reset_game()
            return True
        return len(disconnected_players) > 0

    def heartbeat_monitor(self):
        while True:
            time.sleep(5)
            self.check_disconnected_players()

    # Tambahan: fungsi dari utils.py
    def serialize_data(self, data):
        import json
        return json.dumps(data).encode('utf-8')

    def deserialize_data(self, data):
        import json
        return json.loads(data.decode('utf-8'))

    def send_data(self, sock, data):
        serialized_data = self.serialize_data(data)
        sock.sendall(serialized_data)

    def receive_data(self, sock):
        buffer = bytearray()
        while True:
            part = sock.recv(4096)
            if not part:
                break
            buffer.extend(part)
            if b'\r\n\r\n' in buffer:
                break
        return self.deserialize_data(buffer)

    # Tambahan: fungsi dari game_logic.py
    def generate_question(self, color_names):
        import random
        text = random.choice(color_names)
        text_color_name = random.choice(color_names)
        return text, text_color_name

    def validate_answer(self, user_color_name, correct_color_name):
        return user_color_name == correct_color_name

    def update_player_location(self, players, player_id, x, y):
        if player_id in players:
            players[player_id]['location'] = (x, y)

    def get_all_players(self, players):
        return {'status': 'OK', 'players': list(players.keys())}

    def get_player_face(self, players, player_id):
        if player_id in players:
            return {'status': 'OK', 'face': players[player_id]['face']}
        return {'status': 'ERROR'}

    def get_player_location(self, players, player_id):
        if player_id in players:
            return {'status': 'OK', 'location': players[player_id]['location']}
        return {'status': 'ERROR'}