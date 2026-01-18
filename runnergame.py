import pygame
import random
import json

# Initialize Pygame
pygame.init()

# Load configuration from JSON file
with open('config.json') as config_file:
    config = json.load(config_file)

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Endless / world settings
AUTO_RUN = True
RUNNER_X = 160
SCROLL_SPEED = 2.5

# Colors from config
BACKGROUND_COLOR = config['background']['color']
PLAYER_COLOR = config['player']['color']
PLATFORM_COLOR = config['platforms']['color']
OBSTACLE_COLOR = config['obstacles']['color']

# Player settings from config
PLAYER_WIDTH = config['player']['width']
PLAYER_HEIGHT = config['player']['height']
JUMP_STRENGTH = config['player']['jump_strength']

# Platform settings from config
PLATFORM_WIDTH = config['platforms']['width']
PLATFORM_HEIGHT = config['platforms']['height']

# Create the screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("2D Runner Platform Game")

# Clock to control the frame rate
clock = pygame.time.Clock()

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((PLAYER_WIDTH, PLAYER_HEIGHT))
        self.image.fill(PLAYER_COLOR)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = SCREEN_HEIGHT - PLAYER_HEIGHT - PLATFORM_HEIGHT
        self.pos = pygame.Vector2(self.rect.x, self.rect.y)
        self.change_x = 0
        self.change_y = 0
        self.on_ground = False
        self.move_left = False
        self.move_right = False

    def update(self, platforms):
        # Grounded state is recomputed every frame from collisions
        self.on_ground = False

        # Movement tuning
        max_speed = 8.0
        accel = 0.5
        friction = 0.5
        gravity = 0.6

        # Apply smooth horizontal acceleration
        if self.move_left and not self.move_right:
            self.change_x = max(self.change_x - accel, -max_speed)
        elif self.move_right and not self.move_left:
            self.change_x = min(self.change_x + accel, max_speed)
        else:
            # Decelerate smoothly when no keys pressed
            if self.change_x > 0:
                self.change_x = max(0, self.change_x - friction)
            elif self.change_x < 0:
                self.change_x = min(0, self.change_x + friction)

        # Apply gravity
        self.change_y += gravity

        # --- Horizontal move + resolve ---
        self.pos.x += self.change_x
        self.rect.x = round(self.pos.x)

        for platform in pygame.sprite.spritecollide(self, platforms, False):
            if self.change_x > 0:
                self.rect.right = platform.rect.left
            elif self.change_x < 0:
                self.rect.left = platform.rect.right
            self.pos.x = self.rect.x
            self.change_x = 0

        # Screen bounds (horizontal)
        if self.rect.left < 0:
            self.rect.left = 0
            self.pos.x = self.rect.x
            self.change_x = 0
        elif self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.pos.x = self.rect.x
            self.change_x = 0

        # --- Vertical move + resolve ---
        self.pos.y += self.change_y
        self.rect.y = round(self.pos.y)

        for platform in pygame.sprite.spritecollide(self, platforms, False):
            if self.change_y > 0:
                # Falling: land on top
                self.rect.bottom = platform.rect.top
                self.on_ground = True
            elif self.change_y < 0:
                # Rising: hit head
                self.rect.top = platform.rect.bottom
            self.pos.y = self.rect.y
            self.change_y = 0

        # Ground clamp
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
            self.pos.y = self.rect.y
            self.on_ground = True
            self.change_y = 0

    def jump(self):
        if self.on_ground:
            self.change_y = JUMP_STRENGTH
            self.on_ground = False

    def go_left(self):
        self.move_left = True

    def go_right(self):
        self.move_right = True

    def stop_left(self):
        self.move_left = False

    def stop_right(self):
        self.move_right = False


class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, width=PLATFORM_WIDTH, height=PLATFORM_HEIGHT):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(PLATFORM_COLOR)
        self.rect = self.image.get_rect()
        self.pos_x = float(x)
        self.rect.x = int(round(self.pos_x))
        self.rect.y = y

    def update(self, scroll_speed):
        self.pos_x -= float(scroll_speed)
        self.rect.x = int(round(self.pos_x))


