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
        self.change_x = 0
        self.change_y = 0
        self.on_ground = False

    def update(self):
        # Apply gravity
        if not self.on_ground:
            self.change_y += 1
        
        # Move vertically
        self.rect.y += self.change_y
        
        # Check for collision with ground/platforms
        if self.rect.y >= SCREEN_HEIGHT - PLAYER_HEIGHT:
            self.rect.y = SCREEN_HEIGHT - PLAYER_HEIGHT
            self.on_ground = True
            self.change_y = 0
        
        # Move horizontally
        self.rect.x += self.change_x
        
        # Boundaries check
        if self.rect.x < 0:
            self.rect.x = 0
        elif self.rect.x > SCREEN_WIDTH - PLAYER_WIDTH:
            self.rect.x = SCREEN_WIDTH - PLAYER_WIDTH

    def jump(self):
        if self.on_ground:
            self.change_y += JUMP_STRENGTH
            self.on_ground = False

    def go_left(self):
        self.change_x = -5

    def go_right(self):
        self.change_x = 5

    def stop(self):
        self.change_x = 0


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
                if event.key == pygame.K_SPACE:
                    player.jump()
                if event.key == pygame.K_LEFT:
                    player.go_left()
                if event.key == pygame.K_RIGHT:
                    player.go_right()

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                    player.stop()

        # Update sprites
        all_sprites.update()

        # Check for collisions with platforms (basic example)
        player.on_ground = False 
        for platform in platforms:
            if player.rect.colliderect(platform.rect) and player.change_y >= 0:
                player.rect.bottom = platform.rect.top 
                player.on_ground = True 
                player.change_y = 0 

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
