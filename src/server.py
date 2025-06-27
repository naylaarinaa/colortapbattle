from flask import Flask, jsonify, request
import random
import time
import threading
import sys

app = Flask(__name__)

# Get player count from command line argument, default to 2
def get_required_players():
    if len(sys.argv) > 1:
        try:
            players = int(sys.argv[1])
            if players < 2:
                print("Minimum 2 players required. Setting to 2.")
                return 2
            if players > 10:
                print("Maximum 10 players allowed. Setting to 10.")
                return 10
            return players
        except ValueError:
            print("Invalid player count. Using default of 2 players.")
            return 2
    return 2

REQUIRED_PLAYERS = get_required_players()

COLOR_NAMES = [
    "RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK",
    "GRAY", "ORANGE", "PINK", "BROWN"
]

game_state = {
    'question_id_counter': 0,
    'current_question': None,
    'current_correct_answer': None,
    'player_scores': {},
    'connected_players': set(),
    'game_started': False,
    'countdown_started': False,
    'countdown_start_time': None,
    'countdown_duration': 3,  # 3 seconds countdown
    'game_start_time': None,
    'question_start_time': None,
    'current_question_number': 0,
    'max_questions': 10,
    'question_duration': 10,  # seconds per question
    'players_ready': set(),
    'game_finished': False,
    'first_correct_answer': None,  # Track who answered first for current question
    'answered_players': set(),
    'last_heartbeat': {},  # Track last heartbeat from each player
    'heartbeat_timeout': 10,  # Seconds before considering a player disconnected
    'timesup_state': False,  # NEW: Track if we're in "time's up" state
    'timesup_start_time': None,  # NEW: When time's up state started
    'timesup_duration': 3  # NEW: How long to show "time's up" (3 seconds)
}

def generate_new_question():
    game_state['question_id_counter'] += 1
    
    question_text = random.choice(COLOR_NAMES)
    correct_color_name = random.choice([c for c in COLOR_NAMES if c != question_text])
    
    options = random.sample([c for c in COLOR_NAMES if c != correct_color_name], k=4)
    options.append(correct_color_name)
    random.shuffle(options)
    
    game_state['current_correct_answer'] = correct_color_name
    
    # Reset first answer tracking for new question
    game_state['first_correct_answer'] = None
    game_state['answered_players'] = set()
    
    return {
        "question_id": game_state['question_id_counter'],
        "text": question_text,
        "text_color": correct_color_name,
        "options": options
    }

def start_countdown():
    """Start the 3-second countdown before game begins"""
    game_state['countdown_started'] = True
    game_state['countdown_start_time'] = time.time()
    print(f"Starting 3-second countdown with {len(game_state['connected_players'])} players!")

def start_game():
    """Start the game timer and initialize first question"""
    game_state['game_started'] = True
    game_state['countdown_started'] = False
    game_state['game_start_time'] = time.time()
    game_state['current_question_number'] = 1
    game_state['current_question'] = generate_new_question()
    game_state['question_start_time'] = time.time()
    print(f"Game started with {len(game_state['connected_players'])} players!")

def check_and_start_game():
    """Check if we have enough players to start the countdown"""
    if not game_state['countdown_started'] and not game_state['game_started'] and len(game_state['connected_players']) >= REQUIRED_PLAYERS:
        start_countdown()

@app.route('/join', methods=['POST'])
def join_game():
    """Player joins the game lobby"""
    data = request.get_json()
    player_id = data.get('player_username', data.get('player_id', 'anonymous'))
    
    print(f"Player {player_id} attempting to join...")
    
    # If game is finished, reset it automatically
    if game_state['game_finished']:
        print("Previous game finished, resetting for new players...")
        reset_game()
    
    # Add player to the game
    game_state['connected_players'].add(player_id)
    game_state['player_scores'][player_id] = 0
    game_state['last_heartbeat'][player_id] = time.time()  # Record initial heartbeat
    
    print(f"Player {player_id} joined. Total players: {len(game_state['connected_players'])}")
    
    # Check if we can start the countdown
    check_and_start_game()
    
    return jsonify({
        'status': 'joined',
        'player_count': len(game_state['connected_players']),
        'required_players': REQUIRED_PLAYERS
    })

