import pygame
import random
import sys
import asyncio
import threading
import os
import time
import math
import edge_tts

# Initialize Pygame and Mixer
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Display Config
WIDTH, HEIGHT = 960, 540
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TEKKEN BRAWL: OGRE VS PRINCESS")

# Color Palette
BLACK = (10, 8, 16)
WHITE = (255, 255, 255)
DARK_BG = (14, 12, 22)
DARK_PANEL = (22, 20, 34)
BORDER_COLOR = (45, 40, 65)

# Player Colors & Neons
OGRE_GREEN = (0, 240, 120)
OGRE_DARK = (0, 140, 70)
PRINCESS_PINK = (255, 40, 140)
PRINCESS_DARK = (160, 10, 80)
GOLD = (255, 210, 30)
GOLD_DARK = (180, 140, 10)
SILVER = (180, 185, 200)
CYAN_ACCENT = (0, 230, 255)
RED_DAMAGE = (255, 50, 50)
SUPER_ORANGE = (255, 140, 0)

clock = pygame.time.Clock()

# Fonts
font_small = pygame.font.SysFont("Arial", 14, bold=True)
font_sub = pygame.font.SysFont("Arial", 17, bold=True)
font_hud = pygame.font.SysFont("Impact", 22)
font_timer = pygame.font.SysFont("Impact", 36)
font_title = pygame.font.SysFont("Impact", 68)
font_banner = pygame.font.SysFont("Impact", 54)
font_combo = pygame.font.SysFont("Impact", 28)

GRAVITY = 0.85
FLOOR_Y = HEIGHT - 130
FRICTION = 0.80

# Audio Temp Directory Setup
AUDIO_DIR = "temp_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Load Arena Background
bg_image = None
for bg_filename in ["Back.png", "background.png", "background.jpg"]:
    if os.path.exists(bg_filename):
        try:
            raw_bg = pygame.image.load(bg_filename).convert()
            bg_image = pygame.transform.scale(raw_bg, (WIDTH, HEIGHT))
            break
        except Exception as e:
            print(f"Failed to load {bg_filename}: {e}")

# Load Background Music
try:
    if os.path.exists("sounds/bg_music_new.mp3"):
        pygame.mixer.music.load("sounds/bg_music_new.mp3")
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
except Exception as e:
    print("Could not load background music:", e)

# -------------------------------------------------------------
# EDGE-TTS NEURAL ANNOUNCER ENGINE
# -------------------------------------------------------------
VOICE = "en-US-ChristopherNeural"

def speak_announcer_async(text, duck_volume=True):
    """Generates non-blocking Edge-TTS announcer voice lines."""
    def run_worker():
        filename = os.path.join(AUDIO_DIR, f"tts_{int(time.time() * 1000)}_{random.randint(100, 999)}.mp3")
        
        async def generate():
            try:
                communicate = edge_tts.Communicate(text, VOICE)
                await communicate.save(filename)
                return True
            except Exception as ex:
                return False

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(generate())
            loop.close()

            if success and os.path.exists(filename):
                if duck_volume and pygame.mixer.music.get_busy():
                    pygame.mixer.music.set_volume(0.12)
                
                speech_sound = pygame.mixer.Sound(filename)
                speech_sound.set_volume(1.0)
                channel = pygame.mixer.Channel(1)
                channel.play(speech_sound)

                # Wait until audio finishes to restore background music volume
                while channel.get_busy():
                    time.sleep(0.1)

                if duck_volume:
                    pygame.mixer.music.set_volume(0.35)

                try:
                    os.remove(filename)
                except Exception:
                    pass
        except Exception as err:
            print(f"[Announcer TTS Error]: {err}")

    threading.Thread(target=run_worker, daemon=True).start()


# -------------------------------------------------------------
# SPRITE LOADER WITH ASPECT-PRESERVED SCALING
# -------------------------------------------------------------
def load_scaled_sprite(path, target_height):
    """Loads an image, preserves aspect ratio to target_height, and prepares flipped version."""
    try:
        raw = pygame.image.load(path).convert_alpha()
        w, h = raw.get_size()
        scale_ratio = target_height / max(1, h)
        target_w = max(1, int(w * scale_ratio))
        scaled_r = pygame.transform.smoothscale(raw, (target_w, target_height))
        scaled_l = pygame.transform.flip(scaled_r, True, False)
        return scaled_r, scaled_l
    except Exception as e:
        # Fallback surface
        w, h = int(target_height * 0.6), target_height
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((120, 120, 120, 180))
        return surf, surf


def load_character_animations(base_dirs, target_height):
    """
    Loads animations from Front and Back sets.
    State keys: idle, walk, attacking, jumping, blocking, hit, defeated, super
    """
    states_files = {
        "idle": ["I1.png", "I2.png"],
        "attacking": ["A1.png", "A2.png", "A3.png"],
        "jumping": ["J1.png", "J2.png", "J3.png"],
        "blocking": ["B1.png"],
        "hit": ["Da1.png"],
        "defeated": ["D1.png"],
        "super": ["A1.png", "A2.png", "A3.png"]
    }

    # Resolve existing base directory
    chosen_dir = None
    for d in base_dirs:
        if os.path.exists(d):
            chosen_dir = d
            break

    anims = {}
    for state, filenames in states_files.items():
        front_frames_r = []
        front_frames_l = []
        back_frames_r = []
        back_frames_l = []

        for fname in filenames:
            # Try Front
            front_path = os.path.join(chosen_dir, "Front", fname) if chosen_dir else ""
            if not os.path.exists(front_path) and chosen_dir:
                front_path = os.path.join(chosen_dir, fname)
            
            # Try Back
            back_path = os.path.join(chosen_dir, "Back", fname) if chosen_dir else ""
            if not os.path.exists(back_path) and chosen_dir:
                back_path = os.path.join(chosen_dir, "New folder", fname)
            if not os.path.exists(back_path):
                back_path = front_path

            fr_r, fr_l = load_scaled_sprite(front_path, target_height)
            bk_r, bk_l = load_scaled_sprite(back_path, target_height)

            front_frames_r.append(fr_r)
            front_frames_l.append(fr_l)
            back_frames_r.append(bk_r)
            back_frames_l.append(bk_l)

        anims[state] = {
            "front_right": front_frames_r,
            "front_left": front_frames_l,
            "back_right": back_frames_r,
            "back_left": back_frames_l
        }

    return anims


