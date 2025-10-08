#source .venv/Scripts/activate
import cv2
import mediapipe as mp
import pygame
import random
import math
import sys
import os

# Initialize MediaPipe Hand
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# Helper to check if index finger is up (extended)
def is_index_finger_up(landmarks):
    return landmarks[8].y < landmarks[6].y and abs(landmarks[8].x - landmarks[6].x) < 0.1

# Helper to check if all fingers are folded (for pause)
def is_hand_closed(landmarks):
    return all(landmarks[i].y > landmarks[i-2].y for i in [8, 12, 16, 20])

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Banana Rush')
clock = pygame.time.Clock()

font = pygame.font.SysFont('comicsans', 36)
small_font = pygame.font.SysFont('comicsans', 24)

def render_text_centered(text, font_obj, color, y, outline=True):
    surf = font_obj.render(text, True, color)
    x = WIDTH//2 - surf.get_width()//2
    if outline:
        for ox, oy in [(-2,0),(2,0),(0,-2),(0,2)]:
            screen.blit(font_obj.render(text, True, (0,0,0)), (x+ox, y+oy))
    screen.blit(surf, (x, y))
    return surf.get_rect(topleft=(x, y))

# Load PNG images with 3D effects
try:
    # Load and scale images
    banana_img = pygame.image.load('banana.png').convert_alpha()
    # Prefer new coconut at assets/coconut.png if present
    coconut_path = 'assets/coconut.png'
    if os.path.exists(coconut_path):
        coconut_img = pygame.image.load(coconut_path).convert_alpha()
        print('Loaded coconut from', coconut_path)
    else:
        coconut_img = pygame.image.load('coconut.png').convert_alpha()
    bomb_img = pygame.image.load('bomb.png').convert_alpha()
    
    # Scale images to game size
    banana_img = pygame.transform.scale(banana_img, (80, 80))
    coconut_img = pygame.transform.scale(coconut_img, (80, 80))
    bomb_img = pygame.transform.scale(bomb_img, (80, 80))
    
    images_loaded = True
    print("Images loaded successfully!")
except:
    # Fallback colors if images not found
    images_loaded = False
    BANANA_COLOR = (255, 255, 0)
    COCONUT_COLOR = (139, 69, 19)
    BOMB_COLOR = (0, 0, 0)
    print("Images not found, using colored circles")

# Load bomb animation frames (override single bomb image if frames exist)
bomb_frames = []
try:
    import os
    bomb_dir = 'assets/bomb'
    if os.path.isdir(bomb_dir):
        frame_files = sorted([f for f in os.listdir(bomb_dir) if f.lower().endswith(('.png', '.gif'))])
        for fname in frame_files:
            fp = os.path.join(bomb_dir, fname)
            try:
                frm = pygame.image.load(fp).convert_alpha()
                frm = pygame.transform.scale(frm, (80, 80))
                bomb_frames.append(frm)
            except Exception:
                continue
        if bomb_frames:
            print(f"Loaded {len(bomb_frames)} bomb animation frames.")
except Exception as e:
    print('Bomb frame load error:', e)

BG_COLOR = (34, 139, 34)

# Game variables with difficulty system
score = 0
lives = 3
object_speed = 3
spawn_rate = 30
objects = []
frame_count = 0
game_state = 'main_menu'  # New distinct main menu before difficulty selection
selected_difficulty = None
main_menu_index = 0  # Tracks which button is selected on the main menu

# Attempt to load UI background image (robust path attempts)
ui_bg = None
grass_layer = None
for candidate in [
    'assets/backgrounds/uibg.png',
    'assets/backgrounds/uibg.jpg',
    'assets/backgrounds/uibg.jpeg',
    'assets/background/uibg.png',   # legacy singular
    'assets/background/uibg.jpg',
    'assets/background/uibg.jpeg',
    'assets/uibg.png',
    'assets/uibg.jpg'
]:
    try:
        ui_bg = pygame.image.load(candidate).convert()
        ui_bg = pygame.transform.scale(ui_bg, (WIDTH, HEIGHT))
        print(f"Loaded UI background: {candidate}")
        break
    except Exception:
        continue

