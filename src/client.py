import pygame, sys, os, socket, json, logging

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

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

def load_font(name, size):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../assets/{name}'))
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.SysFont(None, size)

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
    font = load_font('LuckiestGuy-Regular.ttf', 80)
    color_rgb = COLOR_MAP.get(color_name_for_rgb, (0, 0, 0))
    label = font.render(question_text, True, color_rgb)
    outline = font.render(question_text, True, (0, 0, 0))
    label_rect = label.get_rect(center=(WIDTH // 2 + 70, 190))
    screen.blit(outline, label_rect.move(2, 2))
    screen.blit(label, label_rect)

def draw_name_options(option_names):
    positions = []
    font = load_font('BalsamiqSans-Regular.ttf', 25)
    total_height = len(option_names) * 50
    start_y = HEIGHT // 2 - total_height // 2 + 120
    x = WIDTH // 2 + 80
    for i, name in enumerate(option_names):
        y = start_y + i * 55
        rect = pygame.Rect(x - 200, y - 22, 400, 44)
        pygame.draw.rect(screen, (250, 250, 241), rect, border_radius=15)
        pygame.draw.rect(screen, (163, 102, 71), rect, 3, border_radius=15)
        label = font.render(name, True, (70, 39, 24))
        screen.blit(label, label.get_rect(center=(x, y)))
        positions.append(rect)
    return positions

def get_user_answer(mouse_pos, positions, option_names):
    for rect, name in zip(positions, option_names):
        if rect.collidepoint(mouse_pos):
            return name
    return None

def draw_scores(scores, highlight_name=None):
    if not scores: return
    font_other = load_font('BalsamiqSans-Regular.ttf', 24)
    y_offset = 90
    for nomor, (player, player_score) in enumerate(sorted(scores.items(), key=lambda x: -x[1]), 1):
        score_text = f"{nomor}. {player}: {player_score}"
        label = font_other.render(score_text, True, (70, 39, 24))
        label_rect = label.get_rect(topleft=(38, y_offset + 6))
        bg_rect = pygame.Rect(30, y_offset, 150, 36)
        if player == highlight_name:
            pygame.draw.rect(screen, (250, 250, 241), bg_rect, border_radius=12)
            pygame.draw.rect(screen, (163, 102, 71), bg_rect, 3, border_radius=12)
        screen.blit(label, label_rect)
        y_offset += 40

def draw_popup_overlay(popup_type):
    if popup_type in ["correct", "wrong"]:
        try:
            img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../assets/{popup_type}.png'))
            popup_img = pygame.image.load(img_path).convert_alpha()
            popup_rect = popup_img.get_rect(center=(WIDTH//2, HEIGHT//2))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            screen.blit(popup_img, popup_rect)
        except pygame.error:
            show_popup("No Response", color=(100, 100, 100))
    elif popup_type == "noresponse":
        show_popup("No Response", color=(100, 100, 100))

def draw_final_scores_centered(scores, highlight_name=None):
    """
    Menampilkan skor akhir di tengah layar, dengan highlight untuk pemain sendiri.
    Diurutkan dari skor tertinggi ke terendah.
    """
    if not scores:
        return

    font_score = load_font('BalsamiqSans-Regular.ttf', 26)
    row_height = 50
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])  # ⬅️ urut menurun
    total_height = len(sorted_scores) * row_height
    start_y = (HEIGHT - total_height) // 2 + 30

    for i, (player, score) in enumerate(sorted_scores, 1):
        text = f"{i}. {player}: {score}"
        label = font_score.render(text, True, (70, 39, 24))
        label_rect = label.get_rect()

        # Buat background rectangle di tengah
        bg_width = label_rect.width + 50
        bg_height = row_height
        bg_x = (WIDTH - bg_width) // 2
        bg_y = start_y + (i - 1) * row_height
        bg_rect = pygame.Rect(bg_x, bg_y, bg_width, bg_height)

        if player == highlight_name:
            pygame.draw.rect(screen, (250, 250, 241), bg_rect, border_radius=12)
            pygame.draw.rect(screen, (163, 102, 71), bg_rect, 3, border_radius=12)

        label_rect.center = bg_rect.center
        screen.blit(label, label_rect)

def show_you_win_or_lose(client, final_scores):
    sorted_scores = sorted(final_scores.items(), key=lambda x: -x[1])
    winner_name, winner_score = sorted_scores[0]

    if client.player_username == winner_name:
        # Tampilkan halaman YOU WIN
        try:
            win_img = pygame.image.load(os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/winner.png'))).convert_alpha()
            screen.blit(pygame.transform.smoothscale(win_img, (WIDTH, HEIGHT)), (0, 0))
        except pygame.error:
            screen.fill((255, 255, 255))
            font = load_font('LuckiestGuy-Regular.ttf', 80)
            label = font.render("YOU WIN!", True, (0, 200, 0))
            screen.blit(label, label.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        pygame.display.flip()
        pygame.time.wait(4000)  # Delay sebelum lanjut ke final score

    
    pygame.display.flip()

def show_final_score_page_with_buttons(final_scores, client):
    try:
        final_img = pygame.image.load(os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/final_score.png'))).convert_alpha()
        screen.blit(pygame.transform.smoothscale(final_img, (WIDTH, HEIGHT)), (0, 0))
    except pygame.error:
        screen.fill((255, 255, 255))

    draw_final_scores_centered(final_scores, client.player_username)

    font_btn = load_font('LuckiestGuy-Regular.ttf', 36)
    btn_spacing = 40
    restart_btn = pygame.Rect(WIDTH // 2 - 180 - btn_spacing//2, HEIGHT - 100, 180, 50)
    exit_btn = pygame.Rect(WIDTH // 2 + btn_spacing//2, HEIGHT - 100, 120, 50)


    pygame.draw.rect(screen, (240, 169, 45), restart_btn, border_radius=10)
    pygame.draw.rect(screen, (240, 50, 45), exit_btn, border_radius=10)

    pygame.draw.rect(screen, (70, 39, 24), restart_btn, 2, border_radius=10)
    pygame.draw.rect(screen, (70, 39, 24), exit_btn, 2, border_radius=10)

    restart_label = font_btn.render("RESTART", True, (70, 39, 24))
    exit_label = font_btn.render("EXIT", True, (255, 255, 255))

    screen.blit(restart_label, restart_label.get_rect(center=restart_btn.center))
    screen.blit(exit_label, exit_label.get_rect(center=exit_btn.center))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if restart_btn.collidepoint(event.pos):
                    logger.info("🔁 Restart clicked")
                    client.restart_game()
                    os.execl(sys.executable, sys.executable, *sys.argv)

                elif exit_btn.collidepoint(event.pos):
                    logger.info("🚪 Exit clicked")
                    pygame.quit(); sys.exit()
        clock.tick(30)


def render_game_ui(status, score, current_question):
    screen.fill((255, 255, 255))
    screen.blit(main_bg, (0, 0))
    
    # Progress
    if status.get('current_question_number') and status.get('max_questions'):
        font_progress = load_font('BalsamiqSans-Regular.ttf', 25)
        progress_render = font_progress.render(f"{status['current_question_number']}/{status['max_questions']}", True, (0, 0, 0))
        screen.blit(progress_render, (WIDTH // 2 - progress_render.get_width() // 2 - 95, 68))
    
    # Question & options
    if current_question and current_question.get('text'):
        display_color_question(current_question.get('text'), current_question.get('text_color'))
        options = draw_name_options(current_question.get('options', []))
    else:
        options = []
    
    # Timer
    time_remaining = status.get('question_time_remaining', 0)
    remaining = max(0, int(time_remaining))
    font_timer = load_font('BalsamiqSans-Regular.ttf', 25)
    timer_color = (200, 0, 0) if remaining <= 3 else (0, 0, 0)
    timer_render = font_timer.render(f"{remaining}s", True, timer_color)
    screen.blit(timer_render, (WIDTH - timer_render.get_width() - 100, 68))
    
    # Score
    font_score = load_font('BalsamiqSans-Regular.ttf', 30)
    score_render = font_score.render(f"{score}", True, (0, 0, 0))
    score_x = WIDTH // 2 + progress_render.get_width() // 2 - score_render.get_width() + 50
    screen.blit(score_render, (score_x, 68))
    
    # Other scores
    draw_scores(status.get('scores', {}), client.player_username)
    
    return options

class ClientInterface:
    def __init__(self, player_username):
        self.player_username = player_username
        self.server_host = '127.0.0.1'
        self.server_port = 8889
        logger.info(f"🔗 Connected to server: {self.server_host}:{self.server_port}")
        self._last_status = None
        self._last_question_id = None  # Tambahkan tracking untuk question ID

    def send_http_request(self, request_text):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)
                s.connect((self.server_host, self.server_port))
                s.sendall(request_text.encode())
                response = b""
                while True:
                    part = s.recv(4096)
                    if not part: break
                    response += part
                    if b'\r\n\r\n' in response: break
                body = response.split(b'\r\n\r\n', 1)[-1] if b'\r\n\r\n' in response else response
                return json.loads(body.decode())
        except Exception as e:
            logger.error(f"🚫 Server error: {e}")
            return None

    def join_game(self):
        logger.info(f"🎲 Joining as '{self.player_username}'...")
        payload = {'player_username': self.player_username}
        payload_str = json.dumps(payload)
        req = f"POST /join HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: {len(payload_str)}\r\n\r\n{payload_str}"
        result = self.send_http_request(req)
        if result:
            logger.info(f"✅ Joined! Players: {result.get('player_count', 0)}/{result.get('required_players', 2)}")
        return result

    def get_game_status(self):
        req = f"GET /status?player_id={self.player_username} HTTP/1.0\r\n\r\n"
        result = self.send_http_request(req)
        
        # Log status changes - TAMBAHKAN TIMESUP
        if result and result.get('status'):
            status = result.get('status')
            if status != self._last_status and status in ['countdown', 'playing', 'finished', 'timesup']:
                if status == 'countdown':
                    logger.info(f"⏰ Countdown started")
                elif status == 'playing':
                    logger.info(f"🎮 Game started")
                elif status == 'finished':
                    logger.info(f"🏁 Game finished!")
                elif status == 'timesup':
                    logger.info(f"⏱️  Time's up!")
                self._last_status = status
        
        return result

    def get_question(self):
        req = "GET /question HTTP/1.0\r\n\r\n"
        result = self.send_http_request(req)
        
        # TAMBAHKAN LOG SAAT NERIMA SOAL BARU
        if result and result.get('question_id'):
            qid = result.get('question_id')
            if qid != self._last_question_id:
                text = result.get('text', '')
                color = result.get('text_color', '')
                question_num = result.get('question_number', 0)
                logger.info(f"❓ Q{question_num}: '{text}' in {color}")
                self._last_question_id = qid
        
        return result

    def send_answer(self, question_id, answer):
        payload = {'player_username': self.player_username, 'question_id': question_id, 'answer': answer}
        payload_str = json.dumps(payload)
        req = f"POST /answer HTTP/1.0\r\nContent-Type: application/json\r\nContent-Length: {len(payload_str)}\r\n\r\n{payload_str}"
        result = self.send_http_request(req)
        
        if result:
            if result.get('correct'):
                points = result.get('points_earned', 0)
                new_score = result.get('new_score', 0)
                logger.info(f"🎉 CORRECT! +{points} pts → {new_score}")
            elif result:
                logger.info(f"❌ Wrong answer")
        
        return result

    def restart_game(self):
        req = "POST /reset HTTP/1.0\r\n\r\n"
        result = self.send_http_request(req)
        if result and result.get("success"):
            logger.info("🔄 Game restart requested successfully")
        else:
            logger.error("🚫 Failed to restart game")

def show_instructions_modal():
    try:
        instr_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/instructions.png'))
        instr_img = pygame.transform.smoothscale(pygame.image.load(instr_img_path).convert_alpha(), (WIDTH, HEIGHT))
    except pygame.error:
        # Fallback: show text popup instead
        show_popup("Instructions: Match the color name with the text color!", color=(0, 0, 200))
        return
        
    font_button = load_font('LuckiestGuy-Regular.ttf', 38)
    button_rect = pygame.Rect(WIDTH // 2 - 205, HEIGHT - 115, 170, 54)
    waiting, button_clicked, pulse, pulse_dir, pulse_active = True, False, 0, 1, False
    
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
    try:
        lobby_img = pygame.transform.smoothscale(pygame.image.load(os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/waiting_lobby.png'))).convert_alpha(), (WIDTH, HEIGHT))
    except pygame.error:
        # Fallback: create simple background
        lobby_img = pygame.Surface((WIDTH, HEIGHT))
        lobby_img.fill((50, 50, 100))
        
    font_info = load_font('LuckiestGuy-Regular.ttf', 40)
    font_players = load_font('BalsamiqSans-Regular.ttf', 30)
    
    join_result = client.join_game()
    if not join_result:
        logger.error("🚫 Cannot connect to server!")
        show_popup("Failed to connect to server!", color=(255, 0, 0))
        pygame.quit(); sys.exit()
    
    while True:
        status = client.get_game_status()
        if not status:
            logger.error("🚫 Lost connection!")
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
    font_countdown = load_font('LuckiestGuy-Regular.ttf', 120)
    font_message = load_font('LuckiestGuy-Regular.ttf', 60)
    font_info = load_font('LuckiestGuy-Regular.ttf', 30)
    
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

# Load main background
try:
    main_bg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/main.png'))
    main_bg = pygame.transform.smoothscale(pygame.image.load(main_bg_path).convert_alpha(), (WIDTH, HEIGHT))
except pygame.error:
    main_bg = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        c = int(220 + (35 * y / HEIGHT))
        pygame.draw.line(main_bg, (c, c, 255), (0, y), (WIDTH, y))

def get_username_screen():
    try:
        bg_img = pygame.transform.smoothscale(pygame.image.load(os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/username.png'))).convert_alpha(), (WIDTH, HEIGHT))
    except pygame.error:
        bg_img = pygame.Surface((WIDTH, HEIGHT))
        bg_img.fill((100, 150, 200))
        
    font = load_font('LuckiestGuy-Regular.ttf', 48)
    input_box = pygame.Rect(WIDTH // 2 - 80, HEIGHT // 2 - 30, 380, 60)
    color_outline = (220, 120, 40)
    color_outline_hover = (255, 180, 60)
    color_outline_active = (255, 120, 40)
    active, username, done = False, '', False
    button_rect = pygame.Rect(input_box.right + 16, input_box.centery - 28, 56, 56)
    input_anim = button_anim = input_anim_target = button_anim_target = 0
    button_clicked = input_clicked = False

    while not done:
        mouse_pos = pygame.mouse.get_pos()
        hovering_input = input_box.collidepoint(mouse_pos)
        hovering_button = button_rect.collidepoint(mouse_pos) and username.strip()

        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hovering_input or hovering_button else pygame.SYSTEM_CURSOR_ARROW)

        input_anim_target = 2 if input_clicked else (1 if hovering_input else 0)
        button_anim_target = 2 if button_clicked else (1 if hovering_button else 0)
        input_anim += (input_anim_target - input_anim) * 0.3
        button_anim += (button_anim_target - button_anim) * 0.3

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active, input_clicked = True, True
                else:
                    active, input_clicked = False, False
                if button_rect.collidepoint(event.pos) and username.strip():
                    button_clicked = True
            if event.type == pygame.MOUSEBUTTONUP:
                input_clicked = False
                if button_clicked and button_rect.collidepoint(event.pos) and username.strip():
                    done = True
                button_clicked = False
            if event.type == pygame.KEYDOWN and active:
                if event.key == pygame.K_RETURN and username.strip():
                    done = True
                elif event.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                elif len(username) < 16 and event.key == pygame.K_DELETE:
                    username = ''
                elif len(username) < 16 and event.unicode.isprintable():
                    username += event.unicode

        screen.blit(bg_img, (0, 0))

        input_color = color_outline_active if input_anim > 1.5 else (color_outline_hover if input_anim > 0.5 else color_outline)
        input_box_anim = input_box.inflate(int(16 * input_anim), int(10 * input_anim))
        input_box_anim.center = input_box.center
        pygame.draw.rect(screen, (255, 255, 255), input_box_anim, border_radius=10)
        pygame.draw.rect(screen, input_color, input_box_anim, 4 + int(2 * input_anim), border_radius=10)

        txt_surface = font.render(username, True, (255, 255, 255))
        outline_offsets = [(-2,0),(2,0),(0,-2),(0,2)]
        for ox, oy in outline_offsets:
            outline_surface = font.render(username, True, color_outline)
            screen.blit(outline_surface, (input_box_anim.x+10+ox, input_box_anim.y+10+oy))
        screen.blit(txt_surface, (input_box_anim.x+10, input_box_anim.y+10))

        if not username and not active:
            hint_font = load_font('LuckiestGuy-Regular.ttf', 28)
            hint = hint_font.render("max 16 karakter", True, (255, 255, 255))
            for ox, oy in outline_offsets:
                hint_outline = hint_font.render("max 16 karakter", True, color_outline)
                screen.blit(hint_outline, (input_box_anim.x+12+ox, input_box_anim.y+18+oy))
            screen.blit(hint, (input_box_anim.x+12, input_box_anim.y+18))

        button_color = color_outline_active if button_anim > 1.5 else (color_outline_hover if button_anim > 0.5 else color_outline)
        button_rect_anim = button_rect.inflate(int(12 * button_anim), int(12 * button_anim))
        button_rect_anim.center = button_rect.center
        pygame.draw.rect(screen, (255,255,255), button_rect_anim, border_radius=12)
        pygame.draw.rect(screen, button_color, button_rect_anim, 3 + int(2 * button_anim), border_radius=12)
        btn_label = font.render(">", True, button_color)
        btn_label_rect = btn_label.get_rect(center=button_rect_anim.center)
        btn_label_rect.y += 8
        screen.blit(btn_label, btn_label_rect)

        pygame.display.flip()
        clock.tick(30)
    return username.strip()

def show_special_screen(client, status_name, image_name, message):
    font_message = load_font('LuckiestGuy-Regular.ttf', 60 if status_name == 'timesup' else 40)
    try:
        img = pygame.transform.smoothscale(pygame.image.load(os.path.abspath(os.path.join(os.path.dirname(__file__), f'../assets/{image_name}.png'))).convert_alpha(), (WIDTH, HEIGHT))
        use_image = True
    except pygame.error:
        use_image = False
    
    while True:
        status = client.get_game_status()
        if not status:
            show_popup("Lost connection to server!", color=(255, 0, 0))
            pygame.quit(); sys.exit()
        if status.get('status') == status_name:
            render_game_ui(status, score, current_question)
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            if use_image:
                screen.blit(img, (0, 0))
            else:
                msg = font_message.render(message, True, (255, 255, 255))
                screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 50))
            draw_scores(status.get('scores', {}), client.player_username)
        elif status.get('status') in ('playing', 'finished') or status.get('game_started'):
            break
        else:
            break
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        pygame.display.flip()
        clock.tick(60)

# Main execution
logger.info("🎮 Color Tap Battle Client Starting...")

player_username = get_username_screen()
client = ClientInterface(player_username)
score, answered, current_question = 0, False, {}
last_question_id, last_time_remaining, time_up_shown = None, None, False

show_instructions_modal()
show_lobby_screen(client)
show_countdown_screen(client)

while True:
    status = client.get_game_status()
    if not status:
        logger.error("🚫 Lost connection!")
        show_popup("Lost connection to server!", color=(255, 0, 0))
        break
            
    if status.get('status') == 'finished':
        final_scores = status.get('final_scores', {})

        # Logging ke terminal
        for i, (player, player_score) in enumerate(sorted(final_scores.items(), key=lambda x: -x[1]), 1):
            logger.info(f"🏆 {i}. {player}: {player_score} points")

        # Tampilkan YOU WIN (jika pemain menang)
        show_you_win_or_lose(client, final_scores)

        # Tampilkan halaman skor akhir + tombol
        show_final_score_page_with_buttons(final_scores, client)
        break




        
    if status.get('status') == 'timesup':
        show_special_screen(client, 'timesup', 'timesup', "TIME'S UP!")
        continue

    if status.get('status') == 'roundcompleted_waiting':
        if status.get('current_question_number', 0) < status.get('max_questions', 10):
            show_special_screen(client, 'roundcompleted_waiting', 'roundcompleted', "ROUND COMPLETED!")
        continue

    if status.get('status') == 'roundcompleted_all':
        if status.get('current_question_number', 0) < status.get('max_questions', 10):
            show_special_screen(client, 'roundcompleted_all', 'roundcompleted', "ROUND COMPLETED!")
        continue

    
    if status.get('status') == 'playing':
        get_synchronized_question()
    
    option_positions = render_game_ui(status, score, current_question)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            logger.info("👋 User quit")
            pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and not answered and current_question and status.get('question_time_remaining', 0) > 0:
            chosen_name = get_user_answer(event.pos, option_positions, current_question.get('options', []))
            if chosen_name:
                answered = True
                result = client.send_answer(current_question.get('question_id'), chosen_name)
                popup_type = "correct" if result and result.get('correct') else ("wrong" if result else "noresponse")
                if popup_type == "correct":
                    score = result.get('new_score', score)
                
                popup_start = pygame.time.get_ticks()
                round_completed_triggered = False
                while True:
                    status_popup = client.get_game_status()
                    status_code = status_popup.get('status', '')
                    render_game_ui(status_popup, score, current_question)
                    draw_popup_overlay(popup_type)
                    pygame.display.flip()
                    clock.tick(30)
                    
                    if (status_code.startswith("roundcompleted") or status_code == "timesup") and not round_completed_triggered:
                        round_completed_triggered = True
                        pygame.time.wait(1000)
                        break
                    if pygame.time.get_ticks() - popup_start >= 10000:
                        break
                pygame.event.clear()
    
    pygame.display.flip()
    clock.tick(FPS)

logger.info("👋 Client shutting down...")
pygame.quit()
sys.exit()