# -------------------------------------------------------------
# FIGHTER CLASS
# -------------------------------------------------------------
class Fighter:
    def __init__(self, x, name, char_type, primary_color, secondary_color, controls, target_h=150, player_num=1):
        self.char_type = char_type  # "ogre" or "princess"
        self.name = name
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.controls = controls
        self.player_num = player_num
        self.target_h = target_h
        
        # Logical Push Box (body collision separate from sprite bounds)
        self.push_w = 52 if char_type == "princess" else 60
        self.push_h = target_h
        self.x = x
        self.y = FLOOR_Y - self.push_h
        self.vx = 0
        self.vy = 0
        self.is_jumping = False
        
        # Combat Stats
        self.max_hp = 100
        self.hp = 100
        self.display_hp = 100
        self.super_meter = 0
        self.max_super = 100
        self.rounds_won = 0
        
        self.state = "idle"  # idle, walk, attacking, jumping, blocking, hit, defeated, dashing, super
        self.state_timer = 0
        self.combo_count = 0
        self.combo_timer = 0
        self.facing = "right" if player_num == 1 else "left"
        self.dash_cooldown = 0
        self.has_hit_target = False
        
        # Animation
        self.anim_frame = 0.0
        self.anim_speed = 0.09

        # Load Animation Assets
        asset_folders = ["Images1", "Ogre"] if char_type == "ogre" else ["Images2", "Princess"]
        self.animations = load_character_animations(asset_folders, self.target_h)

    @property
    def center_x(self):
        return self.x + self.push_w / 2

    def reset_for_round(self, x_pos):
        self.x = x_pos
        self.y = FLOOR_Y - self.push_h
        self.vx = 0
        self.vy = 0
        self.hp = self.max_hp
        self.display_hp = self.max_hp
        self.state = "idle"
        self.state_timer = 0
        self.is_jumping = False
        self.dash_cooldown = 0
        self.has_hit_target = False
        self.anim_frame = 0.0
        self.facing = "right" if self.player_num == 1 else "left"

    def update(self, keys, opponent):
        # 1. Stable Facing Direction (with 12px dead zone threshold)
        center_diff = opponent.center_x - self.center_x
        if abs(center_diff) > 12:
            if self.state not in ["dashing", "super"]:
                self.facing = "right" if center_diff > 0 else "left"

        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1

        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo_count = 0

        # Natural friction (lighter in mid-air for natural jump arc)
        if self.state != "dashing":
            self.vx *= 0.94 if self.is_jumping else FRICTION

        # 2. State Timers
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer == 0:
                if self.state in ["attacking", "hit", "dashing", "super"]:
                    self.state = "idle"
                    self.anim_frame = 0
                    self.has_hit_target = False

        # 3. Read Player Controls
        is_left = bool(keys[self.controls["left"]])
        is_right = bool(keys[self.controls["right"]])
        is_jump = bool(keys[self.controls["jump"]])
        is_block = bool(keys[self.controls["block"]])

        # 4. Guard Logic
        if self.state == "blocking":
            if not is_block:
                self.state = "idle"
                self.anim_frame = 0

        # 5. Movement and Jump Input Handling
        if self.state in ["idle", "walk", "jumping", "blocking"]:
            if is_block and not self.is_jumping:
                if self.state != "blocking":
                    self.anim_frame = 0
                self.state = "blocking"
                self.vx *= 0.82
            else:
                speed = 6.0 if self.char_type == "princess" else 5.4

                # Simultaneous opposite inputs
                if is_left and is_right:
                    self.vx = 0
                elif is_left:
                    self.vx = -speed
                elif is_right:
                    self.vx = speed

                if is_jump and not self.is_jumping:
                    self.vy = -16.5
                    self.is_jumping = True
                    self.state = "jumping"
                    self.anim_frame = 0

        # 6. Walk vs Idle State Transition
        if not self.is_jumping and self.state in ["idle", "walk"]:
            if abs(self.vx) > 0.8:
                if self.state != "walk":
                    self.state = "walk"
                    self.anim_speed = 0.16
            else:
                if self.state != "idle":
                    self.state = "idle"
                    self.anim_frame = 0
                    self.anim_speed = 0.09

        # 7. Gravity & Floor Boundary
        self.x += self.vx
        self.y += self.vy

        if self.y < FLOOR_Y - self.push_h:
            self.vy += GRAVITY
        else:
            self.y = FLOOR_Y - self.push_h
            self.vy = 0
            self.is_jumping = False
            if self.state == "jumping":
                self.state = "walk" if abs(self.vx) > 0.8 else "idle"
                self.anim_frame = 0

        # 8. Arena Wall Clamp
        min_x = 30
        max_x = WIDTH - 30 - self.push_w
        if self.x < min_x:
            self.x = min_x
        if self.x > max_x:
            self.x = max_x

        # 9. Smooth Health Bar Lag
        if self.display_hp > self.hp:
            self.display_hp -= 0.6
            if self.display_hp < self.hp:
                self.display_hp = self.hp

        self.anim_frame += self.anim_speed

    def attack(self):
        if self.state in ["idle", "walk", "jumping"]:
            self.state = "attacking"
            self.state_timer = 26
            self.anim_frame = 0
            self.has_hit_target = False
            lunge = 6 if self.char_type == "princess" else 7
            self.vx = lunge if self.facing == "right" else -lunge

    def super_attack(self):
        if self.super_meter >= self.max_super and self.state in ["idle", "walk", "jumping"]:
            self.super_meter = 0
            self.state = "super"
            self.state_timer = 36
            self.anim_frame = 0
            self.has_hit_target = False
            self.vx = 14 if self.facing == "right" else -14
            return True
        return False

    def dash(self, keys, particles_list):
        if self.dash_cooldown == 0 and self.state in ["idle", "walk", "jumping"]:
            dir = 0
            is_left = bool(keys[self.controls["left"]])
            is_right = bool(keys[self.controls["right"]])

            if is_left and not is_right:
                dir = -1
            elif is_right and not is_left:
                dir = 1
            else:
                dir = 1 if self.facing == "right" else -1

            self.state = "dashing"
            self.state_timer = 12
            self.anim_frame = 0
            self.vx = dir * 21
            self.dash_cooldown = 45

            # Spawn Dash Energy Ghost Trail
            for _ in range(10):
                particles_list.append([
                    self.center_x + random.uniform(-10, 10),
                    self.y + self.push_h // 2 + random.uniform(-20, 20),
                    random.uniform(-3, 3),
                    random.uniform(-2, 2),
                    self.primary_color,
                    220,
                    random.randint(5, 8)
                ])

    def draw(self, surface):
        center_x = self.center_x
        floor_ground = FLOOR_Y

        # 1. Ground Shadow (dynamic sizing based on altitude)
        altitude = max(0, floor_ground - (self.y + self.push_h))
        shadow_w = max(16, int((self.push_w + 30) * (1.0 - min(0.7, altitude / 200))))
        shadow_h = max(6, int(10 * (1.0 - min(0.7, altitude / 200))))
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (10, 8, 14, 160), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, (center_x - shadow_w // 2, floor_ground - shadow_h // 2))

        # 2. Determine Animation State & Frame
        current_anim_key = self.state if self.state in self.animations else "idle"
        
        dir_key = f"front_{self.facing}"
        if dir_key not in self.animations[current_anim_key]:
            dir_key = f"front_right"
            
        frames = self.animations[current_anim_key][dir_key]

        if self.state == "jumping":
            if self.vy < -4:
                frame_idx = 0
            elif -4 <= self.vy <= 4:
                frame_idx = min(1, len(frames) - 1)
            else:
                frame_idx = min(2, len(frames) - 1)
        elif self.state == "defeated":
            total_dur = 45
            progress = 1.0 - (max(0, self.state_timer) / total_dur)
            frame_idx = min(int(progress * len(frames)), len(frames) - 1)
        elif self.state in ["attacking", "super", "hit"]:
            total_duration = 36 if self.state == "super" else (26 if self.state == "attacking" else 20)
            progress = 1.0 - max(0, self.state_timer / total_duration)
            frame_idx = min(int(progress * len(frames)), len(frames) - 1)
        else:
            frame_idx = int(self.anim_frame) % len(frames)

        current_sprite = frames[frame_idx]
        spr_w, spr_h = current_sprite.get_size()

        # Align Feet with Physics Position (lifts off floor during jump)
        draw_x = center_x - spr_w // 2
        draw_y = (self.y + self.push_h) - spr_h

        # Forward shift during attacks so reach feels impactful
        if self.state in ["attacking", "super"]:
            reach_shift = 14 if self.char_type == "princess" else 18
            draw_x += reach_shift if self.facing == "right" else -reach_shift

        # Blit Character Sprite
        surface.blit(current_sprite, (draw_x, draw_y))

        # Guard Barrier / Energy Shield Visual
        if self.state == "blocking":
            pulse = math.sin(pygame.time.get_ticks() * 0.012) * 0.15 + 0.85
            shield_w = int(48 * pulse)
            shield_h = int((self.push_h * 1.1) * pulse)
            shield_surf = pygame.Surface((shield_w + 30, shield_h + 30), pygame.SRCALPHA)
            
            shield_x = (self.x + self.push_w - 6) if self.facing == "right" else (self.x - shield_w - 18)
            shield_y = int(self.y + (self.push_h - shield_h) / 2 - 15)
            
            # Outer Ambient Aura
            pygame.draw.ellipse(shield_surf, (*self.primary_color, int(65 * pulse)), (0, 0, shield_w + 30, shield_h + 30))
            # Core Energy Forcefield
            pygame.draw.ellipse(shield_surf, (*self.primary_color, int(150 * pulse)), (15, 15, shield_w, shield_h))
            # White Neon Outer Arc
            pygame.draw.ellipse(shield_surf, (255, 255, 255, int(230 * pulse)), (15, 15, shield_w, shield_h), 3)
            # Tech Inner Energy Arc
            pygame.draw.ellipse(shield_surf, (255, 255, 255, int(160 * pulse)), (23, 23, max(8, shield_w - 16), max(16, shield_h - 16)), 1)
            
            surface.blit(shield_surf, (shield_x, shield_y))


# -------------------------------------------------------------
# PUSH BOX COLLISION RESOLUTION (PREVENT PASS-THROUGH)
# -------------------------------------------------------------
def resolve_fighter_body_collision(f1, f2):
    """Resolves grounded horizontal push-box intersection to prevent fighters passing through each other."""
    f1_bottom = f1.y + f1.push_h
    f2_bottom = f2.y + f2.push_h
    f1_top = f1.y
    f2_top = f2.y

    # Cross-up clearance: allow aerial passage if one fighter jumps over the other
    is_high_jump_cross = (f1_bottom < f2_top + 35) or (f2_bottom < f1_top + 35)
    if is_high_jump_cross:
        return

    left_f = f1 if f1.center_x <= f2.center_x else f2
    right_f = f2 if f1.center_x <= f2.center_x else f1

    overlap = (left_f.x + left_f.push_w) - right_f.x

    if overlap > 0:
        half_overlap = overlap / 2.0
        left_f.x -= half_overlap
        right_f.x += half_overlap

        min_x = 30
        max_x = WIDTH - 30

        if left_f.x < min_x:
            wall_push = min_x - left_f.x
            left_f.x = min_x
            right_f.x = min(max_x - right_f.push_w, right_f.x + wall_push)
        if right_f.x + right_f.push_w > max_x:
            wall_push = (right_f.x + right_f.push_w) - max_x
            right_f.x = max_x - right_f.push_w
            left_f.x = max(min_x, left_f.x - wall_push)

        if left_f.x + left_f.push_w > right_f.x:
            right_f.x = left_f.x + left_f.push_w


# -------------------------------------------------------------
# COMBAT ENGINE & HIT DETECTION
# -------------------------------------------------------------
def process_combat(attacker, defender, particles, hit_flashes):
    """Evaluates attacks, damage calculations, block mitigations, and super moves."""
    shake_amount = 0
    hit_event = None

    is_super = attacker.state == "super"
    is_atk = attacker.state == "attacking"

    if (is_atk or is_super) and not attacker.has_hit_target:
        # Check active attack frame window
        active_window = (4 <= attacker.state_timer <= 18) if is_atk else (4 <= attacker.state_timer <= 28)
        
        if active_window:
            reach = 90 if is_super else 75
            # 10px body overlap ensures point-blank strikes connect reliably
            hx = (attacker.x + attacker.push_w - 10) if attacker.facing == "right" else (attacker.x - reach + 10)
            hy = attacker.y + 20
            hitbox = pygame.Rect(hx, hy, reach, 55)
            hurtbox = pygame.Rect(defender.x + 4, defender.y + 4, defender.push_w - 8, defender.push_h - 8)

            if hitbox.colliderect(hurtbox):
                attacker.has_hit_target = True
                
                # Attacker gains super meter
                attacker.super_meter = min(attacker.max_super, attacker.super_meter + (15 if is_super else 22))

                if defender.state == "blocking":
                    # Full block against normal attacks, minor chip damage against super
                    damage = 4 if is_super else 0
                    defender.hp = max(0, defender.hp - damage)
                    defender.vx = (12 if is_super else 8) if attacker.facing == "right" else (-12 if is_super else -8)
                    shake_amount = 6 if is_super else 3
                    hit_event = "BLOCKED!"

                    # Shield Impact Flash Ring
                    flash_x = (defender.x - 5) if attacker.facing == "right" else (defender.x + defender.push_w + 5)
                    hit_flashes.append([flash_x, defender.y + defender.push_h // 2, 12, 8])

                    # Electric Shield Sparks
                    for _ in range(14):
                        particles.append([
                            defender.center_x,
                            defender.y + defender.push_h // 2,
                            random.uniform(-6, 6),
                            random.uniform(-5, 5),
                            CYAN_ACCENT,
                            240,
                            random.randint(4, 7)
                        ])
                else:
                    # Clean Hit
                    damage = 32 if is_super else 16
                    defender.hp = max(0, defender.hp - damage)
                    defender.state = "hit"
                    defender.state_timer = 22
                    defender.anim_frame = 0
                    
                    knockback = 15 if is_super else 10
                    defender.vx = knockback if attacker.facing == "right" else -knockback
                    defender.vy = -5 if is_super else -2
                    
                    shake_amount = 14 if is_super else 8
                    
                    # Combo Tracking
                    attacker.combo_count += 1
                    attacker.combo_timer = 60
                    hit_event = "SUPER HIT!" if is_super else ("COMBO!" if attacker.combo_count > 1 else "HIT!")

                    # Impact Ring Flash
                    hit_flashes.append([hx + reach // 2, hy + 25, 14, 10])

                    # Blood / Hit Energy Sparks
                    spark_color = GOLD if is_super else attacker.primary_color
                    for _ in range(16 if is_super else 12):
                        particles.append([
                            defender.center_x,
                            defender.y + defender.push_h // 2,
                            random.uniform(-7, 7),
                            random.uniform(-8, -1),
                            spark_color,
                            255,
                            random.randint(3, 6)
                        ])

    return shake_amount, hit_event


# -------------------------------------------------------------
# MATCH CONTROLLER & GLOBALS
# -------------------------------------------------------------
p1 = None
p2 = None
game_state = "menu"  # "menu", "name_input", "round_intro", "fight", "round_over", "match_over", "paused"
previous_state = "fight"

round_num = 1
max_rounds = 3  # Best of 3 (first to 2 wins)
match_time_remaining = 99.0
time_over_handled = False
intro_timer = 0
round_banner_text = ""
match_winner = None

camera_shake = 0
particles = []
hit_flashes = []

p1_name_input = "OGRE"
p2_name_input = "PRINCESS"
active_player_input = 1

# UI Buttons
start_btn = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 + 55, 280, 48)
how_to_btn = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 + 115, 280, 42)

resume_btn = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 - 60, 260, 42)
restart_btn = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 - 5, 260, 42)
home_btn = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 50, 260, 42)


