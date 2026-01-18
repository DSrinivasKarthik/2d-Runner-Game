from __future__ import annotations

from dataclasses import dataclass

import pygame

from game.scene_manager import Scene, SceneResult
from game.settings import GameConfig
from game.scenes.gameplay import GameplayScene


@dataclass
class MainMenuScene(Scene):
    config: GameConfig
    screen_size: tuple[int, int]

    def __post_init__(self) -> None:
        self._selected = 0
        self._items = ["Start", "Quit"]
        self._font = pygame.font.SysFont(None, 48)
        self._small = pygame.font.SysFont(None, 28)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected = (self._selected - 1) % len(self._items)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected = (self._selected + 1) % len(self._items)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            choice = self._items[self._selected]
            if choice == "Start":
                self._pending = SceneResult.switch(
                    GameplayScene(config=self.config, screen_size=self.screen_size)
                )
            elif choice == "Quit":
                self._pending = SceneResult.quit()

    def update(self, dt: float):
        pending = getattr(self, "_pending", None)
        self._pending = None
        return pending

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self.config.background_color)

        title = self._font.render("2D Runner", True, (0, 0, 0))
        subtitle = self._small.render("Up/Down + Enter", True, (0, 0, 0))

        screen.blit(title, (40, 40))
        screen.blit(subtitle, (42, 90))

        start_y = 180
        for i, label in enumerate(self._items):
            is_selected = i == self._selected
            color = (20, 20, 20) if not is_selected else (0, 120, 255)
            text = self._font.render(label, True, color)
            screen.blit(text, (60, start_y + i * 70))
