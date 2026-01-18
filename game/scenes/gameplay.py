from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from game.scene_manager import Scene, SceneResult
from game.settings import GameConfig


@dataclass
class World:
    platforms: pygame.sprite.Group
    all_sprites: pygame.sprite.Group
    ground: "Platform"


class Player(pygame.sprite.Sprite):
    def __init__(self, config: GameConfig, screen_size: tuple[int, int]):
        super().__init__()
        self._cfg = config
        self._screen_w, self._screen_h = screen_size

        self.image = pygame.Surface((config.player_width, config.player_height))
        self.image.fill(config.player_color)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = self._screen_h - config.player_height - config.platform_height

        self.pos = pygame.Vector2(self.rect.x, self.rect.y)
        self.change_x = 0.0
        self.change_y = 0.0
        self.on_ground = False

        self.move_left = False
        self.move_right = False

    def jump(self) -> None:
        if self.on_ground:
            self.change_y = float(self._cfg.jump_strength)
            self.on_ground = False

    def update(self, platforms: pygame.sprite.Group) -> None:
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
            if self.change_x > 0:
                self.change_x = max(0.0, self.change_x - friction)
            elif self.change_x < 0:
                self.change_x = min(0.0, self.change_x + friction)

        # Apply gravity
        self.change_y += gravity

        # --- Horizontal move + resolve ---
        self.pos.x += self.change_x
        self.rect.x = int(round(self.pos.x))

        for platform in pygame.sprite.spritecollide(self, platforms, False):
            if self.change_x > 0:
                self.rect.right = platform.rect.left
            elif self.change_x < 0:
                self.rect.left = platform.rect.right
            self.pos.x = float(self.rect.x)
            self.change_x = 0.0

        # Screen bounds (horizontal)
        if self.rect.left < 0:
            self.rect.left = 0
            self.pos.x = float(self.rect.x)
            self.change_x = 0.0
        elif self.rect.right > self._screen_w:
            self.rect.right = self._screen_w
            self.pos.x = float(self.rect.x)
            self.change_x = 0.0

        # --- Vertical move + resolve ---
        self.pos.y += self.change_y
        self.rect.y = int(round(self.pos.y))

        for platform in pygame.sprite.spritecollide(self, platforms, False):
            if self.change_y > 0:
                self.rect.bottom = platform.rect.top
                self.on_ground = True
            elif self.change_y < 0:
                self.rect.top = platform.rect.bottom
            self.pos.y = float(self.rect.y)
            self.change_y = 0.0

        # Ground clamp
        if self.rect.bottom >= self._screen_h:
            self.rect.bottom = self._screen_h
            self.pos.y = float(self.rect.y)
            self.on_ground = True
            self.change_y = 0.0


class Platform(pygame.sprite.Sprite):
    def __init__(
        self,
        config: GameConfig,
        x: float,
        y: int,
        width: int,
        height: int,
    ):
        super().__init__()
        self._cfg = config
        self.image = pygame.Surface((width, height))
        self.image.fill(config.platform_color)
        self.rect = self.image.get_rect()

        self.pos_x = float(x)
        self.rect.x = int(round(self.pos_x))
        self.rect.y = y

    def update(self, scroll_speed: float) -> None:
        self.pos_x -= float(scroll_speed)
        self.rect.x = int(round(self.pos_x))


def _platform_generation_params(config: GameConfig, screen_h: int) -> dict[str, int]:
    gravity = 0.6
    max_speed = 8.0
    jump_v = abs(float(config.jump_strength))

    airtime = (2 * jump_v) / gravity
    max_gap = int(max_speed * airtime * 0.55)

    min_gap = 70
    max_gap = max(140, min(max_gap, 260))
    max_step_up = int((jump_v * jump_v) / (2 * gravity) * 0.65)
    max_step_up = max(70, min(max_step_up, 160))
    max_step_down = 140

    top_y = screen_h - 280
    bottom_y = screen_h - 80

    return {
        "min_gap": min_gap,
        "max_gap": max_gap,
        "max_step_up": max_step_up,
        "max_step_down": max_step_down,
        "top_y": top_y,
        "bottom_y": bottom_y,
    }