def start_new_match():
    global p1, p2, round_num, match_winner, game_state, intro_timer, match_time_remaining, time_over_handled
    
    p1_binds = {
        "left": pygame.K_a,
        "right": pygame.K_d,
        "jump": pygame.K_w,
        "block": pygame.K_s,
        "attack": pygame.K_g,
        "dash": pygame.K_LSHIFT,
        "super": pygame.K_f
    }
    
    p2_binds = {
        "left": pygame.K_LEFT,
        "right": pygame.K_RIGHT,
        "jump": pygame.K_UP,
        "block": pygame.K_DOWN,
        "attack": pygame.K_l,
        "dash": pygame.K_RCTRL,
        "super": pygame.K_k
    }

    n1 = p1_name_input.strip().upper() if p1_name_input.strip() else "OGRE"
    n2 = p2_name_input.strip().upper() if p2_name_input.strip() else "PRINCESS"

    p1 = Fighter(160, n1, "ogre", OGRE_GREEN, GOLD, p1_binds, target_h=155, player_num=1)
    p2 = Fighter(WIDTH - 220, n2, "princess", PRINCESS_PINK, CYAN_ACCENT, p2_binds, target_h=145, player_num=2)
    
    round_num = 1
    match_winner = None
    start_round(1)


def start_round(r_num):
    global round_num, game_state, intro_timer, match_time_remaining, time_over_handled, round_banner_text
    round_num = r_num
    p1.reset_for_round(160)
    p2.reset_for_round(WIDTH - 220)
    match_time_remaining = 99.0
    time_over_handled = False
    game_state = "round_intro"
    intro_timer = 90
    
    if round_num == 3:
        round_banner_text = "FINAL ROUND"
        speak_announcer_async(f"Final Round! {p1.name} versus {p2.name}! Fight for your life!")
    else:
        round_banner_text = f"ROUND {round_num}"
        speak_announcer_async(f"Round {round_num}! {p1.name} versus {p2.name}! Fight!")