@app.route('/status', methods=['GET'])
def get_game_status():
    """Get current game status and record heartbeat"""
    # Get player from query parameter or use 'heartbeat' as default
    player_id = request.args.get('player_id', 'heartbeat')
    
    # Record heartbeat if this is from a specific player
    if player_id != 'heartbeat' and player_id in game_state['connected_players']:
        game_state['last_heartbeat'][player_id] = time.time()
    
    # Check for disconnected players
    check_disconnected_players()
    
    # Handle countdown phase
    if game_state['countdown_started'] and not game_state['game_started']:
        current_time = time.time()
        countdown_elapsed = current_time - game_state['countdown_start_time']
        countdown_remaining = max(0, game_state['countdown_duration'] - countdown_elapsed)
        
        # Check if countdown is finished
        if countdown_remaining <= 0:
            start_game()
            # Fall through to game status below
        else:
            return jsonify({
                'status': 'countdown',
                'countdown_remaining': countdown_remaining,
                'player_count': len(game_state['connected_players']),
                'required_players': REQUIRED_PLAYERS,
                'game_started': False,
                'countdown_started': True
            })
    
    if not game_state['game_started']:
        return jsonify({
            'status': 'waiting',
            'player_count': len(game_state['connected_players']),
            'players_needed': max(0, REQUIRED_PLAYERS - len(game_state['connected_players'])),
            'required_players': REQUIRED_PLAYERS,
            'game_started': False,
            'countdown_started': game_state['countdown_started']
        })
    
    # Handle "Time's Up!" state
    if game_state['timesup_state']:
        current_time = time.time()
        timesup_elapsed = current_time - game_state['timesup_start_time']
        timesup_remaining = max(0, game_state['timesup_duration'] - timesup_elapsed)
        
        # Check if time's up display is finished
        if timesup_remaining <= 0:
            # Move to next question or end game
            game_state['timesup_state'] = False
            game_state['timesup_start_time'] = None
            
            if game_state['current_question_number'] < game_state['max_questions']:
                game_state['current_question_number'] += 1
                game_state['current_question'] = generate_new_question()
                game_state['question_start_time'] = time.time()
                print(f"Moving to question {game_state['current_question_number']}")
            else:
                # Game finished
                game_state['game_finished'] = True
                return jsonify({
                    'status': 'finished',
                    'game_started': True,
                    'final_scores': game_state['player_scores']
                })
        else:
            return jsonify({
                'status': 'timesup',
                'timesup_remaining': timesup_remaining,
                'current_question_number': game_state['current_question_number'],
                'max_questions': game_state['max_questions'],
                'game_started': True
            })
    
    current_time = time.time()
    question_elapsed = current_time - game_state['question_start_time']
    
    # Check if all players have answered
    all_answered = len(game_state['answered_players']) >= len(game_state['connected_players'])
    
    # Check if we need to move to "time's up" state or next question
    if question_elapsed >= game_state['question_duration']:
        # Time's up! Start the time's up display
        if not all_answered:  # Only show "time's up" if not all players answered
            game_state['timesup_state'] = True
            game_state['timesup_start_time'] = time.time()
            print(f"Time's up for question {game_state['current_question_number']}! Showing time's up screen...")
            return jsonify({
                'status': 'timesup',
                'timesup_remaining': game_state['timesup_duration'],
                'current_question_number': game_state['current_question_number'],
                'max_questions': game_state['max_questions'],
                'game_started': True
            })
        else:
            # All answered, move directly to next question
            if game_state['current_question_number'] < game_state['max_questions']:
                game_state['current_question_number'] += 1
                game_state['current_question'] = generate_new_question()
                game_state['question_start_time'] = current_time
                question_elapsed = 0
            else:
                # Game finished
                game_state['game_finished'] = True
                return jsonify({
                    'status': 'finished',
                    'game_started': True,
                    'final_scores': game_state['player_scores']
                })
    elif all_answered:
        # All players answered before time up, move to next question immediately
        if game_state['current_question_number'] < game_state['max_questions']:
            game_state['current_question_number'] += 1
            game_state['current_question'] = generate_new_question()
            game_state['question_start_time'] = current_time
            question_elapsed = 0
        else:
            # Game finished
            game_state['game_finished'] = True
            return jsonify({
                'status': 'finished',
                'game_started': True,
                'final_scores': game_state['player_scores']
            })
    
    return jsonify({
        'status': 'playing',
        'game_started': True,
        'current_question_number': game_state['current_question_number'],
        'max_questions': game_state['max_questions'],
        'question_time_remaining': max(0, game_state['question_duration'] - question_elapsed),
        'players': list(game_state['connected_players']),
        'scores': game_state['player_scores'],
        'all_answered': all_answered
    })

@app.route('/reset', methods=['POST'])
def reset_game_endpoint():
    """Reset the game to allow new games"""
    reset_game()
    return jsonify({'status': 'reset', 'message': 'Game has been reset'})

@app.route('/question', methods=['GET'])
def get_question():
    """Get current synchronized question"""
    if not game_state['game_started']:
        return jsonify({'error': 'Game not started'}), 400
    
    if not game_state['current_question']:
        return jsonify({'error': 'No current question'}), 400
    
    current_time = time.time()
    question_elapsed = current_time - game_state['question_start_time']
    time_remaining = max(0, game_state['question_duration'] - question_elapsed)
    
    response = game_state['current_question'].copy()
    response['time_remaining'] = time_remaining
    response['question_number'] = game_state['current_question_number']
    response['max_questions'] = game_state['max_questions']
    
    return jsonify(response)

