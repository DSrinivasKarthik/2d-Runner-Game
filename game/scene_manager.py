from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame


class Scene:
    """Base scene interface.

    Scenes are responsible for handling events, updating state, and drawing.
    They can request transitions via returning a SceneResult from update().
    """

    def handle_event(self, event: pygame.event.Event) -> None:
        return

    def update(self, dt: float) -> Optional["SceneResult"]:
        return None

    def draw(self, screen: pygame.Surface) -> None:
        return


@dataclass(frozen=True)
class SceneResult:
    action: str
    scene: Optional[Scene] = None

    @staticmethod
    def switch(scene: Scene) -> "SceneResult":
        return SceneResult(action="switch", scene=scene)

    @staticmethod
    def quit() -> "SceneResult":
        return SceneResult(action="quit")


class SceneManager:
    def __init__(self, initial_scene: Scene):
        self._scene: Scene = initial_scene

    @property
    def scene(self) -> Scene:
        return self._scene

    def apply(self, result: Optional[SceneResult]) -> bool:
        """Returns False when app should quit."""
        if result is None:
            return True
        if result.action == "switch" and result.scene is not None:
            self._scene = result.scene
            return True
        if result.action == "quit":
            return False
        return True
