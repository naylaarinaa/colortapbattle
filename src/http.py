import sys, os, threading, time, random, json
from glob import glob
from datetime import datetime

class HttpServer:
    def __init__(self, required_players=2):
        self.REQUIRED_PLAYERS = required_players
        self.COLOR_NAMES = ["RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK", "GRAY", "ORANGE", "PINK", "BROWN"]
        self.types = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.txt': 'text/plain', '.html': 'text/html'}
        self.question_lock = threading.Lock()
        self._init_game_state()
        threading.Thread(target=self.heartbeat_monitor, daemon=True).start()

    def _init_game_state(self):
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

    def heartbeat_monitor(self):
        while True:
            time.sleep(5)
            with self.question_lock:
                self.check_disconnected_players()

    def check_disconnected_players(self):
        now, gs = time.time(), self.game_state
        disconnected = [p for p in gs['connected_players'] if now - gs['last_heartbeat'].get(p, now) > gs['heartbeat_timeout']]
        for p in disconnected:
            print(f"Player {p} disconnected (timeout)")
            gs['connected_players'].discard(p)
            gs['last_heartbeat'].pop(p, None)
            gs['answered_players'].discard(p)
        if not gs['connected_players'] and (gs['game_started'] or gs['countdown_started']):
            print("All players disconnected! Resetting game...")
            self.reset_game_internal()
            return True
        return bool(disconnected)

    def reset_game_internal(self):
        players, now = self.game_state['connected_players'].copy(), time.time()
        self.game_state.update({
            'question_id_counter': 0, 'current_question': None, 'current_correct_answer': None,
            'player_scores': {p: 0 for p in players}, 'connected_players': players,
            'game_started': False, 'countdown_started': False, 'countdown_start_time': None,
            'game_start_time': None, 'question_start_time': None, 'current_question_number': 0,
            'players_ready': set(), 'game_finished': False, 'first_correct_answer': None,
            'answered_players': set(), 'last_heartbeat': {p: now for p in players},
            'timesup_state': False, 'timesup_start_time': None, 'round_completed_state': False,
            'round_completed_start_time': None, 'advancing_question': False,
        })
        print(f"🔄 Game reset - ready for {len(players)} players!")

    def get_question(self):
        gs = self.game_state
        if not gs['game_started'] or not gs['current_question']:
            return {'error': 'Game not started' if not gs['game_started'] else 'No current question'}, 400
        now, elapsed = time.time(), time.time() - gs['question_start_time']
        resp = gs['current_question'].copy()
        resp.update({
            'time_remaining': max(0, gs['question_duration'] - elapsed),
            'question_number': gs['current_question_number'],
            'max_questions': gs['max_questions']
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

    def generate_new_question(self):
        gs = self.game_state
        gs['question_id_counter'] += 1
        text, correct = random.choice(self.COLOR_NAMES), random.choice([c for c in self.COLOR_NAMES if c != (text := random.choice(self.COLOR_NAMES))])
        options = random.sample([c for c in self.COLOR_NAMES if c != correct], 4) + [correct]
        random.shuffle(options)
        gs.update({'current_correct_answer': correct, 'first_correct_answer': None, 'answered_players': set()})
        print(f"✨ Generated Q{gs['question_id_counter']}: '{text}' in {correct}")
        return {"question_id": gs['question_id_counter'], "text": text, "text_color": correct, "options": options}

    def start_countdown(self):
        gs = self.game_state
        gs['countdown_started'], gs['countdown_start_time'] = True, time.time()
        print(f"🔻 Starting countdown with {len(gs['connected_players'])} players")

    def start_game(self):
        gs = self.game_state
        gs.update({'game_started': True, 'countdown_started': False, 'game_start_time': time.time(),
                   'current_question_number': 1, 'current_question': self.generate_new_question(),
                   'question_start_time': time.time()})
        print("🎮 Game started! First question generated.")

    def check_and_start_game(self):
        gs = self.game_state
        if not gs['countdown_started'] and not gs['game_started'] and len(gs['connected_players']) >= self.REQUIRED_PLAYERS:
            self.start_countdown()

    def join_game(self, data):
        gs = self.game_state
        player_id = data.get('player_username', data.get('player_id', 'anonymous'))
        print(f"Player {player_id} attempting to join...")
        if gs['game_finished']:
            print("Previous game finished, resetting for new players...")
            self.reset_game_internal()
        gs['connected_players'].add(player_id)
        gs['player_scores'][player_id] = 0
        gs['last_heartbeat'][player_id] = time.time()
        print(f"Player {player_id} joined. Total players: {len(gs['connected_players'])}")
        self.check_and_start_game()
        return {'status': 'joined', 'player_count': len(gs['connected_players']), 'required_players': self.REQUIRED_PLAYERS}

    def get_game_status(self, player_id):
        with self.question_lock:
            gs, now = self.game_state, time.time()
            if player_id != 'heartbeat' and player_id in gs['connected_players']:
                gs['last_heartbeat'][player_id] = now
            self.check_disconnected_players()
            
            if gs['countdown_started'] and not gs['game_started']:
                rem = max(0, gs['countdown_duration'] - (now - gs['countdown_start_time']))
                if rem <= 0:
                    self.start_game()
                else:
                    return {'status': 'countdown', 'countdown_remaining': rem, 'player_count': len(gs['connected_players']),
                            'required_players': self.REQUIRED_PLAYERS, 'game_started': False, 'countdown_started': True}
            
            if not gs['game_started']:
                return {'status': 'waiting', 'player_count': len(gs['connected_players']),
                        'players_needed': max(0, self.REQUIRED_PLAYERS - len(gs['connected_players'])),
                        'required_players': self.REQUIRED_PLAYERS, 'game_started': False, 'countdown_started': gs['countdown_started']}
            
            all_answered = len(gs['answered_players']) >= len(gs['connected_players'])
            elapsed = now - gs['question_start_time']
            player_has_answered = player_id in gs['answered_players'] if player_id != 'heartbeat' else False
            
            if elapsed >= gs['question_duration']:
                if not all_answered:
                    if not gs['timesup_state']:
                        print(f"⏰ Time's up for question {gs['current_question_number']}")
                        gs['timesup_state'], gs['timesup_start_time'] = True, now
                    rem = max(0, gs['timesup_duration'] - (now - gs['timesup_start_time']))
                    if rem <= 0:
                        return self._advance_question_safely(now, "timesup_finished")
                    status = 'roundcompleted_waiting' if player_has_answered else 'timesup'
                    return {
                        'status': status, 'timesup_remaining': rem, 'current_question_number': gs['current_question_number'],
                        'max_questions': gs['max_questions'], 'game_started': True, 'player_answered': player_has_answered,
                        'answered_players': list(gs['answered_players']),
                        'waiting_for_players': list(gs['connected_players'] - gs['answered_players'])
                    }
                else:
                    return self._advance_question_safely(now, "time_and_all_answered")
            elif all_answered:
                if not gs.get('round_completed_state', False):
                    print(f"🎉 All players answered question {gs['current_question_number']}! Showing round completed...")
                    gs['round_completed_state'], gs['round_completed_start_time'] = True, now
                rem = max(0, gs['round_completed_duration'] - (now - gs['round_completed_start_time']))
                if rem <= 0:
                    return self._advance_question_safely(now, "all_answered_completed")
                return {
                    'status': 'roundcompleted_all', 'roundcompleted_remaining': rem,
                    'current_question_number': gs['current_question_number'], 'max_questions': gs['max_questions'],
                    'game_started': True, 'all_answered': True, 'answered_players': list(gs['answered_players']),
                    'total_players': len(gs['connected_players'])
                }
            
            return {
                'status': 'playing', 'game_started': True, 'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'], 'question_time_remaining': max(0, gs['question_duration'] - elapsed),
                'players': list(gs['connected_players']), 'scores': gs['player_scores'],
                'all_answered': all_answered, 'player_answered': player_has_answered
            }

    def _advance_question_safely(self, now, reason):
        gs = self.game_state
        if gs.get('advancing_question', False):
            return {'status': 'playing', 'game_started': True}
        gs['advancing_question'] = True
        try:
            print(f"🔄 Advancing question from {gs['current_question_number']} (reason: {reason})")
            if gs['current_question_number'] >= gs['max_questions']:
                print(f"🏁 Game finished after {gs['max_questions']} questions!")
                gs['game_finished'] = True
                return {'status': 'finished', 'game_started': True, 'final_scores': gs['player_scores']}
            gs.update({
                'current_question_number': gs['current_question_number'] + 1,
                'current_question': self.generate_new_question(),
                'question_start_time': now, 'answered_players': set(), 'first_correct_answer': None,
                'timesup_state': False, 'timesup_start_time': None, 'round_completed_state': False,
                'round_completed_start_time': None
            })
            print(f"✅ Advanced to question {gs['current_question_number']}")
            return {
                'status': 'playing', 'game_started': True, 'current_question_number': gs['current_question_number'],
                'max_questions': gs['max_questions'], 'question_time_remaining': gs['question_duration'],
                'players': list(gs['connected_players']), 'scores': gs['player_scores'], 'all_answered': False
            }
        finally:
            gs['advancing_question'] = False

    def post_answer(self, data):
        with self.question_lock:
            gs = self.game_state
            player_id = data.get('player_username', data.get('player_id', 'anonymous'))
            question_id, user_answer = data.get('question_id'), data.get('answer')
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
            time_remaining = max(0, gs['question_duration'] - (now - gs['question_start_time']))
            time_points = int(time_remaining * 10)
            gs['answered_players'].add(player_id)
            is_correct = user_answer == gs['current_correct_answer']
            
            if is_correct:
                is_first = gs['first_correct_answer'] is None
                if is_first: gs['first_correct_answer'] = player_id
                bonus, total = 50 if is_first else 0, time_points + (50 if is_first else 0)
                gs['player_scores'][player_id] = gs['player_scores'].get(player_id, 0) + total
                print(f"✅ Correct! Player {player_id} earned {total} points (base: {time_points}, bonus: {bonus})")
                return {
                    'status': 'correct', 'correct': True, 'new_score': gs['player_scores'][player_id],
                    'points_earned': total, 'time_points': time_points, 'bonus_points': bonus,
                    'first_correct': is_first, 'time_remaining': time_remaining
                }
            
            print(f"❌ Wrong! Player {player_id} answered {user_answer}, correct was {gs['current_correct_answer']}")
            return {
                'status': 'incorrect', 'correct': False, 'new_score': gs['player_scores'].get(player_id, 0),
                'points_earned': 0, 'time_remaining': time_remaining
            }

    def reset_game(self):
        with self.question_lock:
            self.reset_game_internal()

if __name__=="__main__":
    httpserver = HttpServer()
    d = httpserver.proses('GET testing.txt HTTP/1.0')
    print(d)
    d = httpserver.proses('GET donalbebek.jpg HTTP/1.0')
    print(d)