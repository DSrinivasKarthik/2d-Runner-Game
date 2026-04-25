from __future__ import annotations

import time
from pathlib import Path

import pygame

from game.scene_manager import SceneManager
from game.settings import load_config
from game.scenes.menu import MainMenuScene
from game.ui.crt_effects import CRTEffect
from game.user_settings import UserSettings, load_user_settings


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60


def _create_display(settings: UserSettings) -> tuple[pygame.Surface, tuple[int, int], bool]:
    if settings.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    window_size = screen.get_size()
    scale_to_window = window_size != (SCREEN_WIDTH, SCREEN_HEIGHT)
    return screen, window_size, scale_to_window


def run() -> None:
    pygame.init()

    config = load_config("config.json")

    settings_path = Path("user_settings.json")
    settings: UserSettings = load_user_settings(settings_path)
    try:
        settings_mtime = settings_path.stat().st_mtime
    except Exception:
        settings_mtime = 0.0
    settings_poll_at = 0.0

    screen, window_size, scale_to_window = _create_display(settings)
    pygame.display.set_caption("2D Runner Platform Game")

    frame = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    crt = CRTEffect(window_size if scale_to_window else (SCREEN_WIDTH, SCREEN_HEIGHT))
    scaled_frame = pygame.Surface(window_size) if scale_to_window else None

    clock = pygame.time.Clock()

    manager = SceneManager(
        MainMenuScene(
            config=config,
            screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
        )
    )

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # Hot-reload user settings (menu writes to disk). Keep polling light.
        now = time.time()
        if now >= settings_poll_at:
            settings_poll_at = now + 0.25
            try:
                new_mtime = settings_path.stat().st_mtime
                if new_mtime != settings_mtime:
                    settings_mtime = new_mtime
                    settings = load_user_settings(settings_path)
            except Exception:
                # Missing/locked file shouldn't break the game loop.
                pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            manager.scene.handle_event(event)

        if not running:
            break

        result = manager.scene.update(dt)
        running = manager.apply(result)

        manager.scene.draw(frame)

        if scale_to_window and scaled_frame is not None:
            pygame.transform.scale(frame, window_size, scaled_frame)
            source = scaled_frame
        else:
            source = frame

        if settings.crt_enabled and settings.crt_intensity > 0.0:
            crt.apply(source, screen, intensity=settings.crt_intensity, time_s=now)
        else:
            screen.blit(source, (0, 0))

        pygame.display.flip()

    pygame.quit()