# Initialize First Match Configuration
start_new_match()
game_state = "menu"


# -------------------------------------------------------------
# HUD & UI RENDERING HELPERS
# -------------------------------------------------------------
def draw_tekken_hud(surface):
    bar_w, bar_h = 350, 24
    top_y = 26

    # --- P1 HEALTH BAR (Top Left) ---
    p1_x = 40
    # Container Glow
    pygame.draw.rect(surface, (0, 80, 40), (p1_x - 3, top_y - 3, bar_w + 6, bar_h + 6), border_radius=5)
    pygame.draw.rect(surface, OGRE_GREEN, (p1_x - 2, top_y - 2, bar_w + 4, bar_h + 4), 2, border_radius=4)
    pygame.draw.rect(surface, BLACK, (p1_x, top_y, bar_w, bar_h), border_radius=3)
    
    # Lagging Red Damage Bar
    if p1.display_hp > 0:
        red_w = int(bar_w * (p1.display_hp / p1.max_hp))
        pygame.draw.rect(surface, RED_DAMAGE, (p1_x, top_y, red_w, bar_h), border_radius=3)
    # Active Green Health Bar
    if p1.hp > 0:
        hp_w = int(bar_w * (p1.hp / p1.max_hp))
        pygame.draw.rect(surface, OGRE_GREEN, (p1_x, top_y, hp_w, bar_h), border_radius=3)
        # Highlight Top Edge
        pygame.draw.line(surface, (200, 255, 220), (p1_x, top_y + 1), (p1_x + hp_w, top_y + 1), 2)

    # P1 Name & Round Win Orbs
    p1_lbl = font_hud.render(p1.name, True, WHITE)
    surface.blit(p1_lbl, (p1_x, top_y + bar_h + 6))
    
    # Round Indicators (Tekken Style Stars)
    for i in range(2):
        orb_x = p1_x + 180 + i * 22
        orb_y = top_y + bar_h + 16
        is_won = p1.rounds_won > i
        pygame.draw.circle(surface, GOLD if is_won else DARK_PANEL, (orb_x, orb_y), 7)
        pygame.draw.circle(surface, WHITE if is_won else BORDER_COLOR, (orb_x, orb_y), 7, 2)

    # P1 Super Gauge (Bottom Left)
    sup_x, sup_y, sup_w, sup_h = 40, HEIGHT - 32, 220, 14
    pygame.draw.rect(surface, DARK_PANEL, (sup_x, sup_y, sup_w, sup_h), border_radius=4)
    pygame.draw.rect(surface, BORDER_COLOR, (sup_x, sup_y, sup_w, sup_h), 1, border_radius=4)
    cur_sup_w = int(sup_w * (p1.super_meter / p1.max_super))
    if cur_sup_w > 0:
        super_col = SUPER_ORANGE if p1.super_meter >= p1.max_super else CYAN_ACCENT
        pygame.draw.rect(surface, super_col, (sup_x, sup_y, cur_sup_w, sup_h), border_radius=4)
    sup_text = "SUPER READY! [F]" if p1.super_meter >= p1.max_super else f"SUPER {int(p1.super_meter)}%"
    s_lbl = font_small.render(sup_text, True, GOLD if p1.super_meter >= p1.max_super else SILVER)
    surface.blit(s_lbl, (sup_x + 6, sup_y - 1))

    # --- P2 HEALTH BAR (Top Right) ---
    p2_x = WIDTH - 40 - bar_w
    # Container Glow
    pygame.draw.rect(surface, (100, 0, 50), (p2_x - 3, top_y - 3, bar_w + 6, bar_h + 6), border_radius=5)
    pygame.draw.rect(surface, PRINCESS_PINK, (p2_x - 2, top_y - 2, bar_w + 4, bar_h + 4), 2, border_radius=4)
    pygame.draw.rect(surface, BLACK, (p2_x, top_y, bar_w, bar_h), border_radius=3)
    
    # Lagging Red Damage Bar (anchored right)
    if p2.display_hp > 0:
        red_w = int(bar_w * (p2.display_hp / p2.max_hp))
        pygame.draw.rect(surface, RED_DAMAGE, (p2_x + bar_w - red_w, top_y, red_w, bar_h), border_radius=3)
    # Active Pink Health Bar (anchored right)
    if p2.hp > 0:
        hp_w = int(bar_w * (p2.hp / p2.max_hp))
        pygame.draw.rect(surface, PRINCESS_PINK, (p2_x + bar_w - hp_w, top_y, hp_w, bar_h), border_radius=3)
        pygame.draw.line(surface, (255, 200, 230), (p2_x + bar_w - hp_w, top_y + 1), (p2_x + bar_w, top_y + 1), 2)

    # P2 Name & Round Win Orbs
    p2_lbl = font_hud.render(p2.name, True, WHITE)
    surface.blit(p2_lbl, (p2_x + bar_w - p2_lbl.get_width(), top_y + bar_h + 6))

    for i in range(2):
        orb_x = p2_x + bar_w - 180 - i * 22
        orb_y = top_y + bar_h + 16
        is_won = p2.rounds_won > i
        pygame.draw.circle(surface, GOLD if is_won else DARK_PANEL, (orb_x, orb_y), 7)
        pygame.draw.circle(surface, WHITE if is_won else BORDER_COLOR, (orb_x, orb_y), 7, 2)

    # P2 Super Gauge (Bottom Right)
    sup2_x = WIDTH - 40 - sup_w
    pygame.draw.rect(surface, DARK_PANEL, (sup2_x, sup_y, sup_w, sup_h), border_radius=4)
    pygame.draw.rect(surface, BORDER_COLOR, (sup2_x, sup_y, sup_w, sup_h), 1, border_radius=4)
    cur_sup2_w = int(sup_w * (p2.super_meter / p2.max_super))
    if cur_sup2_w > 0:
        super2_col = SUPER_ORANGE if p2.super_meter >= p2.max_super else PRINCESS_PINK
        pygame.draw.rect(surface, super2_col, (sup2_x + sup_w - cur_sup2_w, sup_y, cur_sup2_w, sup_h), border_radius=4)
    sup2_text = "SUPER READY! [K]" if p2.super_meter >= p2.max_super else f"SUPER {int(p2.super_meter)}%"
    s2_lbl = font_small.render(sup2_text, True, GOLD if p2.super_meter >= p2.max_super else SILVER)
    surface.blit(s2_lbl, (sup2_x + sup_w - s2_lbl.get_width() - 6, sup_y - 1))

    # --- CENTER FIGHT TIMER & VS BADGE ---
    timer_box = pygame.Rect(WIDTH // 2 - 38, top_y - 4, 76, 44)
    pygame.draw.rect(surface, DARK_PANEL, timer_box, border_radius=6)
    pygame.draw.rect(surface, GOLD, timer_box, 2, border_radius=6)
    
    display_sec = max(0, int(math.ceil(match_time_remaining - 1e-4)))
    t_str = f"{display_sec:02d}"
    t_surf = font_timer.render(t_str, True, RED_DAMAGE if display_sec <= 10 else WHITE)
    surface.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, top_y - 2))

    # Combo Counters
    if p1.combo_count > 1 and p1.combo_timer > 0:
        c1_surf = font_combo.render(f"{p1.combo_count} HITS!", True, GOLD)
        surface.blit(c1_surf, (p1_x + 10, top_y + 60))
    if p2.combo_count > 1 and p2.combo_timer > 0:
        c2_surf = font_combo.render(f"{p2.combo_count} HITS!", True, GOLD)
        surface.blit(c2_surf, (p2_x + bar_w - c2_surf.get_width() - 10, top_y + 60))

    # Bottom Controls Guide
    guide_bar = pygame.Surface((560, 16), pygame.SRCALPHA)
    guide_bar.fill((14, 12, 22, 190))
    surface.blit(guide_bar, (WIDTH // 2 - 280, HEIGHT - 18))
    g_text = font_small.render("P1: [A/D] Move [W] Jump [S] Shield [G] Attack [F] Super  |  P2: [<-/->] Move [^] Jump [v] Shield [L] Attack [K] Super", True, SILVER)
    surface.blit(g_text, (WIDTH // 2 - g_text.get_width() // 2, HEIGHT - 17))


# -------------------------------------------------------------
# MAIN GAME LOOP
# -------------------------------------------------------------
running = True

while running:
    dt = clock.tick(60) / 1000.0
    if dt > 0.1:
        dt = 0.1
    mouse_pos = pygame.mouse.get_pos()

    # Camera Shake Effect
    shake_x = random.randint(-camera_shake, camera_shake) if camera_shake > 0 else 0
    shake_y = random.randint(-camera_shake, camera_shake) if camera_shake > 0 else 0
    if camera_shake > 0 and game_state != "paused":
        camera_shake -= 1

    # Render Surface Creation
    render_surf = pygame.Surface((WIDTH, HEIGHT))
    
    # 1. Background Arena
    if bg_image:
        render_surf.blit(bg_image, (0, 0))
    else:
        render_surf.fill(DARK_BG)
        pygame.draw.rect(render_surf, (30, 28, 44), (0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y))

    # ---------------------------------------------------------
    # EVENT HANDLING
    # ---------------------------------------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "menu":
                if start_btn.collidepoint(mouse_pos):
                    game_state = "name_input"
                    active_player_input = 1
                    p1_name_input = p1.name
                    p2_name_input = p2.name
                elif how_to_btn.collidepoint(mouse_pos):
                    start_new_match()

            elif game_state == "paused":
                if resume_btn.collidepoint(mouse_pos):
                    game_state = previous_state
                    pygame.mixer.music.unpause()
                elif restart_btn.collidepoint(mouse_pos):
                    start_new_match()
                    pygame.mixer.music.play(-1)
                elif home_btn.collidepoint(mouse_pos):
                    game_state = "menu"

        if event.type == pygame.KEYDOWN:
            # Menu Hotkeys
            if game_state == "name_input":
                if event.key == pygame.K_RETURN:
                    if active_player_input == 1:
                        active_player_input = 2
                    elif active_player_input == 2:
                        p1.name = p1_name_input.strip().upper() if p1_name_input.strip() else "OGRE"
                        p2.name = p2_name_input.strip().upper() if p2_name_input.strip() else "PRINCESS"
                        start_new_match()
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

            # Pause Controls
            elif event.key in [pygame.K_p, pygame.K_ESCAPE]:
                if game_state in ["fight", "round_intro", "round_over"]:
                    previous_state = game_state
                    game_state = "paused"
                    pygame.mixer.music.pause()
                elif game_state == "paused":
                    game_state = previous_state
                    pygame.mixer.music.unpause()

            # Fighting Controls
            if game_state == "fight":
                # Player 1 Actions
                if event.key == p1.controls["attack"]:
                    p1.attack()
                elif event.key == p1.controls["dash"]:
                    p1.dash(pygame.key.get_pressed(), particles)
                elif event.key == p1.controls["super"]:
                    if p1.super_attack():
                        speak_announcer_async("Super Move Unleashed!")
                        camera_shake = 16

                # Player 2 Actions
                if event.key == p2.controls["attack"]:
                    p2.attack()
                elif event.key == p2.controls["dash"]:
                    p2.dash(pygame.key.get_pressed(), particles)
                elif event.key == p2.controls["super"]:
                    if p2.super_attack():
                        speak_announcer_async("Super Move Unleashed!")
                        camera_shake = 16

            # Match Over Shortcuts
            if game_state == "match_over":
                if event.key == pygame.K_r:
                    start_new_match()
                    speak_announcer_async("Rematch initiated! Fight!")
                elif event.key == pygame.K_q:
                    game_state = "menu"

    # ---------------------------------------------------------
    # STATE LOGIC & UPDATES
    # ---------------------------------------------------------
    
    # 1. MAIN MENU STATE
    if game_state == "menu":
        # Dark Cyber Overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 18, 220))
        render_surf.blit(overlay, (0, 0))

        # Title Glow & Typography
        pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.005))
        title_sub_glow = font_title.render("TEKKEN BRAWL", True, OGRE_GREEN)
        title_sub_glow.set_alpha(pulse // 3)
        title_main = font_title.render("TEKKEN BRAWL", True, WHITE)

        t_x = WIDTH // 2 - title_main.get_width() // 2
        t_y = HEIGHT // 2 - 140
        render_surf.blit(title_sub_glow, (t_x - 3, t_y - 2))
        render_surf.blit(title_sub_glow, (t_x + 3, t_y + 2))
        render_surf.blit(title_main, (t_x, t_y))

        sub_msg = font_sub.render("OGRE  VS  PRINCESS : CHAMPIONSHIP ARENA", True, GOLD)
        render_surf.blit(sub_msg, (WIDTH // 2 - sub_msg.get_width() // 2, t_y + 80))

        # Start Button
        h_start = start_btn.collidepoint(mouse_pos)
        pygame.draw.rect(render_surf, (0, 240, 120, 40) if h_start else DARK_PANEL, start_btn, border_radius=6)
        pygame.draw.rect(render_surf, OGRE_GREEN if h_start else GOLD, start_btn, 2 if h_start else 1, border_radius=6)
        btn1_txt = font_hud.render("ENTER TOURNAMENT", True, WHITE if not h_start else OGRE_GREEN)
        render_surf.blit(btn1_txt, (start_btn.x + start_btn.width // 2 - btn1_txt.get_width() // 2, start_btn.y + 10))

        # Quick Play Button
        h_quick = how_to_btn.collidepoint(mouse_pos)
        pygame.draw.rect(render_surf, DARK_PANEL, how_to_btn, border_radius=6)
        pygame.draw.rect(render_surf, PRINCESS_PINK if h_quick else SILVER, how_to_btn, 2 if h_quick else 1, border_radius=6)
        btn2_txt = font_sub.render("QUICK MATCH [DEFAULT NAMES]", True, PRINCESS_PINK if h_quick else SILVER)
        render_surf.blit(btn2_txt, (how_to_btn.x + how_to_btn.width // 2 - btn2_txt.get_width() // 2, how_to_btn.y + 11))

        # Control Guide Footer
        guide1 = font_small.render("P1: [W,A,S,D] Move | [G] Strike | [L-Shift] Dash | [F] Super", True, SILVER)
        guide2 = font_small.render("P2: [ARROWS] Move | [L] Strike | [R-Ctrl] Dash | [K] Super", True, SILVER)
        render_surf.blit(guide1, (WIDTH // 2 - guide1.get_width() // 2, HEIGHT - 55))
        render_surf.blit(guide2, (WIDTH // 2 - guide2.get_width() // 2, HEIGHT - 32))

    # 2. NAME INPUT / FIGHTER SELECT STATE
    elif game_state == "name_input":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 8, 18, 230))
        render_surf.blit(overlay, (0, 0))

        header = font_banner.render("CHOOSE COMBATANT NAMES", True, GOLD)
        render_surf.blit(header, (WIDTH // 2 - header.get_width() // 2, 45))

        cursor = "|" if (pygame.time.get_ticks() // 350) % 2 == 0 else " "

        # Player 1 Box
        box1 = pygame.Rect(WIDTH // 2 - 220, 160, 440, 52)
        b1_col = OGRE_GREEN if active_player_input == 1 else BORDER_COLOR
        pygame.draw.rect(render_surf, DARK_PANEL, box1, border_radius=6)
        pygame.draw.rect(render_surf, b1_col, box1, 2 if active_player_input == 1 else 1, border_radius=6)
        
        lbl1 = font_hud.render("PLAYER 1 (OGRE):", True, OGRE_GREEN)
        render_surf.blit(lbl1, (box1.x, box1.y - 30))
        txt1 = font_hud.render(p1_name_input + (cursor if active_player_input == 1 else ""), True, WHITE)
        render_surf.blit(txt1, (box1.x + 16, box1.y + 12))

        # Player 2 Box
        box2 = pygame.Rect(WIDTH // 2 - 220, 270, 440, 52)
        b2_col = PRINCESS_PINK if active_player_input == 2 else BORDER_COLOR
        pygame.draw.rect(render_surf, DARK_PANEL, box2, border_radius=6)
        pygame.draw.rect(render_surf, b2_col, box2, 2 if active_player_input == 2 else 1, border_radius=6)

        lbl2 = font_hud.render("PLAYER 2 (PRINCESS):", True, PRINCESS_PINK)
        render_surf.blit(lbl2, (box2.x, box2.y - 30))
        txt2 = font_hud.render(p2_name_input + (cursor if active_player_input == 2 else ""), True, WHITE)
        render_surf.blit(txt2, (box2.x + 16, box2.y + 12))

        hint = font_sub.render("TYPE NAME AND PRESS ENTER TO CONFIRM", True, SILVER)
        render_surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 370))

    # 3. FIGHT & ROUND STATES
    elif game_state in ["round_intro", "fight", "round_over", "match_over", "paused"]:
        keys = pygame.key.get_pressed()

        # Update Fighters during active fight
        if game_state == "fight":
            # Match Countdown Timer based on exact real elapsed time
            if match_time_remaining > 0:
                match_time_remaining = max(0.0, match_time_remaining - dt)
                if match_time_remaining <= 0 and not time_over_handled:
                    time_over_handled = True
                    match_time_remaining = 0.0
                    # Time Over Evaluation
                    if p1.hp > p2.hp:
                        p2.hp = 0
                        p2.state = "defeated"
                        p2.state_timer = 45
                        game_state = "round_over"
                        intro_timer = 110
                        p1.rounds_won += 1
                        speak_announcer_async(f"TIME OVER! {p1.name} wins on health!")
                    elif p2.hp > p1.hp:
                        p1.hp = 0
                        p1.state = "defeated"
                        p1.state_timer = 45
                        game_state = "round_over"
                        intro_timer = 110
                        p2.rounds_won += 1
                        speak_announcer_async(f"TIME OVER! {p2.name} wins on health!")
                    else:
                        p1.hp = 0
                        p2.hp = 0
                        p1.state = "defeated"
                        p2.state = "defeated"
                        p1.state_timer = 45
                        p2.state_timer = 45
                        game_state = "round_over"
                        intro_timer = 110
                        speak_announcer_async("TIME OVER! DRAW ROUND!")

            # Fighter Physics & Updates
            if p1.state != "defeated":
                p1.update(keys, p2)
            else:
                p1.state_timer = max(0, p1.state_timer - 1)

            if p2.state != "defeated":
                p2.update(keys, p1)
            else:
                p2.state_timer = max(0, p2.state_timer - 1)

            # Resolve Body Push-Box Collision (Prevents Passing Through)
            resolve_fighter_body_collision(p1, p2)

            # Process Combat Hits & Collisions
            shk1, evt1 = process_combat(p1, p2, particles, hit_flashes)
            shk2, evt2 = process_combat(p2, p1, particles, hit_flashes)
            if shk1 > camera_shake: camera_shake = shk1
            if shk2 > camera_shake: camera_shake = shk2

            # Check Knockout / Round End
            if p1.hp <= 0 and p1.state != "defeated":
                p1.hp = 0
                p1.state = "defeated"
                p1.state_timer = 45
                game_state = "round_over"
                intro_timer = 110
                p2.rounds_won += 1
                speak_announcer_async(f"K.O.! {p2.name} wins the round!")

            elif p2.hp <= 0 and p2.state != "defeated":
                p2.hp = 0
                p2.state = "defeated"
                p2.state_timer = 45
                game_state = "round_over"
                intro_timer = 110
                p1.rounds_won += 1
                speak_announcer_async(f"K.O.! {p1.name} wins the round!")

        # Draw Fighters
        p1.draw(render_surf)
        p2.draw(render_surf)

        # Particle System Updates & Render
        for part in particles[:]:
            part[0] += part[2]
            part[1] += part[3]
            part[3] += 0.35  # Particle gravity
            part[5] -= 7     # Alpha fade
            if part[5] <= 0:
                particles.remove(part)
            else:
                p_surf = pygame.Surface((part[6] * 2, part[6] * 2), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*part[4], int(part[5])), (part[6], part[6]), part[6])
                render_surf.blit(p_surf, (part[0] - part[6], part[1] - part[6]))

        # Hit Flash Wave Effects
        for flash in hit_flashes[:]:
            flash[2] += 7
            flash[3] -= 1
            pygame.draw.circle(render_surf, (255, 255, 255, 120), (int(flash[0]), int(flash[1])), int(flash[2]), 2)
            if flash[3] <= 0:
                hit_flashes.remove(flash)

        # Render Top HUD
        draw_tekken_hud(render_surf)

        # Round Intro Banner
        if game_state == "round_intro":
            mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            mask.fill((10, 8, 18, 140))
            render_surf.blit(mask, (0, 0))

            b_surf = font_banner.render(round_banner_text, True, GOLD)
            f_surf = font_hud.render("READY... FIGHT!", True, WHITE)
            render_surf.blit(b_surf, (WIDTH // 2 - b_surf.get_width() // 2, HEIGHT // 2 - 50))
            render_surf.blit(f_surf, (WIDTH // 2 - f_surf.get_width() // 2, HEIGHT // 2 + 18))

            intro_timer -= 1
            if intro_timer <= 0:
                game_state = "fight"

        # Round Over Banner
        elif game_state == "round_over":
            ko_surf = font_title.render("K. O. !", True, RED_DAMAGE)
            render_surf.blit(ko_surf, (WIDTH // 2 - ko_surf.get_width() // 2, HEIGHT // 2 - 60))

            intro_timer -= 1
            if intro_timer <= 0:
                # Check for overall match champion (First to 2 wins)
                if p1.rounds_won >= 2:
                    game_state = "match_over"
                    match_winner = p1
                    speak_announcer_async(f"{p1.name} is the ULTIMATE BRAWL CHAMPION! Dominator match complete!")
                elif p2.rounds_won >= 2:
                    game_state = "match_over"
                    match_winner = p2
                    speak_announcer_async(f"{p2.name} is the ULTIMATE BRAWL CHAMPION! Dominator match complete!")
                else:
                    start_round(round_num + 1)

        # Match Over (Tournament Winner Screen)
        elif game_state == "match_over":
            mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            mask.fill((10, 8, 18, 210))
            render_surf.blit(mask, (0, 0))

            win_title = font_banner.render(f"{match_winner.name} VICTORIOUS!", True, GOLD)
            champ_sub = font_hud.render("TOURNAMENT CHAMPIONSHIP COMPLETE", True, WHITE)
            res_hint = font_sub.render("PRESS [R] FOR REMATCH  |  PRESS [Q] FOR MAIN MENU", True, SILVER)

            render_surf.blit(win_title, (WIDTH // 2 - win_title.get_width() // 2, HEIGHT // 2 - 60))
            render_surf.blit(champ_sub, (WIDTH // 2 - champ_sub.get_width() // 2, HEIGHT // 2 + 10))
            render_surf.blit(res_hint, (WIDTH // 2 - res_hint.get_width() // 2, HEIGHT // 2 + 65))

        # Pause Menu Overlay
        elif game_state == "paused":
            mask = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            mask.fill((10, 8, 18, 200))
            render_surf.blit(mask, (0, 0))

            p_title = font_banner.render("GAME PAUSED", True, WHITE)
            render_surf.blit(p_title, (WIDTH // 2 - p_title.get_width() // 2, HEIGHT // 2 - 130))

            # Resume Button
            h1 = resume_btn.collidepoint(mouse_pos)
            pygame.draw.rect(render_surf, (0, 240, 120, 40) if h1 else DARK_PANEL, resume_btn, border_radius=4)
            pygame.draw.rect(render_surf, OGRE_GREEN if h1 else GOLD, resume_btn, 1, border_radius=4)
            t1 = font_sub.render("RESUME COMBAT", True, WHITE)
            render_surf.blit(t1, (resume_btn.x + resume_btn.width // 2 - t1.get_width() // 2, resume_btn.y + 11))

            # Restart Button
            h2 = restart_btn.collidepoint(mouse_pos)
            pygame.draw.rect(render_surf, (255, 40, 140, 40) if h2 else DARK_PANEL, restart_btn, border_radius=4)
            pygame.draw.rect(render_surf, PRINCESS_PINK if h2 else GOLD, restart_btn, 1, border_radius=4)
            t2 = font_sub.render("RESTART MATCH", True, WHITE)
            render_surf.blit(t2, (restart_btn.x + restart_btn.width // 2 - t2.get_width() // 2, restart_btn.y + 11))

            # Lobby Button
            h3 = home_btn.collidepoint(mouse_pos)
            pygame.draw.rect(render_surf, DARK_PANEL, home_btn, border_radius=4)
            pygame.draw.rect(render_surf, WHITE if h3 else GOLD, home_btn, 1, border_radius=4)
            t3 = font_sub.render("RETURN TO MAIN LOBBY", True, WHITE)
            render_surf.blit(t3, (home_btn.x + home_btn.width // 2 - t3.get_width() // 2, home_btn.y + 11))

    # Blit Final Render Surface with Camera Shake to Screen
    screen.blit(render_surf, (shake_x, shake_y))
    pygame.display.flip()

# Cleanup
pygame.quit()
sys.exit()