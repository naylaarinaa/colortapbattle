def generate_question(color_names):
    import random
    text = random.choice(color_names)
    text_color_name = random.choice(color_names)
    return text, text_color_name

def validate_answer(user_color_name, correct_color_name):
    return user_color_name == correct_color_name

def update_player_location(players, player_id, x, y):
    if player_id in players:
        players[player_id]['location'] = (x, y)

def get_all_players(players):
    return {'status': 'OK', 'players': list(players.keys())}

def get_player_face(players, player_id):
    if player_id in players:
        return {'status': 'OK', 'face': players[player_id]['face']}
    return {'status': 'ERROR'}

def get_player_location(players, player_id):
    if player_id in players:
        return {'status': 'OK', 'location': players[player_id]['location']}
    return {'status': 'ERROR'}