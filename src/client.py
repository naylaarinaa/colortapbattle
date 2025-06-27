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
    def __init__(self, player_id):
        self.player_id = player_id
        self.server_url = 'http://127.0.0.1:8080'

    def get_question(self):
        try:
            response = requests.get(f"{self.server_url}/question")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

    def send_answer(self, question_id, answer):
        payload = {'player_id': self.player_id, 'question_id': question_id, 'answer': answer}
        try:
            response = requests.post(f"{self.server_url}/answer", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None

player_id = input("Masukkan ID pemain Anda: ")
client = ClientInterface(player_id)
score, answered, question_count = 0, False, 0
max_questions, time_limit = 10, 10
question_start_time = 0
current_question = {} 

show_instructions_modal()

def get_next_question():
    global current_question, answered, question_count, question_start_time
    new_question = client.get_question()
    if new_question:
        current_question = new_question
        answered = False
        question_count += 1
        question_start_time = pygame.time.get_ticks()
    else:
        print("Koneksi ke server gagal. Game akan ditutup.")
        pygame.quit()
        sys.exit()

get_next_question()

while True:
    screen.fill((255, 255, 255))
    
    font = pygame.font.SysFont(None, 36)
    progress_render = font.render(f"Question {question_count} of {max_questions}", True, (0, 0, 0))
    screen.blit(progress_render, (WIDTH // 2 - progress_render.get_width() // 2, 30))

    if current_question:
        display_color_question(current_question.get('text'), current_question.get('text_color'))
        option_positions = draw_name_options(current_question.get('options', []))
    
    elapsed = (pygame.time.get_ticks() - question_start_time) / 1000
    remaining = max(0, int(time_limit - elapsed))
    font_timer = pygame.font.SysFont(None, 40)
    timer_render = font_timer.render(f"Time left: {remaining}s", True, (200, 0, 0))
    screen.blit(timer_render, (WIDTH - 220, 10))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        if event.type == pygame.MOUSEBUTTONDOWN and not answered and current_question:
            mouse_pos = pygame.mouse.get_pos()
            chosen_name = get_user_answer(mouse_pos, option_positions, current_question.get('options', []))
            
            if chosen_name:
                answered = True
                result = client.send_answer(current_question.get('question_id'), chosen_name)
                
                if result and result.get('correct'):
                    score = result.get('new_score', score)
                    show_popup("Correct!", color=(0, 180, 0))
                elif result:
                    show_popup("Wrong!", color=(200, 0, 0))
                else:
                    show_popup("No Response", color=(100, 100, 100))

                pygame.event.clear()
                if question_count < max_questions:
                    get_next_question()

    if not answered and elapsed >= time_limit:
        show_popup("Time's Up!", color=(220, 140, 0))
        answered = True
        pygame.event.clear()
        if question_count < max_questions:
            get_next_question()
            
    if question_count >= max_questions and answered:
        screen.fill((255, 255, 255))
        font_end = pygame.font.SysFont(None, 60)
        end_render = font_end.render(f"Game Over! Final Score: {score}", True, (0, 0, 0))
        screen.blit(end_render, (WIDTH // 2 - end_render.get_width() // 2, HEIGHT // 2 - 30))
        pygame.display.flip()
        pygame.time.wait(3000)
        pygame.quit()
        sys.exit()
    
    font_score = pygame.font.SysFont(None, 30)
    score_render = font_score.render(f"Score: {score}", True, (0, 0, 0))
    screen.blit(score_render, (10, 10))

    pygame.display.flip()
    clock.tick(FPS)