@app.route('/answer', methods=['POST'])
def post_answer():
    data = request.get_json()
    player_id = data.get('player_username', data.get('player_id', 'anonymous'))
    question_id = data.get('question_id')
    user_answer = data.get('answer')
    
    print(f"Player {player_id} answered: {user_answer} for question {question_id}")
    
    if not game_state['game_started'] or game_state['game_finished']:
        return jsonify({'status': 'game_not_active'})
    
    if question_id != game_state['question_id_counter']:
        return jsonify({'status': 'question_expired'})
    
    if player_id in game_state['answered_players']:
        return jsonify({'status': 'already_answered'})
    
    # Calculate time-based points
    current_time = time.time()
    elapsed_time = current_time - game_state['question_start_time']
    time_remaining = max(0, game_state['question_duration'] - elapsed_time)
    
    # Points = time remaining * 10 (e.g., 8 seconds left = 80 points)
    time_based_points = int(time_remaining * 10)
    
    game_state['answered_players'].add(player_id)
    
    is_correct = user_answer == game_state['current_correct_answer']
    
    if is_correct:
        # Check if this is the first correct answer
        is_first_correct = game_state['first_correct_answer'] is None
        if is_first_correct:
            game_state['first_correct_answer'] = player_id
            
        # Calculate final score
        base_points = time_based_points
        bonus_points = 50 if is_first_correct else 0  # First answer bonus
        total_points = base_points + bonus_points
        
        game_state['player_scores'][player_id] = game_state['player_scores'].get(player_id, 0) + total_points
        
        print(f"Player {player_id} correct! Time remaining: {time_remaining:.1f}s = {base_points} pts"
              + (f" + {bonus_points} bonus = {total_points} total" if bonus_points > 0 else f" = {total_points} total"))
        
        return jsonify({
            'status': 'correct',
            'correct': True,
            'new_score': game_state['player_scores'][player_id],
            'points_earned': total_points,
            'time_points': base_points,
            'bonus_points': bonus_points,
            'first_correct': is_first_correct,
            'time_remaining': time_remaining
        })
    else:
        print(f"Player {player_id} incorrect answer")
        return jsonify({
            'status': 'incorrect',
            'correct': False,
            'new_score': game_state['player_scores'].get(player_id, 0),
            'points_earned': 0,
            'time_remaining': time_remaining
        })

def reset_game():
    """Reset the game state for a new game"""
    # Keep connected players but reset everything else
    connected_players = game_state['connected_players'].copy()
    
    game_state.update({
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
        'last_heartbeat': {player: time.time() for player in connected_players},  # Reset heartbeats
        'timesup_state': False,  # Reset time's up state
        'timesup_start_time': None,
        'timesup_duration': 3
    })
    print(f"Game reset - ready for {len(connected_players)} players!")

def check_disconnected_players():
    """Remove players who haven't sent heartbeat recently"""
    current_time = time.time()
    disconnected_players = []
    
    for player in list(game_state['connected_players']):
        last_seen = game_state['last_heartbeat'].get(player, current_time)
        if current_time - last_seen > game_state['heartbeat_timeout']:
            disconnected_players.append(player)
    
    # Remove disconnected players
    for player in disconnected_players:
        print(f"Player {player} disconnected (timeout)")
        game_state['connected_players'].discard(player)
        game_state['last_heartbeat'].pop(player, None)
        game_state['answered_players'].discard(player)
        
        # Remove from player scores but keep the score for display
        # game_state['player_scores'].pop(player, None)
    
    # If all players disconnected during an active game, reset
    if len(game_state['connected_players']) == 0 and (game_state['game_started'] or game_state['countdown_started']):
        print("All players disconnected! Resetting game...")
        reset_game()
        return True
    
    return len(disconnected_players) > 0

def heartbeat_monitor():
    """Background thread to monitor player connections"""
    while True:
        time.sleep(5)  # Check every 5 seconds
        check_disconnected_players()

# Start heartbeat monitoring thread
heartbeat_thread = threading.Thread(target=heartbeat_monitor, daemon=True)
heartbeat_thread.start()
print("Heartbeat monitoring started")

if __name__ == '__main__':
    print("Starting Color Tap Battle Server...")
    print(f"Required players to start: {REQUIRED_PLAYERS}")
    print("Task Processing Model: Multi-threaded Flask with threading support")
    print("Server will handle multiple concurrent requests using threads")
    print(f"Usage: python server.py [player_count] (default: 2, min: 2, max: 10)")
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)