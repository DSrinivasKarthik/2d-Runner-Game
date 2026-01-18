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
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((PLATFORM_WIDTH, PLATFORM_HEIGHT))
        self.image.fill(PLATFORM_COLOR)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


def main():
    # Create sprite groups
    all_sprites = pygame.sprite.Group()
    platforms = pygame.sprite.Group()

    # Create player instance
    player = Player()
    all_sprites.add(player)

    # Create platforms randomly positioned in the screen.
    for i in range(5):
        x_pos = random.randint(0, SCREEN_WIDTH - PLATFORM_WIDTH)
        y_pos = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - PLATFORM_HEIGHT)
        platform = Platform(x_pos, y_pos)
        all_sprites.add(platform)
        platforms.add(platform)

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

        # Update player with proper collision resolution
        player.update(platforms)

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
