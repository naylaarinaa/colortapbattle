import pygame
import sys
import os
import socket
import json

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

def show_popup(message, color=(0, 0, 0)):
    popup_rect = pygame.Rect((WIDTH-320)//2, (HEIGHT-120)//2, 320, 120)
    font_popup = pygame.font.SysFont(None, 54, bold=True)
    pygame.draw.rect(screen, (255, 255, 255), popup_rect, border_radius=18)
    pygame.draw.rect(screen, color, popup_rect, 4, border_radius=18)
    label = font_popup.render(message, True, color)
    screen.blit(label, (popup_rect.centerx - label.get_width() // 2, popup_rect.centery - label.get_height() // 2))
    pygame.display.flip()
    pygame.time.wait(800)

def show_popup_with_image(message, image_filename, display_time=800):
    try:
        img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets', image_filename))
        popup_img = pygame.image.load(img_path).convert_alpha()
        popup_rect = popup_img.get_rect(center=(WIDTH//2, HEIGHT//2))
        screen_backup = screen.copy()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        screen.blit(overlay, (0, 0))
        screen.blit(popup_img, popup_rect)
        pygame.display.flip()
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < display_time:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
            pygame.time.wait(10)
        screen.blit(screen_backup, (0, 0))
    except pygame.error:
        show_popup(message)

def display_color_question(question_text, color_name_for_rgb):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font = pygame.font.Font(font_path, 80)
    color_rgb = COLOR_MAP.get(color_name_for_rgb, (0, 0, 0))
    label = font.render(question_text, True, color_rgb)
    outline = font.render(question_text, True, (0, 0, 0))
    label_rect = label.get_rect(center=(WIDTH // 2, 120))
    bg_rect = pygame.Rect(label_rect.left - 30, label_rect.top - 20, label_rect.width + 60, label_rect.height + 40)
    pygame.draw.rect(screen, (255, 255, 255), bg_rect, border_radius=18)
    pygame.draw.rect(screen, (200, 200, 200), bg_rect, 3, border_radius=18)
    screen.blit(outline, label_rect.move(2, 2))
    screen.blit(label, label_rect)

def draw_name_options(option_names):
    positions, spacing, y = [], WIDTH // (len(option_names) + 1), 250
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/BalsamiqSans-Regular.ttf'))
    font = pygame.font.Font(font_path, 40)
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
        self.server_host = '127.0.0.1'
        self.server_port = 8889

    def send_http_request(self, request_text):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_host, self.server_port))
            s.sendall(request_text.encode())
            response = b""
            while True:
                part = s.recv(4096)
                if not part: break
                response += part
                if b'\r\n\r\n' in response: break
            body = response.split(b'\r\n\r\n', 1)[-1] if b'\r\n\r\n' in response else response
            try:
                return json.loads(body.decode())
            except Exception:
                return None

    def join_game(self):
        payload = {'player_username': self.player_username}
        payload_str = json.dumps(payload)
        req = (
            "POST /join HTTP/1.0\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload_str)}\r\n\r\n"
            f"{payload_str}"
        )
        return self.send_http_request(req)

    def get_game_status(self):
        req = f"GET /status?player_id={self.player_username} HTTP/1.0\r\n\r\n"
        return self.send_http_request(req)

    def get_question(self):
        req = "GET /question HTTP/1.0\r\n\r\n"
        return self.send_http_request(req)

    def send_answer(self, question_id, answer):
        payload = {'player_username': self.player_username, 'question_id': question_id, 'answer': answer}
        payload_str = json.dumps(payload)
        req = (
            "POST /answer HTTP/1.0\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(payload_str)}\r\n\r\n"
            f"{payload_str}"
        )
        return self.send_http_request(req)

def show_instructions_modal():
    instr_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/instructions.png'))
    instr_img = pygame.image.load(instr_img_path).convert_alpha()
    instr_img = pygame.transform.smoothscale(instr_img, (WIDTH, HEIGHT))
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_button = pygame.font.Font(font_path, 38)
    button_rect = pygame.Rect(WIDTH // 2 - 205, HEIGHT - 115, 170, 54)
    waiting, button_clicked = True, False
    pulse, pulse_dir, pulse_active = 0, 1, False
    while waiting:
        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and is_hover:
                button_clicked, pulse_active, pulse, pulse_dir = True, True, 0, 1
            if event.type == pygame.MOUSEBUTTONUP and is_hover and button_clicked:
                waiting = False
        if pulse_active:
            pulse += pulse_dir * 4
            if pulse > 24: pulse_dir = -1
            if pulse < 0: pulse_active, pulse, pulse_dir = False, 0, 1
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

def show_lobby_screen(client):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_path_2 = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/BalsamiqSans-Regular.ttf'))
    lobby_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/waiting_lobby.png'))
    lobby_img = pygame.transform.smoothscale(pygame.image.load(lobby_img_path).convert_alpha(), (WIDTH, HEIGHT))
    font_info = pygame.font.Font(font_path, 40)
    font_players = pygame.font.Font(font_path_2, 30)
    join_result = client.join_game()
    if not join_result:
        show_popup("Failed to connect to server!", color=(255, 0, 0))
        pygame.quit(); sys.exit()
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('countdown_started') or status.get('game_started'):
            break
        screen.blit(lobby_img, (0, 0))
        player_count = status.get('player_count', 0)
        required_players = status.get('required_players', 2)
        players_needed = status.get('players_needed', required_players)
        count_msg = font_info.render(f"Players: {player_count}/{required_players}", True, (255, 255, 255))
        screen.blit(count_msg, (100, HEIGHT - 120))
        msg = (font_players.render(f"Need {players_needed} more player(s)", True, (255, 255, 255))
               if players_needed > 0 else font_players.render("Starting countdown...", True, (0, 255, 0)))
        screen.blit(msg, (100, HEIGHT - 80))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(10)

def show_countdown_screen(client):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_countdown = pygame.font.Font(font_path, 120)
    font_message = pygame.font.Font(font_path, 60)
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('status') == 'countdown':
            countdown_number = max(1, int(status.get('countdown_remaining', 0)) + 1)
            screen.fill((255, 255, 255))
            ready_msg = font_message.render("GET READY!", True, (200, 0, 0))
            screen.blit(ready_msg, (WIDTH // 2 - ready_msg.get_width() // 2, HEIGHT // 2 - 120))
            if countdown_number <= 3:
                colors = {3: (255, 0, 0), 2: (255, 140, 0), 1: (0, 200, 0)}
                countdown_color = colors.get(countdown_number, (0, 0, 0))
                countdown_text = font_countdown.render(str(countdown_number), True, countdown_color)
                screen.blit(countdown_text, (WIDTH // 2 - countdown_text.get_width() // 2, HEIGHT // 2 - 30))
            font_info = pygame.font.Font(font_path, 30)
            player_count = status.get('player_count', 0)
            players_msg = font_info.render(f"Players Ready: {player_count}", True, (100, 100, 100))
            screen.blit(players_msg, (WIDTH // 2 - players_msg.get_width() // 2, HEIGHT // 2 + 100))
        elif status.get('game_started'):
            break
        else:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(60)

def get_synchronized_question():
    global current_question, answered, last_question_id, time_up_shown
    new_question = client.get_question()
    qid = new_question.get('question_id') if new_question else None
    if qid and qid != last_question_id:
        current_question, answered, last_question_id, time_up_shown = new_question, False, qid, False
        return True
    return False

try:
    main_bg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/main.png'))
    main_bg = pygame.transform.smoothscale(pygame.image.load(main_bg_path).convert_alpha(), (WIDTH, HEIGHT))
except pygame.error:
    main_bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        c = int(220 + (35 * y / HEIGHT))
        pygame.draw.line(main_bg, (c, c, 255), (0, y), (WIDTH, y))

def get_username_screen():
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font = pygame.font.Font(font_path, 48)
    input_box = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2, 360, 60)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    username = ''
    done = False

    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                # If the user clicked on the input_box rect.
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        if username.strip():
                            done = True
                    elif event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    elif len(username) < 16 and event.unicode.isprintable():
                        username += event.unicode

        screen.fill((255, 255, 255))
        title = font.render("Masukkan Username Anda:", True, (0, 0, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))

        # Render the current text.
        txt_surface = font.render(username, True, (0, 0, 0))
        width = max(360, txt_surface.get_width()+20)
        input_box.w = width
        pygame.draw.rect(screen, color, input_box, 4, border_radius=10)
        screen.blit(txt_surface, (input_box.x+10, input_box.y+10))

        # Draw hint if empty
        if not username:
            hint_font = pygame.font.Font(font_path, 28)
            hint = hint_font.render("max 16 karakter", True, (180, 180, 180))
            screen.blit(hint, (input_box.x+12, input_box.y+18))

        pygame.display.flip()
        clock.tick(30)
    return username.strip()

player_username = get_username_screen()
client = ClientInterface(player_username)
score, answered, current_question = 0, False, {}
last_question_id, last_time_remaining, time_up_shown = None, None, False

show_instructions_modal()
show_lobby_screen(client)
show_countdown_screen(client)

def show_timesup_screen(client):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_message = pygame.font.Font(font_path, 60)
    try:
        timesup_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/timesup.png'))
        timesup_img = pygame.transform.smoothscale(pygame.image.load(timesup_img_path).convert_alpha(), (WIDTH, HEIGHT))
        use_image = True
    except pygame.error:
        use_image = False
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('status') == 'timesup':
            screen.fill((255, 255, 255))
            screen.blit(main_bg, (0, 0))
            if current_question and current_question.get('text'):
                display_color_question(current_question.get('text'), current_question.get('text_color'))
                draw_name_options(current_question.get('options', []))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            if use_image:
                screen.blit(timesup_img, (0, 0))
            else:
                timesup_msg = font_message.render("TIME'S UP!", True, (255, 255, 255))
                screen.blit(timesup_msg, (WIDTH // 2 - timesup_msg.get_width() // 2, HEIGHT // 2 - 50))
        elif status.get('status') in ('playing', 'finished'):
            break
        else:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(60)

def show_roundcompleted_waiting_screen(client):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_message = pygame.font.Font(font_path, 40)
    try:
        img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/roundcompleted.png'))
        img = pygame.transform.smoothscale(pygame.image.load(img_path).convert_alpha(), (WIDTH, HEIGHT))
        use_image = True
    except pygame.error:
        use_image = False
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('status') == 'roundcompleted_waiting':
            screen.fill((255, 255, 255))
            screen.blit(main_bg, (0, 0))
            if current_question and current_question.get('text'):
                display_color_question(current_question.get('text'), current_question.get('text_color'))
                draw_name_options(current_question.get('options', []))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            if use_image:
                screen.blit(img, (0, 0))
            else:
                completed_msg = font_message.render("ROUND COMPLETED!", True, (255, 255, 255))
                screen.blit(completed_msg, (WIDTH // 2 - completed_msg.get_width() // 2, HEIGHT // 2 - 100))
        elif status.get('status') in ('playing', 'finished'):
            break
        else:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(60)

def show_roundcompleted_all_screen(client):
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_message = pygame.font.Font(font_path, 50)
    try:
        img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/roundcompleted.png'))
        img = pygame.transform.smoothscale(pygame.image.load(img_path).convert_alpha(), (WIDTH, HEIGHT))
        use_image = True
    except pygame.error:
        use_image = False
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('status') == 'roundcompleted_all':
            screen.fill((255, 255, 255))
            screen.blit(main_bg, (0, 0))
            if current_question and current_question.get('text'):
                display_color_question(current_question.get('text'), current_question.get('text_color'))
                draw_name_options(current_question.get('options', []))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            if use_image:
                screen.blit(img, (0, 0))
            else:
                completed_msg = font_message.render("ROUND COMPLETED!", True, (255, 255, 255))
                screen.blit(completed_msg, (WIDTH // 2 - completed_msg.get_width() // 2, HEIGHT // 2 - 100))
        elif status.get('status') in ('playing', 'finished'):
            break
        else:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(60)

while True:
    status = client.get_game_status()
    if not status:
        show_popup("Lost connection to server!", color=(255, 0, 0))
        break
    if status.get('status') == 'finished':
        final_scores = status.get('final_scores', {})
        scores_text = "\n".join([f"{player}: {score}" for player, score in final_scores.items()])
        show_popup(f"Game Over!\n\nFinal Scores:\n{scores_text}", color=(0, 0, 200))
        break
    if status.get('status') == 'timesup':
        show_timesup_screen(client); continue
    if status.get('status') == 'roundcompleted_waiting':
        show_roundcompleted_waiting_screen(client); continue
    if status.get('status') == 'roundcompleted_all':
        show_roundcompleted_all_screen(client); continue
    if status.get('status') == 'playing':
        get_synchronized_question()
    screen.fill((255, 255, 255))
    screen.blit(main_bg, (0, 0))
    if status.get('current_question_number') and status.get('max_questions'):
        font = pygame.font.SysFont(None, 36)
        progress_render = font.render(f"Question {status['current_question_number']} of {status['max_questions']}", True, (0, 0, 0))
        screen.blit(progress_render, (WIDTH // 2 - progress_render.get_width() // 2, 30))
    option_positions = []
    if current_question and current_question.get('text'):
        display_color_question(current_question.get('text'), current_question.get('text_color'))
        option_positions = draw_name_options(current_question.get('options', []))
    time_remaining = status.get('question_time_remaining', 0)
    remaining = max(0, int(time_remaining))
    font_timer = pygame.font.SysFont(None, 40)
    timer_color = (200, 0, 0) if remaining <= 3 else (0, 0, 0)
    timer_render = font_timer.render(f"Time left: {remaining}s", True, timer_color)
    screen.blit(timer_render, (WIDTH - 220, 10))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and not answered and current_question and time_remaining > 0:
            mouse_pos = pygame.mouse.get_pos()
            chosen_name = get_user_answer(mouse_pos, option_positions, current_question.get('options', []))
            if chosen_name:
                answered = True
                result = client.send_answer(current_question.get('question_id'), chosen_name)
                if result and result.get('correct'):
                    score = result.get('new_score', score)
                    show_popup_with_image("", "correct.png", display_time=1000)
                elif result:
                    show_popup_with_image("", "wrong.png", display_time=1000)
                else:
                    show_popup("No Response", color=(100, 100, 100))
                pygame.event.clear()
    font_score = pygame.font.SysFont(None, 30)
    score_render = font_score.render(f"Your Score: {score}", True, (0, 0, 0))
    screen.blit(score_render, (10, 10))
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

pygame.quit()
sys.exit()