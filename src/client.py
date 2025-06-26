import pygame
import sys
import os
import socket
import json
import random

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Color Tap Battle")
clock = pygame.time.Clock()
FPS = 60

color_map = {
    'RED': (255, 0, 0), 'GREEN': (0, 255, 0), 'BLUE': (0, 0, 255),
    'YELLOW': (255, 255, 0), 'PURPLE': (128, 0, 128), 'BLACK': (0, 0, 0),
    'GRAY': (128, 128, 128), 'ORANGE': (255, 165, 0), 'PINK': (255, 105, 180),
    'BROWN': (139, 69, 19),
}
color_names = list(color_map.keys())

def show_instructions_modal():
    instr_img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/instructions.png'))
    instr_img = pygame.image.load(instr_img_path).convert_alpha()
    instr_img = pygame.transform.smoothscale(instr_img, (WIDTH, HEIGHT))
    font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../assets/LuckiestGuy-Regular.ttf'))
    font_button = pygame.font.Font(font_path, 38)
    button_rect = pygame.Rect(WIDTH//2 - 205, HEIGHT - 120, 170, 54)
    waiting, button_clicked = True, False
    pulse = 0
    pulse_dir = 1
    pulse_active = False
    while waiting:
        mouse_pos = pygame.mouse.get_pos()
        is_hover = button_rect.collidepoint(mouse_pos)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and is_hover:
                button_clicked = True
                pulse_active = True
                pulse = 0
                pulse_dir = 1
            if event.type == pygame.MOUSEBUTTONUP and is_hover and button_clicked:
                waiting = False
        # Animasi pulse SAAT DIKLIK
        if pulse_active:
            pulse += pulse_dir * 4
            if pulse > 24:
                pulse_dir = -1
            if pulse < 0:
                pulse_active = False
                pulse = 0
                pulse_dir = 1
        screen.fill((255,255,255))
        screen.blit(instr_img, (0, 0))
        # Button color & hover
        btn_color = (220, 155, 50) if is_hover else (240, 169, 45)  # hover sedikit lebih terang
        btn_rect_anim = button_rect.inflate(pulse, pulse)
        pygame.draw.rect(screen, btn_color, btn_rect_anim, border_radius=12)
        pygame.draw.rect(screen, (70, 39, 24), btn_rect_anim, 2, border_radius=12)  # #462718
        btn_label = font_button.render("START", True, (70, 39, 24))  # #462718
        screen.blit(btn_label, (btn_rect_anim.centerx - btn_label.get_width()//2, btn_rect_anim.centery - btn_label.get_height()//2))
        pygame.display.flip()
        clock.tick(60)

def show_popup(message, color=(0,0,0)):
    popup_width, popup_height = 320, 120
    popup_rect = pygame.Rect((WIDTH - popup_width)//2, (HEIGHT - popup_height)//2, popup_width, popup_height)
    font_popup = pygame.font.SysFont(None, 54, bold=True)
    pygame.draw.rect(screen, (255,255,255), popup_rect, border_radius=18)
    pygame.draw.rect(screen, color, popup_rect, 4, border_radius=18)
    label = font_popup.render(message, True, color)
    screen.blit(label, (popup_rect.centerx - label.get_width()//2, popup_rect.centery - label.get_height()//2))
    pygame.display.flip()
    pygame.time.wait(800)  # Lebih cepat

def generate_question():
    question_text = random.choice(color_names)
    correct_color_name = random.choice([c for c in color_names if c != question_text])
    color_rgb = color_map[correct_color_name]
    option_names = random.sample([c for c in color_names if c != correct_color_name], k=4)
    option_names.append(correct_color_name)
    random.shuffle(option_names)
    return question_text, correct_color_name, color_rgb, option_names

def display_color_question(question_text, color_rgb):
    font = pygame.font.SysFont(None, 80)
    outline = font.render(question_text, True, (0,0,0))
    label = font.render(question_text, True, color_rgb)
    label_rect = label.get_rect(center=(WIDTH//2, 100))
    screen.blit(outline, label_rect.move(2,2))
    screen.blit(label, label_rect)

def draw_name_options(option_names):
    positions, spacing, y = [], WIDTH // (len(option_names) + 1), 250
    font = pygame.font.SysFont(None, 40)
    for i, name in enumerate(option_names):
        x = spacing * (i + 1)
        rect = pygame.Rect(x-70, y-30, 140, 60)
        pygame.draw.rect(screen, (200,200,200), rect, border_radius=15)
        pygame.draw.rect(screen, (0,0,0), rect, 3, border_radius=15)
        label = font.render(name, True, (0,0,0))
        screen.blit(label, label.get_rect(center=(x, y)))
        positions.append(rect)
    return positions

def get_user_answer(mouse_pos, positions, option_names):
    for rect, name in zip(positions, option_names):
        if rect.collidepoint(mouse_pos):
            return name
    return None

def validate_answer(user_choice, correct_color_name):
    return user_choice == correct_color_name

class ClientInterface:
    def __init__(self, idplayer='1'):
        self.idplayer = idplayer
        self.server_address = ('127.0.0.1', 55555)
    def get_other_players(self):
        try:
            hasil = self.send_command("get_all_players")
            return hasil['players'] if hasil['status'] == 'OK' else []
        except: return []
    def get_players_face(self):
        try:
            hasil = self.send_command(f"get_players_face {self.idplayer}")
            return hasil['face'] if hasil['status'] == 'OK' else None
        except: return None
    def send_command(self, command_str):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(self.server_address)
        try:
            sock.sendall(command_str.encode())
            data_received = ""
            while True:
                data = sock.recv(16)
                if data:
                    data_received += data.decode()
                    if "\r\n\r\n" in data_received:
                        break
                else:
                    break
            return json.loads(data_received)
        except:
            return {"status": "ERROR"}
        finally:
            sock.close()
    def set_location(self, x, y):
        hasil = self.send_command(f"set_location {self.idplayer} {x} {y}")
        return hasil['status'] == 'OK'
    def get_location(self):
        hasil = self.send_command(f"get_location {self.idplayer}")
        if hasil['status'] == 'OK':
            x, y = map(int, hasil['location'].split(','))
            return x, y
        return None

class Pac:
    def __init__(self, id='1', isremote=False):
        self.id = id
        self.isremote = isremote
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.speed = 5
        self.client = ClientInterface(id)
    def move(self, keys):
        if not self.isremote:
            if keys[pygame.K_UP]: self.y -= self.speed
            if keys[pygame.K_DOWN]: self.y += self.speed
            if keys[pygame.K_LEFT]: self.x -= self.speed
            if keys[pygame.K_RIGHT]: self.x += self.speed
            self.client.set_location(self.x, self.y)
        else:
            lokasi = self.client.get_location()
            if lokasi: self.x, self.y = lokasi
    def draw(self, surface):
        pass

p_number = input("Player number >>> ")
current_player = Pac(p_number)
client = ClientInterface(p_number)
players = {pid: Pac(pid, isremote=True) for pid in client.get_other_players() if pid != p_number}
score, answered, question_count, max_questions, question_start_time, time_limit = 0, False, 0, 10, 0, 10

show_instructions_modal()

def next_question():
    global question_text, correct_color_name, color_rgb, option_names, answered, question_count, question_start_time
    question_text, correct_color_name, color_rgb, option_names = generate_question()
    answered = False
    question_count += 1
    question_start_time = pygame.time.get_ticks()

next_question()

while True:
    screen.fill((255, 255, 255))
    font = pygame.font.SysFont(None, 36)
    progress_render = font.render(f"Question {question_count} of {max_questions}", True, (0, 0, 0))
    screen.blit(progress_render, (WIDTH//2 - progress_render.get_width()//2, 30))
    display_color_question(question_text, color_rgb)
    option_positions = draw_name_options(option_names)
    elapsed = (pygame.time.get_ticks() - question_start_time) / 1000
    remaining = max(0, int(time_limit - elapsed))
    font_timer = pygame.font.SysFont(None, 40)
    timer_render = font_timer.render(f"Time left: {remaining}s", True, (200, 0, 0))
    screen.blit(timer_render, (WIDTH - 220, 10))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()
        if event.type == pygame.MOUSEBUTTONDOWN and not answered:
            mouse_pos = pygame.mouse.get_pos()
            chosen_name = get_user_answer(mouse_pos, option_positions, option_names)
            if chosen_name:
                if validate_answer(chosen_name, correct_color_name):
                    point = max(1, int(time_limit - elapsed))
                    score += point
                    show_popup("Correct!", color=(0,180,0))
                    print(f"✅ Correct! Score: {score} (+{point})")
                else:
                    show_popup("Wrong!", color=(200,0,0))
                    print(f"❌ Wrong. Score: {score} (+0)")
                answered = True
                pygame.event.clear()  # Biar tidak delay klik berikutnya
                if question_count < max_questions:
                    next_question()
                else:
                    screen.fill((255,255,255))
                    font_end = pygame.font.SysFont(None, 60)
                    end_render = font_end.render(f"Game Over! Final Score: {score}", True, (0, 0, 0))
                    screen.blit(end_render, (WIDTH//2 - end_render.get_width()//2, HEIGHT//2 - 30))
                    pygame.display.flip()
                    pygame.time.wait(2000)
                    pygame.quit()
                    sys.exit()
    if not answered and elapsed >= time_limit:
        show_popup("Time's Up!", color=(220, 140, 0))
        print(f"⏰ Time's up! Wrong answer. Score: {score} (+0)")
        answered = True
        pygame.event.clear()
        if question_count < max_questions:
            next_question()
        else:
            screen.fill((255,255,255))
            font_end = pygame.font.SysFont(None, 60)
            end_render = font_end.render(f"Game Over! Final Score: {score}", True, (0, 0, 0))
            screen.blit(end_render, (WIDTH//2 - end_render.get_width()//2, HEIGHT//2 - 30))
            pygame.display.flip()
            pygame.time.wait(2000)
            pygame.quit()
            sys.exit()
    keys = pygame.key.get_pressed()
    current_player.move(keys)
    current_player.draw(screen)
    for p in players.values():
        p.move(keys)
        p.draw(screen)
    font_score = pygame.font.SysFont(None, 30)
    score_render = font_score.render(f"Score: {score}", True, (0, 0, 0))
    screen.blit(score_render, (10, 10))
    pygame.display.flip()
    clock.tick(FPS)