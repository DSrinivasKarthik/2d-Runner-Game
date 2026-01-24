from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import pygame


@dataclass
class TransitionState:
    from_surface: pygame.Surface
    to_surface: pygame.Surface
    origin: tuple[int, int]
    from_selected: int
    to_selected: int


class MenuTransition:
    """Pluggable transition between two already-rendered menu frames.

    The menu scene is responsible for rendering `from_surface` and `to_surface`.
    A transition only composites them onto the final screen.

    This separation makes it easy to swap transitions later.
    """

    def __init__(self, *, duration: float = 0.18):
        self.duration = float(duration)
        self.t = 0.0
        self._state: Optional[TransitionState] = None

    @property
    def active(self) -> bool:
        return self._state is not None

    def start(self, state: TransitionState) -> None:
        self._state = state
        self.t = 0.0

    def cancel(self) -> None:
        self._state = None
        self.t = 0.0

    def update(self, dt: float) -> None:
        if not self.active:
            return
        self.t += float(dt)
        if self.t >= self.duration:
            self.cancel()

    def _alpha(self) -> float:
        if self.duration <= 0.0:
            return 1.0
        x = max(0.0, min(1.0, self.t / self.duration))
        # smoothstep
        return x * x * (3.0 - 2.0 * x)

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError


class NoTransition(MenuTransition):
    def draw(self, screen: pygame.Surface) -> None:
        if not self.active or self._state is None:
            return
        screen.blit(self._state.to_surface, (0, 0))


class CrossfadeTransition(MenuTransition):
    """Simple, tasteful crossfade.

    Good default until a stronger art-direction arrives.
    """

    def __init__(self, *, duration: float = 0.16, dim_old: float = 0.12):
        super().__init__(duration=duration)
        self._dim_old = float(dim_old)

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active or self._state is None:
            return

        a = self._alpha()

        # Old page
        screen.blit(self._state.from_surface, (0, 0))
        if self._dim_old > 0.0:
            dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            dim.fill((0, 0, 0, int(255 * self._dim_old * a)))
            screen.blit(dim, (0, 0))

        # New page
        to_surf = self._state.to_surface.copy()
        to_surf.set_alpha(int(255 * a))
        screen.blit(to_surf, (0, 0))


class IrisTransition(MenuTransition):
    """Kept as an optional example transition (not enabled by default)."""

    def __init__(self, *, duration: float = 0.2, start_radius: float = 36.0):
        super().__init__(duration=duration)
        self._start_radius = float(start_radius)

    def draw(self, screen: pygame.Surface) -> None:
        if not self.active or self._state is None:
            return

        a = self._alpha()
        w, h = screen.get_size()

        screen.blit(self._state.from_surface, (0, 0))

        max_r = int(math.hypot(w, h))
        r = int(self._start_radius + a * (max_r - self._start_radius))

        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((0, 0, 0, 0))
        pygame.draw.circle(mask, (255, 255, 255, 255), self._state.origin, r)

        to_surf = self._state.to_surface.copy()
        to_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(to_surf, (0, 0))
