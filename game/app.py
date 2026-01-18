from __future__ import annotations

import pygame

from game.scene_manager import SceneManager
from game.settings import load_config
from game.scenes.menu import MainMenuScene


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60


def run() -> None:
    pygame.init()

    config = load_config("config.json")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("2D Runner Platform Game")

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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            manager.scene.handle_event(event)

        if not running:
            break

        result = manager.scene.update(dt)
        running = manager.apply(result)

        manager.scene.draw(screen)
        pygame.display.flip()

    pygame.quit()
