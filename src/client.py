import pygame
import sys
import os
import requests

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Color Tap Battle")
clock = pygame.time.Clock()
FPS = 60

COLOR_MAP = {
    'RED': (255, 0, 0), 'GREEN': (0, 255, 0), 'BLUE': (0, 0, 255),
    'YELLOW': (255, 255, 0), 'PURPLE': (128, 0, 128), 'BLACK': (0, 0, 0),
    'GRAY': (128, 128, 128), 'ORANGE': (255, 165, 0), 'PINK': (255, 105, 180),
    'BROWN': (139, 69, 19),
}

def show_instructions_modal():
    instr_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/instructions.png'))
    instr_img = pygame.image.load(instr_img_path).convert_alpha()
    instr_img = pygame.transform.smoothscale(instr_img, (WIDTH, HEIGHT))
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_button = pygame.font.Font(font_path, 38)
    button_rect = pygame.Rect(WIDTH // 2 - 205, HEIGHT - 120, 170, 54)
    waiting, button_clicked = True, False
    pulse, pulse_dir, pulse_active = 0, 1, False
    
    while waiting:
        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and is_hover:
                button_clicked = True
                pulse_active = True
                pulse, pulse_dir = 0, 1
            if event.type == pygame.MOUSEBUTTONUP and is_hover and button_clicked:
                waiting = False
        
        if pulse_active:
            pulse += pulse_dir * 4
            if pulse > 24:
                pulse_dir = -1
            if pulse < 0:
                pulse_active, pulse, pulse_dir = False, 0, 1
                
        screen.fill((255, 255, 255))
        screen.blit(instr_img, (0, 0))
        
        btn_color = (220, 155, 50) if is_hover else (240, 169, 45)
        btn_rect_anim = button_rect.inflate(pulse, pulse)
        pygame.draw.rect(screen, btn_color, btn_rect_anim, border_radius=12)
        pygame.draw.rect(screen, (70, 39, 24), btn_rect_anim, 2, border_radius=12)
        btn_label = font_button.render("START", True, (70, 39, 24))
        screen.blit(btn_label, (btn_rect_anim.centerx - btn_label.get_width() // 2, btn_rect_anim.centery - btn_label.get_height() // 2))
        pygame.display.flip()
        clock.tick(60)

def show_popup(message, color=(0, 0, 0)):
    popup_width, popup_height = 320, 120
    popup_rect = pygame.Rect((WIDTH - popup_width) // 2, (HEIGHT - popup_height) // 2, popup_width, popup_height)
    font_popup = pygame.font.SysFont(None, 54, bold=True)
    pygame.draw.rect(screen, (255, 255, 255), popup_rect, border_radius=18)
    pygame.draw.rect(screen, color, popup_rect, 4, border_radius=18)
    label = font_popup.render(message, True, color)
    screen.blit(label, (popup_rect.centerx - label.get_width() // 2, popup_rect.centery - label.get_height() // 2))
    pygame.display.flip()
    pygame.time.wait(800)

def display_color_question(question_text, color_name_for_rgb):
    font = pygame.font.SysFont(None, 80)
    color_rgb = COLOR_MAP.get(color_name_for_rgb, (0, 0, 0))
    outline = font.render(question_text, True, (0, 0, 0))
    label = font.render(question_text, True, color_rgb)
    label_rect = label.get_rect(center=(WIDTH // 2, 100))
    screen.blit(outline, label_rect.move(2, 2))
    screen.blit(label, label_rect)

def draw_name_options(option_names):
    positions, spacing, y = [], WIDTH // (len(option_names) + 1), 250
    font = pygame.font.SysFont(None, 40)
    for i, name in enumerate(option_names):
        x = spacing * (i + 1)
        rect = pygame.Rect(x - 70, y - 30, 140, 60)
        pygame.draw.rect(screen, (200, 200, 200), rect, border_radius=15)
        pygame.draw.rect(screen, (0, 0, 0), rect, 3, border_radius=15)
        label = font.render(name, True, (0, 0, 0))
        screen.blit(label, label.get_rect(center=(x, y)))
        positions.append(rect)
    return positions

def get_user_answer(mouse_pos, positions, option_names):
    for rect, name in zip(positions, option_names):
        if rect.collidepoint(mouse_pos):
            return name
    return None

class ClientInterface:
    def __init__(self, player_username):
        self.player_username = player_username
        self.server_url = 'http://127.0.0.1:8080'

    def join_game(self):
        """Join the multiplayer game lobby"""
        payload = {'player_username': self.player_username}
        print(f"Attempting to join game as {self.player_username}")
        try:
            response = requests.post(f"{self.server_url}/join", json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"Join response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"Failed to join game: {e}")
            return None

    def get_game_status(self):
        """Get current game status and send heartbeat"""
        try:
            # Send player_id as query parameter for heartbeat tracking
            response = requests.get(f"{self.server_url}/status", params={'player_id': self.player_username})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get status: {e}")
            return None

    def get_question(self):
        try:
            response = requests.get(f"{self.server_url}/question")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    def send_answer(self, question_id, answer):
        payload = {'player_username': self.player_username, 'question_id': question_id, 'answer': answer}
        try:
            response = requests.post(f"{self.server_url}/answer", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
def show_countdown_screen(client):
    """Display 3-second countdown before game starts"""
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_countdown = pygame.font.Font(font_path, 120)
    font_message = pygame.font.Font(font_path, 60)
    
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit()
            sys.exit()
        
        if status.get('status') == 'countdown':
            countdown_remaining = status.get('countdown_remaining', 0)
            countdown_number = max(1, int(countdown_remaining) + 1)
            
            # Fill screen with white background
            screen.fill((255, 255, 255))
            
            # Show "GET READY!" message
            ready_msg = font_message.render("GET READY!", True, (200, 0, 0))
            screen.blit(ready_msg, (WIDTH // 2 - ready_msg.get_width() // 2, HEIGHT // 2 - 120))
            
            # Show countdown number
            if countdown_number <= 3:
                # Color changes: 3=red, 2=orange, 1=green
                colors = {3: (255, 0, 0), 2: (255, 140, 0), 1: (0, 200, 0)}
                countdown_color = colors.get(countdown_number, (0, 0, 0))
                
                countdown_text = font_countdown.render(str(countdown_number), True, countdown_color)
                screen.blit(countdown_text, (WIDTH // 2 - countdown_text.get_width() // 2, HEIGHT // 2 - 30))
            
            # Show player count
            font_info = pygame.font.Font(font_path, 30)
            player_count = status.get('player_count', 0)
            players_msg = font_info.render(f"Players Ready: {player_count}", True, (100, 100, 100))
            screen.blit(players_msg, (WIDTH // 2 - players_msg.get_width() // 2, HEIGHT // 2 + 100))
            
        elif status.get('game_started'):
            print("Countdown finished! Starting game...")
            break
        else:
            # Should not happen, but handle gracefully
            break
            
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        pygame.display.flip()
        clock.tick(60)  # Higher FPS for smooth countdown


def show_lobby_screen(client):
    """Display waiting screen until enough players join"""
    # Use the same font path as in show_instructions_modal
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_path_2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/BalsamiqSans-Regular.ttf'))

    # Load waiting lobby background
    lobby_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/waiting_lobby.png'))
    lobby_img = pygame.image.load(lobby_img_path).convert_alpha()
    lobby_img = pygame.transform.smoothscale(lobby_img, (WIDTH, HEIGHT))
    
    # Use the custom font instead of system fonts
    font_info = pygame.font.Font(font_path, 40)
    font_players = pygame.font.Font(font_path_2, 30)
    
    # Join the game
    join_result = client.join_game()
    if not join_result:
        show_popup("Failed to connect to server!", color=(255, 0, 0))
        pygame.quit()
        sys.exit()
    
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit()
            sys.exit()
        
        print(f"Lobby status: {status}")  # Debug output
        
        if status.get('countdown_started') or status.get('game_started'):
            print("Countdown started or game started! Exiting lobby...")
            break
            
        # Draw background image
        screen.blit(lobby_img, (0, 0))
        
        # Player count (bottom left, not all the way)
        player_count = status.get('player_count', 0)
        required_players = status.get('required_players', 2)
        players_needed = status.get('players_needed', required_players)
        count_msg = font_info.render(f"Players: {player_count}/{required_players}", True, (255, 255, 255))
        screen.blit(count_msg, (100, HEIGHT - 120))
        
        if players_needed > 0:
            need_msg = font_players.render(f"Need {players_needed} more player(s)", True, (255, 255, 255))
            screen.blit(need_msg, (100, HEIGHT - 80))
        else:
            ready_msg = font_players.render("Starting countdown...", True, (0, 255, 0))
            screen.blit(ready_msg, (100, HEIGHT - 80))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        
        pygame.display.flip()
        clock.tick(10)  # Lower FPS for lobby
player_username = input("Masukkan Usernme Anda: ")
client = ClientInterface(player_username)
score, answered = 0, False
current_question = {} 
last_question_id = None
last_time_remaining = None
time_up_shown = False

# Initialize global variables
last_time_remaining = None
time_up_shown = False

show_instructions_modal()

# Show lobby and wait for game to start
show_lobby_screen(client)

# Show countdown screen
show_countdown_screen(client)

def get_synchronized_question():
    """Get the current synchronized question from server"""
    global current_question, answered, last_question_id, time_up_shown
    new_question = client.get_question()
    if new_question and new_question.get('question_id') != last_question_id:
        current_question = new_question
        answered = False
        last_question_id = new_question.get('question_id')
        time_up_shown = False  # Reset time up flag for new question
        return True
    return False


# Game loop
while True:
    
    # Get game status to check if game is still running
    status = client.get_game_status()
    if not status:
        show_popup("Lost connection to server!", color=(255, 0, 0))
        break
    
    if status.get('status') == 'finished':
        # Show final scores
        screen.fill((255, 255, 255))
        font_end = pygame.font.SysFont(None, 60)
        end_render = font_end.render("Game Finished!", True, (0, 0, 0))
        screen.blit(end_render, (WIDTH // 2 - end_render.get_width() // 2, HEIGHT // 2 - 60))
        
        final_scores = status.get('final_scores', {})
        y_offset = HEIGHT // 2
        font_scores = pygame.font.SysFont(None, 40)
        for player, player_score in final_scores.items():
            score_text = f"{player}: {player_score}"
            score_render = font_scores.render(score_text, True, (0, 0, 0))
            screen.blit(score_render, (WIDTH // 2 - score_render.get_width() // 2, y_offset))
            y_offset += 40
        
        pygame.display.flip()
        pygame.time.wait(5000)
        break
    
    # Get current question
    get_synchronized_question()
    
    screen.fill((255, 255, 255))
    
    # Display question progress
    if status.get('current_question_number') and status.get('max_questions'):
        font = pygame.font.SysFont(None, 36)
        progress_render = font.render(f"Question {status['current_question_number']} of {status['max_questions']}", True, (0, 0, 0))
        screen.blit(progress_render, (WIDTH // 2 - progress_render.get_width() // 2, 30))

    # Display question and options
    option_positions = []
    if current_question and current_question.get('text'):
        display_color_question(current_question.get('text'), current_question.get('text_color'))
        option_positions = draw_name_options(current_question.get('options', []))
    
    # Display synchronized timer
    time_remaining = status.get('question_time_remaining', 0)
    remaining = max(0, int(time_remaining))
    font_timer = pygame.font.SysFont(None, 40)
    timer_color = (200, 0, 0) if remaining <= 3 else (0, 0, 0)
    timer_render = font_timer.render(f"Time left: {remaining}s", True, timer_color)
    screen.blit(timer_render, (WIDTH - 220, 10))
    
    # Show status if all players answered
    if status.get('all_answered'):
        font_status = pygame.font.SysFont(None, 30)
        status_render = font_status.render("All players answered! Moving to next...", True, (0, 150, 0))
        screen.blit(status_render, (WIDTH // 2 - status_render.get_width() // 2, 65))

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        if event.type == pygame.MOUSEBUTTONDOWN and not answered and current_question and time_remaining > 0:
            mouse_pos = pygame.mouse.get_pos()
            chosen_name = get_user_answer(mouse_pos, option_positions, current_question.get('options', []))
            
            if chosen_name:
                answered = True
                result = client.send_answer(current_question.get('question_id'), chosen_name)
                
                if result and result.get('correct'):
                    score = result.get('new_score', score)
                    time_points = result.get('time_points', 0)
                    bonus_points = result.get('bonus_points', 0)
                    total_points = result.get('points_earned', 0)
                    
                    if result.get('first_correct'):
                        show_popup(f"Correct! +{time_points} pts (time) + {bonus_points} pts (first) = {total_points} pts!", color=(255, 215, 0))
                    else:
                        show_popup(f"Correct! +{time_points} pts (time)", color=(0, 180, 0))
                elif result:
                    show_popup("Wrong! +0 pts", color=(200, 0, 0))
                else:
                    show_popup("No Response", color=(100, 100, 100))

                pygame.event.clear()

    # Check if time ran out and show "Time's Up!" message
    if not answered and time_remaining <= 0 and not time_up_shown and current_question:
        show_popup("Time's Up!", color=(255, 140, 0))
        time_up_shown = True
    
    # Check if all players answered and show message
    if status.get('all_answered') and not answered and current_question:
        show_popup("All players answered!", color=(0, 100, 255))
    
    last_time_remaining = time_remaining

    # Display current score and leaderboard
    font_score = pygame.font.SysFont(None, 30)
    score_render = font_score.render(f"Your Score: {score}", True, (0, 0, 0))
    screen.blit(score_render, (10, 10))
    
   
    
    # Show other players' scores
    if status.get('scores'):
        y_offset = 70
        font_other = pygame.font.SysFont(None, 24)
        for player, player_score in status['scores'].items():
            if player != client.player_username:
                other_score = font_other.render(f"{player}: {player_score}", True, (100, 100, 100))
                screen.blit(other_score, (10, y_offset))
                y_offset += 25

    pygame.display.flip()
    clock.tick(FPS)

# Game ended
pygame.quit()
sys.exit()