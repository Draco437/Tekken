import pygame
import random
import sys

pygame.init()

WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TECH BRAWLERS: LIGHTSABER VERSUS SHOWDOWN")

BLACK = (10, 8, 16)
WHITE = (255, 255, 255)
DARK_GRAY = (24, 22, 34)
NEON_CYAN = (0, 243, 255)
NEON_MAGENTA = (255, 0, 110)
GOLD = (255, 190, 11)
SILVER = (150, 154, 172)
GLASS_OVERLAY = (18, 16, 26)
GRID_LINE_COLOR = (45, 35, 65)
SHIELD_BLUE = (0, 191, 255, 110)
SHIELD_RED = (255, 69, 0, 110)

clock = pygame.time.Clock()
font_sub = pygame.font.SysFont("Arial", 16, bold=True)
font_main = pygame.font.SysFont("Impact", 24)
font_title = pygame.font.SysFont("Impact", 64)
font_splash = pygame.font.SysFont("Impact", 50)

GRAVITY = 1.0
FLOOR_Y = HEIGHT - 90
FRICTION = 0.82

game_over = False
winner_text = ""
camera_shake = 0
game_state = "menu" 
previous_state = "fight" 
intro_timer = 0      
bg_scroll = 0.0

# Name Input State Variables
p1_name_input = ""
p2_name_input = ""
active_player_input = 1  # 1 for P1, 2 for P2

particles = [] 
hit_flashes = [] 

stars = [(random.randint(0, WIDTH), random.randint(0, FLOOR_Y - 120), random.choice([1, 2])) for _ in range(60)]

# NIGHT CITY BUILDINGS GENERATION WITH WINDOWS
WINDOW_COLORS = [
    (255, 230, 120),  # Warm yellow
    (0, 220, 255),    # Cyber cyan
    (255, 180, 80),   # Warm amber
    (200, 220, 255),  # Soft blue/white
    (40, 38, 55)      # Dark / Off window
]

skyscrapers = []
for i in range(16):
    w = random.randint(70, 110)
    h = random.randint(120, 270)
    x = i * 60 + random.randint(-15, 15)
    y = FLOOR_Y - h
    
    windows = []
    win_w, win_h = 4, 5
    gap_x, gap_y = 6, 8
    
    start_x = x + 8
    start_y = y + 12
    
    for wx in range(start_x, x + w - 10, win_w + gap_x):
        for wy in range(start_y, y + h - 15, win_h + gap_y):
            if random.random() < 0.35:
                color = random.choice(WINDOW_COLORS[:-1])
            else:
                color = WINDOW_COLORS[-1]
            windows.append((wx, wy, win_w, win_h, color))
            
    has_antenna = random.random() < 0.4
    antenna_x = x + w // 2
    
    bg_shade = random.randint(18, 28)
    building_color = (bg_shade, bg_shade + 2, bg_shade + 10)
    
    skyscrapers.append({
        'rect': (x, y, w, h),
        'windows': windows,
        'has_antenna': has_antenna,
        'antenna_x': antenna_x,
        'color': building_color
    })