def _platform_generation_params():
    # Use physics to pick gaps/steps that are actually reachable.
    # These are conservative so platforms "make sense" for gameplay.
    gravity = 0.6
    max_speed = 8.0
    jump_v = abs(JUMP_STRENGTH)

    # Approx airtime to return to same height: t ~= 2*v/g
    airtime = (2 * jump_v) / gravity
    # Use a safety factor because player won't always be at max speed.
    max_gap = int(max_speed * airtime * 0.55)

    min_gap = 70
    max_gap = max(140, min(max_gap, 260))
    max_step_up = int((jump_v * jump_v) / (2 * gravity) * 0.65)
    max_step_up = max(70, min(max_step_up, 160))
    max_step_down = 140

    top_y = SCREEN_HEIGHT - 280
    bottom_y = SCREEN_HEIGHT - 80

    return {
        "min_gap": min_gap,
        "max_gap": max_gap,
        "max_step_up": max_step_up,
        "max_step_down": max_step_down,
        "top_y": top_y,
        "bottom_y": bottom_y,
    }


def spawn_next_platform(last_platform):
    p = _platform_generation_params()

    gap = random.randint(p["min_gap"], p["max_gap"])
    width = random.randint(int(PLATFORM_WIDTH * 0.8), int(PLATFORM_WIDTH * 1.6))

    next_x = last_platform.rect.right + gap

    # Step the height gradually so jumps are reachable.
    delta_y = random.randint(-p["max_step_up"], p["max_step_down"])
    next_y = last_platform.rect.y + delta_y
    next_y = max(p["top_y"], min(p["bottom_y"], next_y))

    return Platform(next_x, next_y, width=width)


def main():
    # Create sprite groups
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()

    # Create player instance
    player = Player()
    all_sprites.add(player)

    # Create a ground platform (stable reference for gameplay)
    ground = Platform(0, SCREEN_HEIGHT - PLATFORM_HEIGHT, width=SCREEN_WIDTH * 3)
    platforms.add(ground)
    all_sprites.add(ground)

    # Create a sensible, reachable chain of platforms extending beyond the screen
    last = Platform(200, SCREEN_HEIGHT - 180, width=int(PLATFORM_WIDTH * 1.2))
    platforms.add(last)
    all_sprites.add(last)

    while last.rect.x < SCREEN_WIDTH + 500:
        last = spawn_next_platform(last)
        platforms.add(last)
        all_sprites.add(last)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    player.jump()
                if event.key == pygame.K_LEFT:
                    player.go_left()
                if event.key == pygame.K_RIGHT:
                    player.go_right()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    player.stop_left()
                if event.key == pygame.K_RIGHT:
                    player.stop_right()

        # Base world scroll (auto-run)
        platforms.update(SCROLL_SPEED)

        # Update player with proper collision resolution
        player.update(platforms)

        # Auto-run camera: keep the runner near a fixed X, move world instead.
        if AUTO_RUN:
            dx = player.rect.x - RUNNER_X
            if dx != 0:
                for plat in platforms:
                    plat.pos_x -= dx
                    plat.rect.x = int(round(plat.pos_x))
                player.pos.x -= dx
                player.rect.x = int(round(player.pos.x))

        # Wrap ground so it always covers the bottom
        while ground.rect.right < SCREEN_WIDTH:
            ground.pos_x += ground.rect.width
            ground.rect.x = int(round(ground.pos_x))
        while ground.rect.left > 0:
            ground.pos_x -= ground.rect.width
            ground.rect.x = int(round(ground.pos_x))

        # Recycle off-screen platforms by spawning new ones ahead (ignore ground)
        non_ground = [p for p in platforms if p is not ground]
        if non_ground:
            furthest = max(non_ground, key=lambda s: s.rect.right)
            for plat in list(non_ground):
                if plat.rect.right < -200:
                    plat.kill()
                    new_plat = spawn_next_platform(furthest)
                    platforms.add(new_plat)
                    all_sprites.add(new_plat)
                    furthest = new_plat

        # Fill the screen with background color and draw all sprites
        screen.fill(BACKGROUND_COLOR)
        all_sprites.draw(screen)

        # Refresh the display
        pygame.display.flip()

        # Cap the frame rate
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
