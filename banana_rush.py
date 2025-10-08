import cv2
import mediapipe as mp
import pygame
import random
import math
import sys

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

# Load PNG images with 3D effects
try:
    # Load and scale images
    banana_img = pygame.image.load('banana.png').convert_alpha()
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

BG_COLOR = (34, 139, 34)

# Game variables with difficulty system
score = 0
lives = 3
object_speed = 3
spawn_rate = 30
objects = []
frame_count = 0
game_state = 'menu'
selected_difficulty = None

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
    screen.fill((20, 40, 20))
    title = font.render('Banana Rush', True, (255, 255, 0))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
    
    if not paused:
        # Show difficulty selection
        if not selected_difficulty:
            subtitle = small_font.render('Select Difficulty:', True, (200, 200, 200))
            screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 120))
            
            easy_text = font.render('1: Easy (5 Lives)', True, (200, 255, 200))
            screen.blit(easy_text, (WIDTH//2 - easy_text.get_width()//2, 160))
            
            med_text = font.render('2: Medium (3 Lives)', True, (255, 200, 200))
            screen.blit(med_text, (WIDTH//2 - med_text.get_width()//2, 200))
            
            hard_text = font.render('3: Hard (2 Lives)', True, (255, 100, 100))
            screen.blit(hard_text, (WIDTH//2 - hard_text.get_width()//2, 240))
            
            # Show difficulty descriptions
            easy_desc = small_font.render('Easy: Forgiving gameplay, score penalties only', True, (150, 200, 150))
            screen.blit(easy_desc, (WIDTH//2 - easy_desc.get_width()//2, 290))
            
            med_desc = small_font.render('Medium: Balanced challenge, life penalties', True, (200, 150, 150))
            screen.blit(med_desc, (WIDTH//2 - med_desc.get_width()//2, 315))
            
            hard_desc = small_font.render('Hard: Unforgiving, instant game over risks', True, (200, 100, 100))
            screen.blit(hard_desc, (WIDTH//2 - hard_desc.get_width()//2, 340))
        else:
            # Show selected difficulty and start option
            diff_text = font.render(f'Selected: {selected_difficulty.title()}', True, (255, 255, 255))
            screen.blit(diff_text, (WIDTH//2 - diff_text.get_width()//2, 150))
            
            start_text = font.render('S: Start Game', True, (255, 255, 255))
            screen.blit(start_text, (WIDTH//2 - start_text.get_width()//2, 200))
            
            back_text = small_font.render('B: Back to Difficulty Selection', True, (200, 200, 200))
            screen.blit(back_text, (WIDTH//2 - back_text.get_width()//2, 250))
    else:
        # Pause menu
        pause_text = font.render('PAUSED', True, (255, 255, 0))
        screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, 150))
        
        point_text = font.render('Point to continue', True, (200, 255, 200))
        screen.blit(point_text, (WIDTH//2 - point_text.get_width()//2, 200))
        
        # Show current game stats
        if score > 0 or lives < DIFFICULTY_CONFIG[selected_difficulty]['lives']:
            stats_text = small_font.render(f'Score: {score} | Lives: {lives} | Difficulty: {selected_difficulty.title()}', True, (200, 200, 200))
            screen.blit(stats_text, (WIDTH//2 - stats_text.get_width()//2, 280))
    
    quit_text = font.render('Q: Quit', True, (255, 255, 255))
    screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 380))
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
        'rotation': random.randint(0, 360),
        'rotation_speed': random.uniform(2, 8),
        'scale': random.uniform(0.8, 1.2),
        'wobble_phase': random.uniform(0, 2*math.pi),
        'fall_speed': random.uniform(0.8, 1.2),
        'swing': random.uniform(-2, 2)
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
        base_img = bomb_img
    
    # Apply wobble effect
    wobble_scale = 1.0 + 0.1 * math.sin(obj['wobble_phase'])
    current_scale = obj['scale'] * wobble_scale
    
    # Scale the image
    scaled_size = int(80 * current_scale)
    if scaled_size > 0:
        scaled_img = pygame.transform.scale(base_img, (scaled_size, scaled_size))
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
    
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lm = hand_landmarks.landmark
            h, w, _ = frame.shape
            tip_x, tip_y = int(lm[8].x * WIDTH), int(lm[8].y * HEIGHT)
            if is_index_finger_up(lm):
                monkey_tip = (tip_x, tip_y)
                hand_pointing = True
            if is_hand_closed(lm):
                hand_closed = True

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
        clock.tick(10)
        continue

    # Get difficulty configuration
    config = DIFFICULTY_CONFIG[selected_difficulty] if selected_difficulty else DIFFICULTY_CONFIG['medium']
    
    # Dynamic background based on difficulty
    bg_color = config['bg_color']
    screen.fill(bg_color)
    
    # Animated background effect
    for y in range(0, HEIGHT, 4):
        green_val = int(bg_color[1] + 20 * math.sin((y + frame_count) * 0.01))
        pygame.draw.line(screen, (bg_color[0], green_val, bg_color[2]), (0, y), (WIDTH, y))

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

    # Draw enhanced monkey hand
    if monkey_tip:
        # Draw glowing hand cursor
        for i in range(8):
            size = 20 - i * 2
            color = (255, 100 - i * 10, 100 - i * 10)
            pygame.draw.circle(screen, color, monkey_tip, size)
        
        # Add sparkle effect
        if frame_count % 5 == 0:
            sparkle_x = monkey_tip[0] + random.randint(-15, 15)
            sparkle_y = monkey_tip[1] + random.randint(-15, 15)
            pygame.draw.circle(screen, (255, 255, 255), (sparkle_x, sparkle_y), 2)
        
        # Check for catching objects
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