# Load grass foreground layer (depth element)
try:
    gpath = 'assets/backgrounds/grass.png'
    grass_raw = pygame.image.load(gpath).convert_alpha()
    # Scale width to screen, keep aspect ratio; anchor bottom
    scale_w = WIDTH
    ratio = scale_w / grass_raw.get_width()
    scale_h = int(grass_raw.get_height() * ratio)
    grass_layer = pygame.transform.smoothscale(grass_raw, (scale_w, scale_h))
    print('Loaded grass layer for foreground depth.')
except Exception as e:
    print('Grass layer not loaded:', e)

# Style helpers
UI_TITLE_COLOR = (230, 210, 170)
UI_BUTTON_COLOR = (90, 60, 40)
UI_BUTTON_HOVER = (140, 100, 70)
UI_BUTTON_BORDER = (40, 25, 15)
UI_BACKDROP_TINT = (30, 20, 10)

MAIN_MENU_BUTTONS = ["START", "OPTIONS", "CREDITS", "EXIT"]

def draw_main_menu(selected_index: int):
    # Draw background image or tinted fallback
    if ui_bg:
        screen.blit(ui_bg, (0, 0))
    else:
        screen.fill((60, 40, 30))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((*UI_BACKDROP_TINT, 90))
        screen.blit(tint, (0, 0))

    # Title panel
    title_text = font.render('BANANA RUSH', True, UI_TITLE_COLOR)
    title_rect = title_text.get_rect(center=(WIDTH//2, 110))
    pygame.draw.rect(screen, UI_BUTTON_BORDER, title_rect.inflate(40, 30))
    pygame.draw.rect(screen, UI_BUTTON_COLOR, title_rect.inflate(30, 20))
    screen.blit(title_text, title_rect)

    # Buttons vertically stacked
    start_y = 210
    spacing = 62
    for i, label in enumerate(MAIN_MENU_BUTTONS):
        btn_text = font.render(label, True, UI_TITLE_COLOR)
        btn_rect = btn_text.get_rect(center=(WIDTH//2, start_y + i * spacing))
        outer = btn_rect.inflate(60, 26)
        inner = btn_rect.inflate(50, 16)
        # Background layers
        pygame.draw.rect(screen, UI_BUTTON_BORDER, outer, border_radius=6)
        base_color = UI_BUTTON_HOVER if i == selected_index else UI_BUTTON_COLOR
        pygame.draw.rect(screen, base_color, inner, border_radius=6)
        # Add subtle top highlight
        highlight = pygame.Surface(inner.size, pygame.SRCALPHA)
        pygame.draw.rect(highlight, (255, 255, 255, 35), highlight.get_rect().inflate(-4, -inner.height//2), border_radius=6)
        screen.blit(highlight, inner.topleft)
        screen.blit(btn_text, btn_rect)

    help_text = small_font.render('Use UP/DOWN + ENTER (Esc to Quit)', True, (220, 200, 180))
    screen.blit(help_text, (WIDTH//2 - help_text.get_width()//2, HEIGHT - 60))
    pygame.display.flip()

def draw_game_background(frame_count: int, config):
    """Draw the in-game background using the UI background image if available,
    otherwise fall back to the legacy procedural gradient lines.
    A subtle animated vertical oscillation and difficulty tint are applied.
    """
    if ui_bg:
        # Slight vertical float to give life
        offset = int(5 * math.sin(frame_count * 0.01))
        screen.blit(ui_bg, (0, offset))
        if offset > 0:
            # Fill gap at top when image shifts down
            screen.blit(ui_bg, (0, offset - HEIGHT))
        # Difficulty tint overlay
        tint_color = config['bg_color'] if config else (0, 0, 0)
        tint_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        # Light alpha so art shows through
        tint_surf.fill((*tint_color, 60))
        screen.blit(tint_surf, (0, 0))
        # Foreground grass parallax (slower vertical oscillation) if available
        if grass_layer:
            g_offset = int(3 * math.sin(frame_count * 0.006))
            g_rect = grass_layer.get_rect(midbottom=(WIDTH//2, HEIGHT + g_offset))
            screen.blit(grass_layer, g_rect)
    else:
        # Fallback to previous animated background
        bg_color = config['bg_color'] if config else (34, 139, 34)
        screen.fill(bg_color)
        for y in range(0, HEIGHT, 4):
            green_val = int(bg_color[1] + 20 * math.sin((y + frame_count) * 0.01))
            pygame.draw.line(screen, (bg_color[0], green_val, bg_color[2]), (0, y), (WIDTH, y))

# Difficulty configurations
DIFFICULTY_CONFIG = {
    'easy': {
        'lives': 5,
        'object_speed': 2,
        'spawn_rate': 40,
        'coconut_penalty': 1,  # Score reduction
        'bomb_penalty': 1,     # Lives lost
        'miss_penalty': False, # No penalty for missing bananas
        'bg_color': (34, 139, 34)
    },
    'medium': {
        'lives': 3,
        'object_speed': 3,
        'spawn_rate': 30,
        'coconut_penalty': 'life',  # Lose a life
        'bomb_penalty': 2,          # Lives lost
        'miss_penalty': False,
        'bg_color': (25, 100, 25)
    },
    'hard': {
        'lives': 2,
        'object_speed': 4,
        'spawn_rate': 25,
        'coconut_penalty': 'game_over',  # Instant game over
        'bomb_penalty': 'game_over',     # Instant game over
        'miss_penalty': True,            # Lose life for missing bananas
        'bg_color': (15, 60, 15)
    }
}

def draw_menu(paused=False):
    # Background for difficulty selection or pause overlay
    if not paused:
        if ui_bg:
            screen.blit(ui_bg, (0,0))
            dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dark.fill((0,0,0,140))
            screen.blit(dark, (0,0))
        else:
            screen.fill((25,35,25))
    else:
        # Pause uses darkened current frame (caller already drew screen before switching?)
        if ui_bg:
            screen.blit(ui_bg, (0,0))
            dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            dim.fill((0,0,0,190))
            screen.blit(dim, (0,0))
        else:
            screen.fill((15,25,15))

    # Title
    title_rect = render_text_centered('BANANA RUSH', font, (255, 225, 120), 40)
    pygame.draw.rect(screen, (80,55,25), title_rect.inflate(40,20), border_radius=8)
    pygame.draw.rect(screen, (140,100,60), title_rect.inflate(30,10), border_radius=8)
    render_text_centered('BANANA RUSH', font, (255, 225, 120), 40)
    
    if not paused:
        # Show difficulty selection
        if not selected_difficulty:
            # Background panel for heading to ensure visibility
            heading_y = 100
            panel_rect = pygame.Rect(0,0,480,70)
            panel_rect.center = (WIDTH//2, heading_y+35)
            panel_surf = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
            panel_surf.fill((0,0,0,140))
            screen.blit(panel_surf, panel_rect.topleft)
            render_text_centered('Select Difficulty', font, (255,255,255), heading_y)

            # Button specs
            btn_data = [
                ('1: EASY', 'Forgiving / score penalties only', (90,150,90), (140,210,140)),
                ('2: MEDIUM', 'Balanced challenge & life loss', (150,120,120), (210,170,170)),
                ('3: HARD', 'High risk: instant failures', (170,70,70), (230,110,110))
            ]
            base_y = 190  # Shift buttons slightly lower to make space for heading panel
            for i,(title,label,c1,c2) in enumerate(btn_data):
                y = base_y + i*90
                rect = pygame.Rect(0,0,520,70)
                rect.center = (WIDTH//2, y)
                # Panel
                pygame.draw.rect(screen, c1, rect, border_radius=10)
                inner = rect.inflate(-8,-8)
                pygame.draw.rect(screen, c2, inner, border_radius=10)
                # Title
                t_surf = small_font.render(title, True, (20,20,20))
                screen.blit(t_surf, (inner.x + 16, inner.y + 8))
                # Label
                l_surf = small_font.render(label, True, (30,30,30))
                screen.blit(l_surf, (inner.x + 16, inner.y + 36))

            instruct = small_font.render('Press 1 / 2 / 3 to choose difficulty', True, (230,230,230))
            screen.blit(instruct, (WIDTH//2 - instruct.get_width()//2, HEIGHT - 120))
            start_hint = small_font.render('Then press S to Start | Q to Quit | M for Main Menu', True, (220,220,220))
            screen.blit(start_hint, (WIDTH//2 - start_hint.get_width()//2, HEIGHT - 90))
        else:
            chosen_color = (255,255,255)
            render_text_centered(f'Selected: {selected_difficulty.title()}', font, chosen_color, 150)
            panel = pygame.Rect(0,0,480,140)
            panel.center = (WIDTH//2, 250)
            pygame.draw.rect(screen, (60,60,80), panel, border_radius=12)
            pygame.draw.rect(screen, (120,120,160), panel.inflate(-10,-10), border_radius=12)
            t1 = small_font.render('S: Start Game', True, (10,10,10))
            t2 = small_font.render('B: Back to Difficulty Selection', True, (10,10,10))
            screen.blit(t1, (panel.centerx - t1.get_width()//2, panel.y + 25))
            screen.blit(t2, (panel.centerx - t2.get_width()//2, panel.y + 70))
    else:
        # Pause menu
        pause_text = font.render('PAUSED', True, (255, 255, 0))
        screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, 150))
        
        point_text = font.render('Point to continue', True, (200, 255, 200))
        screen.blit(point_text, (WIDTH//2 - point_text.get_width()//2, 200))

        # New option: Return to Main Menu
        menu_text = small_font.render('M: Main Menu', True, (220, 220, 220))
        screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, 240))
        
        # Show current game stats
        if score > 0 or lives < DIFFICULTY_CONFIG[selected_difficulty]['lives']:
            stats_text = small_font.render(f'Score: {score} | Lives: {lives} | Difficulty: {selected_difficulty.title()}', True, (200, 200, 200))
            screen.blit(stats_text, (WIDTH//2 - stats_text.get_width()//2, 280))
    
    quit_text = font.render('Q: Quit', True, (255, 255, 255))
    screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, HEIGHT - 50))
    pygame.display.flip()

def draw_game_over():
    screen.fill((40, 20, 20))
    game_over_text = font.render('GAME OVER', True, (255, 100, 100))
    screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, 200))
    
    final_score = font.render(f'Final Score: {score}', True, (255, 255, 255))
    screen.blit(final_score, (WIDTH//2 - final_score.get_width()//2, 250))
    
    difficulty_text = small_font.render(f'Difficulty: {selected_difficulty.title()}', True, (200, 200, 200))
    screen.blit(difficulty_text, (WIDTH//2 - difficulty_text.get_width()//2, 290))
    
    restart_text = font.render('R: Restart | M: Menu | Q: Quit', True, (255, 255, 255))
    screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, 350))
    pygame.display.flip()

# Webcam setup
cap = cv2.VideoCapture(0)

# Enhanced object creation with difficulty-based properties
def random_object():
    if not selected_difficulty:
        kind = 'banana'  # Default
    else:
        # Adjust probabilities based on difficulty
        if selected_difficulty == 'easy':
            weights = [0.8, 0.15, 0.05]  # More bananas, fewer bombs
        elif selected_difficulty == 'medium':
            weights = [0.7, 0.2, 0.1]   # Balanced
        else:  # hard
            weights = [0.6, 0.25, 0.15] # More obstacles
        
        kind = random.choices(['banana', 'coconut', 'bomb'], weights=weights)[0]
    
    x = random.randint(80, WIDTH-80)
    y = -80
    return {
        'kind': kind, 
        'x': x, 
        'y': y, 
        'radius': 40,
        'caught': False,
        'rotation': random.randint(0,360),  # Used for non-frame objects
        'rotation_speed': random.uniform(2, 8),
        'scale': random.uniform(0.8, 1.2),
        'wobble_phase': random.uniform(0, 2*math.pi),
        'fall_speed': random.uniform(0.8, 1.2),
        'swing': random.uniform(-2, 2),
        'anim_index': 0,
        'anim_counter': 0
    }

# Enhanced 3D drawing function (same as before)
def draw_object(obj):
    if not images_loaded:
        # Fallback to colored circles
        color = BANANA_COLOR if obj['kind']=='banana' else COCONUT_COLOR if obj['kind']=='coconut' else BOMB_COLOR
        pygame.draw.circle(screen, color, (int(obj['x']), int(obj['y'])), obj['radius'])
        return
    
    # Update 3D animation properties
    obj['rotation'] += obj['rotation_speed']
    obj['wobble_phase'] += 0.1
    obj['x'] += obj['swing'] * 0.5
    
    # Keep objects within screen bounds
    if obj['x'] < 40:
        obj['x'] = 40
        obj['swing'] = abs(obj['swing'])
    elif obj['x'] > WIDTH - 40:
        obj['x'] = WIDTH - 40
        obj['swing'] = -abs(obj['swing'])
    
    # Select the appropriate image
    if obj['kind'] == 'banana':
        base_img = banana_img
    elif obj['kind'] == 'coconut':
        base_img = coconut_img
    else:  # bomb
        if bomb_frames:
            # Simple frame animation
            obj['anim_counter'] += 1
            if obj['anim_counter'] >= 5:  # frame delay
                obj['anim_counter'] = 0
                obj['anim_index'] = (obj['anim_index'] + 1) % len(bomb_frames)
            base_img = bomb_frames[obj['anim_index']]
        else:
            base_img = bomb_img
    
    # Apply wobble effect (skip wobble scaling for bombs to keep constant size)
    if obj['kind'] == 'bomb':
        current_scale = obj['scale']  # constant
    else:
        wobble_scale = 1.0 + 0.1 * math.sin(obj['wobble_phase'])
        current_scale = obj['scale'] * wobble_scale
    
    # Scale the image (coconut slightly smaller base size)
    base_size = 80
    if obj['kind'] == 'coconut':
        base_size = 60  # reduced size for coconut
    scaled_size = int(base_size * current_scale)
    if scaled_size > 0:
        scaled_img = pygame.transform.scale(base_img, (scaled_size, scaled_size))
        # Always rotate (including bombs) for a spinning fall effect
        rotated_img = pygame.transform.rotate(scaled_img, obj['rotation'])
        
        # Create shadow effect
        shadow_img = rotated_img.copy()
        shadow_img.fill((0, 0, 0, 80), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Position the images
        img_rect = rotated_img.get_rect(center=(int(obj['x']), int(obj['y'])))
        shadow_rect = shadow_img.get_rect(center=(int(obj['x'] + 4), int(obj['y'] + 4)))
        
        # Draw shadow first, then main image
        screen.blit(shadow_img, shadow_rect)
        screen.blit(rotated_img, img_rect)
        
        # Add glint effect
        if obj['rotation'] % 360 < 5:
            glint_pos = (int(obj['x'] - scaled_size//4), int(obj['y'] - scaled_size//4))
            pygame.draw.circle(screen, (255, 255, 255, 150), glint_pos, 5)

# Particle system for slice effects
particles = []

def create_slice_particles(x, y, obj_kind):
    colors = {
        'banana': [(255, 255, 0), (255, 200, 0), (255, 150, 0)],
        'coconut': [(139, 69, 19), (160, 82, 45), (210, 180, 140)],
        'bomb': [(255, 0, 0), (255, 100, 0), (255, 150, 0)]
    }
    
    for _ in range(10):
        particle = {
            'x': x + random.randint(-20, 20),
            'y': y + random.randint(-20, 20),
            'vx': random.uniform(-5, 5),
            'vy': random.uniform(-8, -2),
            'life': 30,
            'color': random.choice(colors[obj_kind])
        }
        particles.append(particle)

def update_particles():
    global particles
    for particle in particles[:]:
        particle['x'] += particle['vx']
        particle['y'] += particle['vy']
        particle['vy'] += 0.3
        particle['life'] -= 1
        
        if particle['life'] <= 0:
            particles.remove(particle)
        else:
            size = max(1, particle['life'] // 6)
            pygame.draw.circle(screen, particle['color'], 
                             (int(particle['x']), int(particle['y'])), size)

def reset_game():
    global score, lives, objects, frame_count
    if selected_difficulty:
        config = DIFFICULTY_CONFIG[selected_difficulty]
        lives = config['lives']
        score = 0
        objects = []
        frame_count = 0

# Finger sprite (animated) setup
finger_frames = []
finger_frame_index = 0
finger_anim_counter = 0
FINGER_ANIM_DELAY = 6  # frames between animation steps

# Pointer virtual position & jump control
pointer_x = WIDTH // 2
pointer_y_base = int(HEIGHT * 0.75)  # 3/4 down screen
pointer_y = pointer_y_base
jump_active = False
jump_velocity = 0.0
JUMP_STRENGTH = -18.0
GRAVITY = 1.0
JUMP_COOLDOWN_FRAMES = 25
last_jump_frame = -999

def update_pointer(monkey_tip_raw, frame_count):
    """Update constrained pointer position.
    Horizontal follows raw x; vertical fixed unless jumping. Jump triggers when
    raw finger y is raised above top threshold quickly while pointing.
    """
    global pointer_x, pointer_y, jump_active, jump_velocity, last_jump_frame
    # Follow horizontal smoothly
    if monkey_tip_raw:
        target_x = monkey_tip_raw[0]
        pointer_x += int((target_x - pointer_x) * 0.25)  # smoothing

    # Jump initiation condition: raw y in upper 1/3 of frame
    if (monkey_tip_raw and monkey_tip_raw[1] < HEIGHT * 0.33 and
        frame_count - last_jump_frame > JUMP_COOLDOWN_FRAMES and not jump_active):
        jump_active = True
        jump_velocity = JUMP_STRENGTH
        last_jump_frame = frame_count

    if jump_active:
        jump_velocity += GRAVITY
        pointer_y += jump_velocity
        if pointer_y >= pointer_y_base:
            pointer_y = pointer_y_base
            jump_active = False
            jump_velocity = 0.0
    else:
        pointer_y = pointer_y_base

    return (pointer_x, int(pointer_y))

def load_finger_sprite():
    global finger_frames
    # Try animated GIF first
    gif_path = 'assets/finger_tip.gif'
    try:
        gif = pygame.image.load(gif_path).convert_alpha()
        # Split GIF if multiple frames? Pygame treats GIF as static; so fallback to frame sequence below.
    except Exception:
        pass
    # Load sequence s1.png, s2.png, ...
    import os
    base_dir = 'assets'
    if os.path.isdir(base_dir):
        numbered = []
        for i in range(1, 50):
            p = os.path.join(base_dir, f's{i}.png')
            if os.path.exists(p):
                try:
                    img = pygame.image.load(p).convert_alpha()
                    # Scale to 48x48 for consistent cursor size
                    img = pygame.transform.smoothscale(img, (48, 48))
                    numbered.append(img)
                except Exception:
                    continue
        if numbered:
            finger_frames = numbered
    # If still empty, create a fallback gradient circle surface once
    if not finger_frames:
        surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        center = 24
        for r in range(24, 0, -1):
            alpha = int(255 * (1 - r / 24))
            pygame.draw.circle(surf, (255, 60 + r*3, 60 + r*3, alpha), (center, center), r)
        finger_frames = [surf]

def draw_finger_sprite(pos, frame_count):
    global finger_frame_index, finger_anim_counter
    if not finger_frames:
        load_finger_sprite()
    finger_anim_counter += 1
    if finger_anim_counter >= FINGER_ANIM_DELAY:
        finger_anim_counter = 0
        finger_frame_index = (finger_frame_index + 1) % len(finger_frames)
    frame = finger_frames[finger_frame_index]
    rect = frame.get_rect(center=pos)
    screen.blit(frame, rect)
    # Optional sparkle effect (reuse existing timing)
    if frame_count % 10 == 0 and len(finger_frames) == 1:
        sx = pos[0] + random.randint(-10, 10)
        sy = pos[1] + random.randint(-10, 10)
        pygame.draw.circle(screen, (255, 255, 255), (sx, sy), 2)

# Main game loop
running = True
while running:
    # Webcam frame
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)
    monkey_tip = None
    hand_pointing = False
    hand_closed = False
    raw_tip = None
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark
            h, w, _ = frame.shape
            tip_x, tip_y = int(lm[8].x * WIDTH), int(lm[8].y * HEIGHT)
            if is_index_finger_up(lm):
                raw_tip = (tip_x, tip_y)
                hand_pointing = True
            if is_hand_closed(lm):
                hand_closed = True

    if game_state == 'main_menu':
        draw_main_menu(main_menu_index)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    main_menu_index = (main_menu_index - 1) % len(MAIN_MENU_BUTTONS)
                elif event.key == pygame.K_DOWN:
                    main_menu_index = (main_menu_index + 1) % len(MAIN_MENU_BUTTONS)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    choice = MAIN_MENU_BUTTONS[main_menu_index]
                    if choice == 'START':
                        game_state = 'menu'  # Go to difficulty selection (legacy menu)
                    elif choice == 'OPTIONS':
                        game_state = 'options'
                    elif choice == 'CREDITS':
                        game_state = 'credits'
                    elif choice == 'EXIT':
                        running = False
        clock.tick(30)
        continue

    if game_state == 'options':
        # Simple placeholder options screen
        screen.fill((25, 25, 40))
        txt = font.render('OPTIONS', True, (240, 240, 240))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 80))
        back_msg = small_font.render('Press ESC to Main Menu', True, (200, 200, 200))
        screen.blit(back_msg, (WIDTH//2 - back_msg.get_width()//2, HEIGHT - 100))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = 'main_menu'
        pygame.display.flip()
        clock.tick(30)
        continue

    if game_state == 'credits':
        screen.fill((40, 25, 25))
        txt = font.render('CREDITS', True, (255, 230, 180))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 70))
        lines = [
            'Game: Banana Rush',
            'Concept: You',
            'Programming: (placeholder)',
            'Art / UI: (placeholder)',
            'Press ESC to return'
        ]
        for i, line in enumerate(lines):
            lsurf = small_font.render(line, True, (230, 210, 200))
            screen.blit(lsurf, (WIDTH//2 - lsurf.get_width()//2, 160 + i * 40))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                game_state = 'main_menu'
        pygame.display.flip()
        clock.tick(30)
        continue

    if game_state == 'menu':
        draw_menu(paused=False)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    selected_difficulty = 'easy'
                elif event.key == pygame.K_2:
                    selected_difficulty = 'medium'
                elif event.key == pygame.K_3:
                    selected_difficulty = 'hard'
                elif event.key == pygame.K_s and selected_difficulty:
                    game_state = 'running'
                    reset_game()
                elif event.key == pygame.K_b:
                    selected_difficulty = None
                elif event.key == pygame.K_q:
                    running = False
        clock.tick(10)
        continue

    elif game_state == 'game_over':
        draw_game_over()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    game_state = 'running'
                    reset_game()
                elif event.key == pygame.K_m:
                    game_state = 'menu'
                    selected_difficulty = None
                elif event.key == pygame.K_q:
                    running = False
        clock.tick(10)
        continue

    # Pause logic
    if game_state == 'running' and hand_closed:
        game_state = 'paused'
    elif game_state == 'paused' and hand_pointing and not hand_closed:
        game_state = 'running'

    if game_state == 'paused':
        draw_menu(paused=True)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_m:
                    # Return to new main menu; reset selection to allow choosing difficulty again
                    game_state = 'main_menu'
                    selected_difficulty = None
                    # Clear active game objects & stats to avoid carry-over
                    objects = []
                    score = 0
                    # Lives will be set when a new difficulty is selected
        clock.tick(10)
        continue

    # Get difficulty configuration
    config = DIFFICULTY_CONFIG[selected_difficulty] if selected_difficulty else DIFFICULTY_CONFIG['medium']
    
    # New unified game background draw (uses ui_bg if available)
    draw_game_background(frame_count, config)

    if game_state == 'running':
        frame_count += 1
        
        # Spawn objects based on difficulty
        if frame_count % config['spawn_rate'] == 0:
            objects.append(random_object())
            
        # Move objects with difficulty-based speed
        for obj in objects:
            obj['y'] += config['object_speed'] * obj['fall_speed']
        
        # Check for missed bananas in hard mode
        if config['miss_penalty']:
            for obj in objects[:]:
                if obj['kind'] == 'banana' and obj['y'] >= HEIGHT and not obj['caught']:
                    lives -= 1
                    objects.remove(obj)
                    create_slice_particles(obj['x'], HEIGHT - 50, 'bomb')  # Red particles for penalty
            
        # Remove off-screen objects
        objects = [obj for obj in objects if obj['y'] < HEIGHT + 100 and not obj['caught']]

    # Draw objects with 3D effects
    for obj in objects:
        draw_object(obj)

    # Update and draw particles
    update_particles()

    # Update & draw constrained pointer (horizontal follow, jump vertical)
    monkey_tip = update_pointer(raw_tip, frame_count)
    if hand_pointing:
        draw_finger_sprite(monkey_tip, frame_count)

        # Check for catching objects (unchanged logic threshold may need adjusting for sprite size)
        for obj in objects:
            if not obj['caught']:
                dist = math.hypot(monkey_tip[0] - obj['x'], monkey_tip[1] - obj['y'])
                if dist < obj['radius'] + 20:
                    obj['caught'] = True
                    
                    # Create slice particles
                    create_slice_particles(obj['x'], obj['y'], obj['kind'])
                    
                    # Apply difficulty-based scoring and penalties
                    if obj['kind'] == 'banana':
                        score += 1
                    elif obj['kind'] == 'coconut':
                        penalty = config['coconut_penalty']
                        if penalty == 'game_over':
                            lives = 0
                        elif penalty == 'life':
                            lives -= 1
                        else:  # Score reduction
                            score = max(0, score - penalty)
                    elif obj['kind'] == 'bomb':
                        penalty = config['bomb_penalty']
                        if penalty == 'game_over':
                            lives = 0
                        else:
                            lives -= penalty

    # Check for game over
    if lives <= 0:
        game_state = 'game_over'

    # Draw enhanced HUD
    for offset in [(2, 2), (1, 1), (0, 0)]:
        color = (0, 0, 0) if offset != (0, 0) else (255, 255, 255)
        score_text = font.render(f'Score: {score}', True, color)
        screen.blit(score_text, (10 + offset[0], 10 + offset[1]))
        
        lives_text = font.render(f'Lives: {lives}', True, (255, 100, 100) if offset == (0, 0) else (0, 0, 0))
        screen.blit(lives_text, (10 + offset[0], 50 + offset[1]))
        
        diff_text = small_font.render(f'Difficulty: {selected_difficulty.title() if selected_difficulty else "None"}', True, color)
        screen.blit(diff_text, (10 + offset[0], 90 + offset[1]))

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    pygame.display.flip()
    clock.tick(60)

cap.release()
cv2.destroyAllWindows()
pygame.quit()
sys.exit()