class Fighter:
    def __init__(self, x, y, name, color, saber_color, controls, player_num=1):
        self.name = name
        self.color = color
        self.saber_color = saber_color
        self.controls = controls 
        self.player_num = player_num
        
        self.w, self.h = 46, 88
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.is_jumping = False
        
        self.hp = 100
        self.max_hp = 100
        self.display_hp = 100  
        self.state = "idle" 
        self.state_timer = 0
        self.attack_type = None 
        self.facing = "right"

        self.dash_cooldown = 0

    def update(self, keys, opponent):
        self.facing = "right" if self.x < opponent.x else "left"
        
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        if self.state != "dashing":
            self.vx *= FRICTION

        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer == 0:
                self.state = "idle"
                self.attack_type = None

        if self.state == "blocking" and not keys[self.controls["block"]]:
            self.state = "idle"

        if self.state in ["idle", "jumping", "blocking"]:
            if keys[self.controls["block"]]:
                self.state = "blocking"
                self.vx = 0 
            else:
                if keys[self.controls["left"]]:  self.vx = -7
                if keys[self.controls["right"]]: self.vx = 7
                
                if keys[self.controls["jump"]] and not self.is_jumping:
                    self.vy = -17
                    self.is_jumping = True
                    self.state = "jumping"

        self.x += self.vx
        self.y += self.vy
        
        if self.y < FLOOR_Y - self.h:
            self.vy += GRAVITY
        else:
            self.y = FLOOR_Y - self.h
            self.vy = 0
            self.is_jumping = False
            if self.state == "jumping": self.state = "idle"

        if self.x < 20: self.x = 20
        if self.x > WIDTH - self.w - 20: self.x = WIDTH - self.w - 20

        if self.display_hp > self.hp:
            self.display_hp -= 0.6

    def attack(self, attack_type):
        if self.state in ["idle", "jumping"]:
            self.state = "attacking"
            self.attack_type = attack_type
            self.state_timer = 14
            self.vx = 6 if self.facing == "right" else -6 

    def force_dash(self, keys):
        if self.dash_cooldown == 0 and self.state in ["idle", "jumping"]:
            dash_dir = 0
            if keys[self.controls["left"]]:   dash_dir = -1
            elif keys[self.controls["right"]]: dash_dir = 1
            else: dash_dir = 1 if self.facing == "right" else -1

            self.state = "dashing"
            self.state_timer = 8
            self.vx = dash_dir * 22
            self.dash_cooldown = 45  

            for _ in range(6):
                particles.append([self.x + self.w//2, self.y + self.h//2, random.uniform(-2, 2), random.uniform(-2, 2), self.saber_color, 180, random.randint(4, 7)])

    def draw(self, surface):
        fx = self.x
        fy = self.y
        fw, fh = self.w, self.h
        center_x = fx + fw // 2
        
        if self.player_num == 1:
            armor_main = (0, 210, 255)       # Cyan
            armor_accent = (180, 245, 255)   
            visor_glow = (0, 255, 200)       
            joint_color = (40, 55, 75)       
        else:
            armor_main = (255, 0, 128)       # Magenta/Pink
            armor_accent = (255, 170, 215)   
            visor_glow = (255, 220, 0)       
            joint_color = (65, 35, 55)       

        shadow_w = max(12, fw + 20 - (abs(FLOOR_Y - (fy + fh)) // 3))
        pygame.draw.ellipse(surface, (5, 4, 10), (center_x - shadow_w//2, FLOOR_Y - 4, shadow_w, 8))

        if self.state in ["attacking", "dashing"]:
            aura_surf = pygame.Surface((fw + 30, fh + 30), pygame.SRCALPHA)
            pygame.draw.ellipse(aura_surf, (*self.saber_color, 70), (0, 0, fw + 30, fh + 30))
            surface.blit(aura_surf, (fx - 15, fy - 15))

        # Legs & Boots
        pygame.draw.rect(surface, joint_color, (center_x - 14, fy + 52, 10, 24), border_radius=3)
        pygame.draw.rect(surface, armor_main, (center_x - 16, fy + 72, 12, 14), border_radius=3)
        pygame.draw.rect(surface, WHITE, (center_x - 16, fy + 72, 12, 14), 1, border_radius=3)

        pygame.draw.rect(surface, joint_color, (center_x + 4, fy + 52, 10, 24), border_radius=3)
        pygame.draw.rect(surface, armor_main, (center_x + 4, fy + 72, 12, 14), border_radius=3)
        pygame.draw.rect(surface, WHITE, (center_x + 4, fy + 72, 12, 14), 1, border_radius=3)

        # Chest
        pygame.draw.rect(surface, armor_main, (fx + 4, fy + 22, fw - 8, 32), border_radius=6)
        pygame.draw.rect(surface, WHITE, (fx + 4, fy + 22, fw - 8, 32), 2, border_radius=6)
        
        pygame.draw.rect(surface, armor_accent, (center_x - 10, fy + 26, 20, 24), border_radius=4)
        pygame.draw.circle(surface, WHITE, (center_x, fy + 38), 5)
        pygame.draw.circle(surface, visor_glow, (center_x, fy + 38), 3)

        # Shoulders
        pad_y = fy + 20
        pygame.draw.rect(surface, armor_accent, (fx - 3, pad_y, 12, 14), border_radius=4)
        pygame.draw.rect(surface, WHITE, (fx - 3, pad_y, 12, 14), 1, border_radius=4)
        
        pygame.draw.rect(surface, armor_accent, (fx + fw - 9, pad_y, 12, 14), border_radius=4)
        pygame.draw.rect(surface, WHITE, (fx + fw - 9, pad_y, 12, 14), 1, border_radius=4)

        # Helmet
        helmet_rect = pygame.Rect(center_x - 14, fy + 2, 28, 22)
        pygame.draw.rect(surface, joint_color, helmet_rect, border_radius=8)
        pygame.draw.rect(surface, armor_accent, helmet_rect, 2, border_radius=8)

        # Visor
        if self.facing == "right":
            visor_rect = (center_x - 2, fy + 8, 14, 6)
        else:
            visor_rect = (center_x - 12, fy + 8, 14, 6)
            
        pygame.draw.rect(surface, visor_glow, visor_rect, border_radius=3)
        pygame.draw.rect(surface, WHITE, visor_rect, 1, border_radius=3)

        # Lightsaber
        saber_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s_length = 52
        
        if self.state == "attacking":
            if self.attack_type == "high":
                ex = fx + fw + s_length if self.facing == "right" else fx - s_length
                ey = fy - 18
            elif self.attack_type == "mid":
                ex = fx + fw + s_length if self.facing == "right" else fx - s_length
                ey = fy + 32
            else: 
                ex = fx + fw + s_length if self.facing == "right" else fx - s_length
                ey = fy + fh - 2
            origin = (center_x, fy + 34)
        else:
            ex = fx + fw + 10 if self.facing == "right" else fx - 10
            ey = fy - 2
            origin = (ex, fy + 42)

        pygame.draw.line(surface, SILVER, origin, (origin[0] + (4 if self.facing=="right" else -4), origin[1] - 8), 4)

        pygame.draw.line(saber_surface, (*self.saber_color, 80), origin, (ex, ey), 12)
        pygame.draw.line(saber_surface, (*self.saber_color, 180), origin, (ex, ey), 6)
        pygame.draw.line(saber_surface, WHITE, origin, (ex, ey), 2)
        surface.blit(saber_surface, (0, 0))

        if self.state == "blocking":
            shield_surf = pygame.Surface((fw + 40, fh + 30), pygame.SRCALPHA)
            color_mask = SHIELD_BLUE if self.player_num == 1 else SHIELD_RED
            pygame.draw.ellipse(shield_surf, color_mask, (0, 0, fw + 40, fh + 20))
            pygame.draw.ellipse(shield_surf, WHITE, (0, 0, fw + 40, fh + 20), 2)
            surface.blit(shield_surf, (fx - 20, fy - 10))


def process_combat_collisions(p1, p2):
    global camera_shake
    if p1.state == "attacking" and p1.state_timer == 11:
        reach = 75
        hx = p1.x + p1.w if p1.facing == "right" else p1.x - reach
        
        if p1.attack_type == "high": hy = p1.y - 15
        elif p1.attack_type == "mid": hy = p1.y + 20
        else: hy = p1.y + 50

        if pygame.Rect(hx, hy, reach, 32).colliderect(pygame.Rect(p2.x, p2.y, p2.w, p2.h)):
            if p2.state == "blocking":
                p2.vx = 4 if p1.facing == "right" else -4  
                camera_shake = 3
                for _ in range(4):
                    particles.append([p2.x + p2.w//2, p2.y + p2.h//2, random.uniform(-4, 4), random.uniform(-4, 4), (255, 255, 255), 200, 3])
            else:
                dmg = 15 if p1.attack_type == "mid" else 10
                p2.hp -= dmg
                p2.state = "hit"
                p2.state_timer = 10
                p2.vx = 10 if p1.facing == "right" else -10
                camera_shake = 14 

                hit_flashes.append([hx + reach//2, hy + 16, 12, 8])

                for _ in range(12):
                    particles.append([p2.x + p2.w//2, p2.y + p2.h//2, random.uniform(-6, 6), random.uniform(-9, -2), p1.saber_color, 255, random.randint(3, 5)])

def draw_cyber_background(surface):
    for y in range(0, FLOOR_Y):
        color_val = max(8, 32 - int(y * 0.07))
        pygame.draw.line(surface, (12, 10, color_val), (0, y), (WIDTH, y))

    for star in stars:
        pygame.draw.circle(surface, (160, 180, 220), (star[0], star[1]), star[2])

    for s in skyscrapers:
        x, y, w, h = s['rect']
        pygame.draw.rect(surface, s['color'], (x, y, w, h))
        pygame.draw.rect(surface, (35, 35, 55), (x, y, w, h), 1)
        pygame.draw.line(surface, (60, 70, 110), (x, y), (x + w, y), 2)

        if s['has_antenna']:
            ax = s['antenna_x']
            pygame.draw.line(surface, (80, 80, 100), (ax, y), (ax, y - 18), 1)
            pygame.draw.circle(surface, (255, 40, 40), (ax, y - 18), 2)

        for wx, wy, ww, wh, color in s['windows']:
            pygame.draw.rect(surface, color, (wx, wy, ww, wh))

    pygame.draw.rect(surface, DARK_GRAY, (0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))

    num_lines = 16
    for i in range(num_lines + 1):
        x_start = int((WIDTH / num_lines) * i)
        x_end = int((WIDTH / 2) + (x_start - WIDTH / 2) * 1.5)
        pygame.draw.line(surface, GRID_LINE_COLOR, (x_start, FLOOR_Y), (x_end, HEIGHT), 1)

    global bg_scroll
    if game_state != "paused":
        bg_scroll = (bg_scroll + 0.8) % 30
    curr_y = FLOOR_Y + int(bg_scroll)
    while curr_y < HEIGHT:
        pygame.draw.line(surface, GRID_LINE_COLOR, (0, curr_y), (WIDTH, curr_y), 1)
        curr_y += 25

    pygame.draw.line(surface, GOLD, (0, FLOOR_Y), (WIDTH, FLOOR_Y), 2)


def reset_match():
    global p1, p2, game_over, winner_text
    p1_binds = {"left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w, "block": pygame.K_s}
    p2_binds = {"left": pygame.K_LEFT, "right": pygame.K_RIGHT, "jump": pygame.K_UP, "block": pygame.K_DOWN}
    
    name_1 = p1_name_input.strip().upper() if p1_name_input.strip() else "PLAYER 1"
    name_2 = p2_name_input.strip().upper() if p2_name_input.strip() else "PLAYER 2"

    p1 = Fighter(180, FLOOR_Y - 88, name_1, NEON_CYAN, NEON_CYAN, p1_binds, player_num=1)
    p2 = Fighter(WIDTH - 222, FLOOR_Y - 88, name_2, NEON_MAGENTA, NEON_MAGENTA, p2_binds, player_num=2)
    game_over = False
    winner_text = ""

reset_match()
start_btn = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 50, 240, 46)

resume_btn = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 - 60, 240, 42)
restart_btn = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 - 5, 240, 42)
home_btn = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 50, 240, 42)

while True:
    clock.tick(60)
    
    render_offset_x = random.randint(-camera_shake, camera_shake) if camera_shake > 0 else 0
    render_offset_y = random.randint(-camera_shake, camera_shake) if camera_shake > 0 else 0
    if camera_shake > 0 and game_state != "paused": camera_shake -= 1

    display_surface = pygame.Surface((WIDTH, HEIGHT))
    draw_cyber_background(display_surface)

    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == "menu" and event.button == 1 and start_btn.collidepoint(mouse_pos):
                game_state = "name_input"
                active_player_input = 1
                p1_name_input = ""
                p2_name_input = ""
            
            elif game_state == "paused" and event.button == 1:
                if resume_btn.collidepoint(mouse_pos):
                    game_state = previous_state
                elif restart_btn.collidepoint(mouse_pos):
                    reset_match()
                    game_state = "level_intro"
                    intro_timer = 90
                elif home_btn.collidepoint(mouse_pos):
                    reset_match()
                    game_state = "menu"

        # Text input handling for Name Input Phase
        if event.type == pygame.KEYDOWN:
            if game_state == "name_input":
                if event.key == pygame.K_RETURN:
                    if active_player_input == 1:
                        active_player_input = 2
                    elif active_player_input == 2:
                        reset_match()
                        game_state = "level_intro"
                        intro_timer = 90
                elif event.key == pygame.K_BACKSPACE:
                    if active_player_input == 1:
                        p1_name_input = p1_name_input[:-1]
                    else:
                        p2_name_input = p2_name_input[:-1]
                else:
                    if len(event.unicode) > 0 and event.unicode.isprintable():
                        if active_player_input == 1 and len(p1_name_input) < 12:
                            p1_name_input += event.unicode
                        elif active_player_input == 2 and len(p2_name_input) < 12:
                            p2_name_input += event.unicode

            # Pause Toggle
            if event.key in [pygame.K_p, pygame.K_ESCAPE]:
                if game_state in ["fight", "level_intro"]:
                    previous_state = game_state
                    game_state = "paused"
                elif game_state == "paused":
                    game_state = previous_state

            if game_state == "fight" and not game_over:
                if event.key == pygame.K_f: p1.attack("high")
                if event.key == pygame.K_g: p1.attack("mid")
                if event.key == pygame.K_v: p1.attack("low")
                if event.key == pygame.K_LSHIFT: p1.force_dash(pygame.key.get_pressed())

                if event.key == pygame.K_i: p2.attack("high")
                if event.key == pygame.K_o: p2.attack("mid")
                if event.key == pygame.K_k: p2.attack("low")
                if event.key == pygame.K_RCTRL:  p2.force_dash(pygame.key.get_pressed())

            if event.key == pygame.K_r and game_over:
                reset_match()
                game_state = "level_intro"
                intro_timer = 90

            if event.key == pygame.K_q and game_over:
                reset_match()
                game_state = "menu"

    # 1. START MENU SCREEN 
    if game_state == "menu":
        menu_mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        menu_mask.fill((10, 8, 16, 180))
        display_surface.blit(menu_mask, (0,0))

        title_obj = font_title.render("LIGHTSABER DUEL", True, WHITE)
        sub_obj = font_sub.render("LOCAL 2-PLAYER VERSUS ARENA MODE", True, SILVER)
        display_surface.blit(title_obj, (WIDTH // 2 - title_obj.get_width() // 2, HEIGHT // 2 - 110))
        display_surface.blit(sub_obj, (WIDTH // 2 - sub_obj.get_width() // 2, HEIGHT // 2 - 40))

        is_hover = start_btn.collidepoint(mouse_pos)
        pygame.draw.rect(display_surface, GOLD if is_hover else GLASS_OVERLAY, start_btn, border_radius=4)
        pygame.draw.rect(display_surface, WHITE if is_hover else GOLD, start_btn, 1, border_radius=4)
        
        btn_txt = font_sub.render("ENTER THE ARENA", True, WHITE)
        display_surface.blit(btn_txt, (start_btn.x + (start_btn.width//2 - btn_txt.get_width()//2), start_btn.y + (start_btn.height//2 - btn_txt.get_height()//2)))

    # 2. PLAYER NAME INPUT PHASE SCREEN
    elif game_state == "name_input":
        input_mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        input_mask.fill((10, 8, 16, 210))
        display_surface.blit(input_mask, (0,0))

        prompt_title = font_splash.render("ENTER COMBATANT NAMES", True, GOLD)
        display_surface.blit(prompt_title, (WIDTH // 2 - prompt_title.get_width() // 2, 50))

        # P1 Box
        p1_box = pygame.Rect(WIDTH // 2 - 220, 150, 440, 50)
        p1_border = NEON_CYAN if active_player_input == 1 else (60, 70, 90)
        pygame.draw.rect(display_surface, GLASS_OVERLAY, p1_box, border_radius=6)
        pygame.draw.rect(display_surface, p1_border, p1_box, 2, border_radius=6)
        
        p1_lbl = font_sub.render("PLAYER 1:", True, NEON_CYAN)
        p1_txt = font_main.render(p1_name_input + ("|" if active_player_input == 1 else ""), True, WHITE)
        display_surface.blit(p1_lbl, (p1_box.x - 100, p1_box.y + 14))
        display_surface.blit(p1_txt, (p1_box.x + 15, p1_box.y + 10))

        # P2 Box
        p2_box = pygame.Rect(WIDTH // 2 - 220, 240, 440, 50)
        p2_border = NEON_MAGENTA if active_player_input == 2 else (60, 70, 90)
        pygame.draw.rect(display_surface, GLASS_OVERLAY, p2_box, border_radius=6)
        pygame.draw.rect(display_surface, p2_border, p2_box, 2, border_radius=6)

        p2_lbl = font_sub.render("PLAYER 2:", True, NEON_MAGENTA)
        p2_txt = font_main.render(p2_name_input + ("|" if active_player_input == 2 else ""), True, WHITE)
        display_surface.blit(p2_lbl, (p2_box.x - 100, p2_box.y + 14))
        display_surface.blit(p2_txt, (p2_box.x + 15, p2_box.y + 10))

        hint_txt = font_sub.render("TYPE YOUR NAME AND PRESS ENTER TO CONFIRM", True, SILVER)
        display_surface.blit(hint_txt, (WIDTH // 2 - hint_txt.get_width() // 2, 340))

    # 3. LEVEL INTRO SPLASH
    elif game_state == "level_intro":
        intro_mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        intro_mask.fill((10, 8, 16, 120))
        display_surface.blit(intro_mask, (0,0))

        match_txt = font_splash.render("PREPARE YOURSELF", True, WHITE)
        objective_txt = font_main.render(f"{p1.name}  VS  {p2.name}", True, GOLD)
        
        display_surface.blit(match_txt, (WIDTH // 2 - match_txt.get_width() // 2, HEIGHT // 2 - 60))
        display_surface.blit(objective_txt, (WIDTH // 2 - objective_txt.get_width() // 2, HEIGHT // 2 + 5))
        
        intro_timer -= 1
        if intro_timer <= 0:
            game_state = "fight"

    # 4. ACTIVE FIGHT SIMULATION LAYER & HIGHLIGHTED HUD
    elif game_state in ["fight", "paused"]:
        if game_state == "fight" and not game_over:
            keys = pygame.key.get_pressed()
            p1.update(keys, p2)
            p2.update(keys, p1)

            process_combat_collisions(p1, p2)
            process_combat_collisions(p2, p1)

            if p1.hp <= 0:
                p1.hp = 0
                game_over = True
                winner_text = f"{p2.name} VICTORIOUS! DOMINATOR MATCH COMPLETE"
            elif p2.hp <= 0:
                p2.hp = 0
                game_over = True
                winner_text = f"{p1.name} VICTORIOUS! DOMINATOR MATCH COMPLETE"

        p1.draw(display_surface)
        p2.draw(display_surface)

        if game_state == "fight":
            for part in particles[:]:
                part[0] += part[2]; part[1] += part[3]; part[3] += 0.4; part[5] -= 6
                if part[5] <= 0: particles.remove(part)
                else:
                    p_surf = pygame.Surface((part[6]*2, part[6]*2), pygame.SRCALPHA)
                    pygame.draw.circle(p_surf, (*part[4], part[5]), (part[6], part[6]), part[6])
                    display_surface.blit(p_surf, (part[0] - part[6], part[1] - part[6]))

            for flash in hit_flashes[:]:
                flash[2] += 6; flash[3] -= 1
                pygame.draw.circle(display_surface, (255, 255, 255, 100), (flash[0], flash[1]), flash[2], 2)
                if flash[3] <= 0: hit_flashes.remove(flash)

        # Player 1 HUD Block
        bar_x1, bar_y, bar_w, bar_h = 40, 30, 340, 26
        
        pygame.draw.rect(display_surface, (0, 100, 140), (bar_x1 - 4, bar_y - 4, bar_w + 8, bar_h + 8), border_radius=6)
        pygame.draw.rect(display_surface, NEON_CYAN, (bar_x1 - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2, border_radius=5)
        pygame.draw.rect(display_surface, BLACK, (bar_x1, bar_y, bar_w, bar_h), border_radius=4)
        
        if p1.display_hp > 0: 
            pygame.draw.rect(display_surface, (255, 255, 255), (bar_x1, bar_y, int(bar_w * (p1.display_hp / 100)), bar_h), border_radius=4)
        if p1.hp > 0:
            pygame.draw.rect(display_surface, NEON_CYAN, (bar_x1, bar_y, int(bar_w * (p1.hp / 100)), bar_h), border_radius=4)
        
        pygame.draw.line(display_surface, (200, 255, 255), (bar_x1, bar_y + 2), (bar_x1 + bar_w, bar_y + 2), 1)

        p1_name_surf = font_main.render(p1.name, True, WHITE)
        display_surface.blit(p1_name_surf, (bar_x1, bar_y + 32))
        pygame.draw.rect(display_surface, NEON_CYAN, (bar_x1, bar_y + 60, p1_name_surf.get_width(), 3))
        
        cd_w_1 = int(70 * (p1.dash_cooldown / 45))
        if cd_w_1 > 0: pygame.draw.rect(display_surface, GOLD, (bar_x1, bar_y + 68, cd_w_1, 4))

        # Player 2 HUD Block
        bar_x2 = WIDTH - 380
        
        pygame.draw.rect(display_surface, (140, 0, 70), (bar_x2 - 4, bar_y - 4, bar_w + 8, bar_h + 8), border_radius=6)
        pygame.draw.rect(display_surface, NEON_MAGENTA, (bar_x2 - 2, bar_y - 2, bar_w + 4, bar_h + 4), 2, border_radius=5)
        pygame.draw.rect(display_surface, BLACK, (bar_x2, bar_y, bar_w, bar_h), border_radius=4)
        
        if p2.display_hp > 0: 
            pygame.draw.rect(display_surface, (255, 255, 255), (bar_x2, bar_y, int(bar_w * (p2.display_hp / 100)), bar_h), border_radius=4)
        if p2.hp > 0:
            pygame.draw.rect(display_surface, NEON_MAGENTA, (bar_x2, bar_y, int(bar_w * (p2.hp / 100)), bar_h), border_radius=4)

        pygame.draw.line(display_surface, (255, 200, 230), (bar_x2, bar_y + 2), (bar_x2 + bar_w, bar_y + 2), 1)

        p2_name_surf = font_main.render(p2.name, True, WHITE)
        display_surface.blit(p2_name_surf, (bar_x2 + bar_w - p2_name_surf.get_width(), bar_y + 32))
        pygame.draw.rect(display_surface, NEON_MAGENTA, (bar_x2 + bar_w - p2_name_surf.get_width(), bar_y + 60, p2_name_surf.get_width(), 3))

        cd_w_2 = int(70 * (p2.dash_cooldown / 45))
        if cd_w_2 > 0: pygame.draw.rect(display_surface, GOLD, (bar_x2 + bar_w - cd_w_2, bar_y + 68, cd_w_2, 4))

        # Center VS Badge
        vs_obj = font_main.render("VS", True, GOLD)
        display_surface.blit(vs_obj, (WIDTH // 2 - vs_obj.get_width() // 2, 28))

        # PAUSE OVERLAY
        if game_state == "paused":
            pause_mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pause_mask.fill((10, 8, 16, 200))
            display_surface.blit(pause_mask, (0, 0))

            p_title = font_splash.render("GAME PAUSED", True, WHITE)
            display_surface.blit(p_title, (WIDTH // 2 - p_title.get_width() // 2, HEIGHT // 2 - 130))

            h1 = resume_btn.collidepoint(mouse_pos)
            pygame.draw.rect(display_surface, GOLD if h1 else GLASS_OVERLAY, resume_btn, border_radius=4)
            pygame.draw.rect(display_surface, WHITE if h1 else GOLD, resume_btn, 1, border_radius=4)
            t1 = font_sub.render("RESUME COMBAT", True, WHITE)
            display_surface.blit(t1, (resume_btn.x + (resume_btn.width//2 - t1.get_width()//2), resume_btn.y + (resume_btn.height//2 - t1.get_height()//2)))

            h2 = restart_btn.collidepoint(mouse_pos)
            pygame.draw.rect(display_surface, GOLD if h2 else GLASS_OVERLAY, restart_btn, border_radius=4)
            pygame.draw.rect(display_surface, WHITE if h2 else GOLD, restart_btn, 1, border_radius=4)
            t2 = font_sub.render("RESTART MATCH", True, WHITE)
            display_surface.blit(t2, (restart_btn.x + (restart_btn.width//2 - t2.get_width()//2), restart_btn.y + (restart_btn.height//2 - t2.get_height()//2)))

            h3 = home_btn.collidepoint(mouse_pos)
            pygame.draw.rect(display_surface, GOLD if h3 else GLASS_OVERLAY, home_btn, border_radius=4)
            pygame.draw.rect(display_surface, WHITE if h3 else GOLD, home_btn, 1, border_radius=4)
            t3 = font_sub.render("RETURN TO MAIN LOBBY", True, WHITE)
            display_surface.blit(t3, (home_btn.x + (home_btn.width//2 - t3.get_width()//2), home_btn.y + (home_btn.height//2 - t3.get_height()//2)))

    # 5. GAME OVER OVERLAY
    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(210)
        display_surface.blit(overlay, (0, 0))

        win_obj = font_main.render(winner_text, True, GOLD)
        res_obj = font_sub.render("PRESS 'R' TO REMATCH BATTLE  |  PRESS 'Q' TO QUIT TO MAIN LOBBY SCREEN", True, SILVER)
        
        display_surface.blit(win_obj, (WIDTH // 2 - win_obj.get_width() // 2, HEIGHT // 2 - 35))
        display_surface.blit(res_obj, (WIDTH // 2 - res_obj.get_width() // 2, HEIGHT // 2 + 15))

    screen.blit(display_surface, (render_offset_x, render_offset_y))
    pygame.display.flip()