def spawn_next_platform(config: GameConfig, screen_h: int, last_platform: Platform) -> Platform:
    p = _platform_generation_params(config, screen_h)

    gap = random.randint(p["min_gap"], p["max_gap"])
    width = random.randint(int(config.platform_width * 0.8), int(config.platform_width * 1.6))

    next_x = last_platform.rect.right + gap

    delta_y = random.randint(-p["max_step_up"], p["max_step_down"])
    next_y = last_platform.rect.y + delta_y
    next_y = max(p["top_y"], min(p["bottom_y"], next_y))

    return Platform(
        config=config,
        x=float(next_x),
        y=int(next_y),
        width=int(width),
        height=int(config.platform_height),
    )


@dataclass
class GameplayScene(Scene):
    config: GameConfig
    screen_size: tuple[int, int]

    def __post_init__(self) -> None:
        self._screen_w, self._screen_h = self.screen_size

        self._scroll_speed = 2.5
        self._auto_run = True
        self._runner_x = 160

        self.all_sprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()

        self.player = Player(self.config, self.screen_size)
        self.all_sprites.add(self.player)

        # Ground
        self.ground = Platform(
            config=self.config,
            x=0,
            y=self._screen_h - self.config.platform_height,
            width=self._screen_w * 3,
            height=self.config.platform_height,
        )
        self.platforms.add(self.ground)
        self.all_sprites.add(self.ground)

        # Sensible platform chain
        last = Platform(
            config=self.config,
            x=200,
            y=self._screen_h - 180,
            width=int(self.config.platform_width * 1.2),
            height=self.config.platform_height,
        )
        self.platforms.add(last)
        self.all_sprites.add(last)

        while last.rect.x < self._screen_w + 500:
            last = spawn_next_platform(self.config, self._screen_h, last)
            self.platforms.add(last)
            self.all_sprites.add(last)

        self._pending: SceneResult | None = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._pending = SceneResult.switch(
                    __import__("game.scenes.menu", fromlist=["MainMenuScene"]).MainMenuScene(
                        config=self.config,
                        screen_size=self.screen_size,
                    )
                )
            elif event.key == pygame.K_UP:
                self.player.jump()
            elif event.key == pygame.K_LEFT:
                self.player.move_left = True
            elif event.key == pygame.K_RIGHT:
                self.player.move_right = True

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                self.player.move_left = False
            elif event.key == pygame.K_RIGHT:
                self.player.move_right = False

    def update(self, dt: float):
        # Move platforms (endless scroll)
        self.platforms.update(self._scroll_speed)

        # Update player + collisions
        self.player.update(self.platforms)

        # Auto-run camera follow
        if self._auto_run:
            dx = self.player.rect.x - self._runner_x
            if dx != 0:
                for plat in self.platforms:
                    plat.pos_x -= dx
                    plat.rect.x = int(round(plat.pos_x))
                self.player.pos.x -= dx
                self.player.rect.x = int(round(self.player.pos.x))

        # Ground wrap
        while self.ground.rect.right < self._screen_w:
            self.ground.pos_x += self.ground.rect.width
            self.ground.rect.x = int(round(self.ground.pos_x))
        while self.ground.rect.left > 0:
            self.ground.pos_x -= self.ground.rect.width
            self.ground.rect.x = int(round(self.ground.pos_x))

        # Recycle platforms
        non_ground = [p for p in self.platforms if p is not self.ground]
        if non_ground:
            furthest = max(non_ground, key=lambda s: s.rect.right)
            for plat in list(non_ground):
                if plat.rect.right < -200:
                    plat.kill()
                    new_plat = spawn_next_platform(self.config, self._screen_h, furthest)
                    self.platforms.add(new_plat)
                    self.all_sprites.add(new_plat)
                    furthest = new_plat

        pending, self._pending = self._pending, None
        return pending

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.config.background_color)
        self.all_sprites.draw(screen)
