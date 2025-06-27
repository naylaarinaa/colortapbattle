from flask import Flask, jsonify, request
import random

app = Flask(__name__)

COLOR_NAMES = [
    "RED", "GREEN", "BLUE", "YELLOW", "PURPLE", "BLACK",
    "GRAY", "ORANGE", "PINK", "BROWN"
]

game_state = {
    'question_id_counter': 0,
    'current_correct_answer': None,
    'player_scores': {}
}

def generate_new_question():
    game_state['question_id_counter'] += 1
    
    question_text = random.choice(COLOR_NAMES)
    correct_color_name = random.choice([c for c in COLOR_NAMES if c != question_text])
    
    options = random.sample([c for c in COLOR_NAMES if c != correct_color_name], k=4)
    options.append(correct_color_name)
    random.shuffle(options)
    
    game_state['current_correct_answer'] = correct_color_name
    
    return {
        "question_id": game_state['question_id_counter'],
        "text": question_text,
        "text_color": correct_color_name,
        "options": options
    }

@app.route('/question', methods=['GET'])
def get_question():
    question_data = generate_new_question()
    return jsonify(question_data)

@app.route('/answer', methods=['POST'])
def post_answer():
    data = request.get_json()
    player_id = data.get('player_id', 'anonymous')
    player_answer = data.get('answer')

    if player_id not in game_state['player_scores']:
        game_state['player_scores'][player_id] = 0

    is_correct = (player_answer == game_state['current_correct_answer'])
    
    if is_correct:
        game_state['player_scores'][player_id] += 100

    response = {
        'correct': is_correct,
        'new_score': game_state['player_scores'][player_id]
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)