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
    'game_start_time': None,
    'question_start_time': None,
    'current_question_number': 0,
    'max_questions': 10,
    'question_duration': 10,  # seconds per question
    'players_ready': set(),
    'game_finished': False,
    'first_correct_answer': None,  # Track who answered first for current question
    'answered_players': set()  # Track who has answered current question
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

def start_game():
    """Start the game timer and initialize first question"""
    game_state['game_started'] = True
    game_state['game_start_time'] = time.time()
    game_state['current_question_number'] = 1
    game_state['current_question'] = generate_new_question()
    game_state['question_start_time'] = time.time()
    print(f"Game started with {len(game_state['connected_players'])} players!")

def check_and_start_game():
    """Check if we have enough players to start the game"""
    if not game_state['game_started'] and len(game_state['connected_players']) >= REQUIRED_PLAYERS:
        start_game()

@app.route('/join', methods=['POST'])
def join_game():
    """Player joins the game lobby"""
    data = request.get_json()
    player_id = data.get('player_username', data.get('player_id', 'anonymous'))  # Accept both field names
    
    print(f"Player {player_id} attempting to join. Current players: {list(game_state['connected_players'])}")
    
    # If game is finished, reset it automatically
    if game_state.get('game_finished', False):
        reset_game()
    
    if player_id in game_state['connected_players']:
        print(f"Player {player_id} already connected")
        return jsonify({'status': 'already_connected', 'message': 'Player already connected'})
    
    game_state['connected_players'].add(player_id)
    game_state['player_scores'][player_id] = 0
    
    print(f"Player {player_id} joined. Total players: {len(game_state['connected_players'])}")
    
    check_and_start_game()
    
    return jsonify({
        'status': 'joined',
        'player_count': len(game_state['connected_players']),
        'game_started': game_state['game_started']
    })

@app.route('/status', methods=['GET'])
def get_game_status():
    """Get current game status"""
    if not game_state['game_started']:
        return jsonify({
            'status': 'waiting',
            'player_count': len(game_state['connected_players']),
            'players_needed': max(0, REQUIRED_PLAYERS - len(game_state['connected_players'])),
            'required_players': REQUIRED_PLAYERS,
            'game_started': False
        })
    
    current_time = time.time()
    question_elapsed = current_time - game_state['question_start_time']
    
    # Check if all players have answered
    all_answered = len(game_state['answered_players']) >= len(game_state['connected_players'])
    
    # Check if we need to move to next question (either time up or all answered)
    if question_elapsed >= game_state['question_duration'] or all_answered:
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
    player_id = data.get('player_username', data.get('player_id', 'anonymous'))  # Accept both field names
    player_answer = data.get('answer')

    if player_id not in game_state['player_scores']:
        game_state['player_scores'][player_id] = 0

    # Check if player already answered this question
    if player_id in game_state['answered_players']:
        return jsonify({
            'correct': False,
            'new_score': game_state['player_scores'][player_id],
            'all_scores': game_state['player_scores'],
            'message': 'Already answered this question'
        })

    # Mark player as having answered
    game_state['answered_players'].add(player_id)
    
    is_correct = (player_answer == game_state['current_correct_answer'])
    bonus_points = 0
    is_first_correct = False
    
    if is_correct:
        # Base points for correct answer
        game_state['player_scores'][player_id] += 100
        
        # Check if this is the first correct answer
        if game_state['first_correct_answer'] is None:
            game_state['first_correct_answer'] = player_id
            game_state['player_scores'][player_id] += 50  # Bonus for first correct
            bonus_points = 50
            is_first_correct = True

    response = {
        'correct': is_correct,
        'new_score': game_state['player_scores'][player_id],
        'all_scores': game_state['player_scores'],
        'first_correct': is_first_correct,
        'bonus_points': bonus_points
    }
    
    return jsonify(response)

def reset_game():
    """Reset the game state for a new game"""
    game_state.update({
        'question_id_counter': 0,
        'current_question': None,
        'current_correct_answer': None,
        'player_scores': {player: 0 for player in game_state['connected_players']},
        'game_started': False,
        'game_start_time': None,
        'question_start_time': None,
        'current_question_number': 0,
        'players_ready': set(),
        'game_finished': False,
        'first_correct_answer': None,
        'answered_players': set()
    })
    print("Game reset - ready for new players!")

if __name__ == '__main__':
    print("Starting Color Tap Battle Server...")
    print(f"Required players to start: {REQUIRED_PLAYERS}")
    print("Task Processing Model: Multi-threaded Flask with threading support")
    print("Server will handle multiple concurrent requests using threads")
    print(f"Usage: python server.py [player_count] (default: 2, min: 2, max: 10)")
    app.run(host='127.0.0.1', port=8080, debug=False, threaded=True)