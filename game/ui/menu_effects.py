from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame


@dataclass
class DriftParticle:
    x: float
    y: float
    speed: float
    radius: int
    alpha: int


class StarDriftBackground:
    """Lightweight animated backdrop: drifting particles + subtle parallax blocks.

    Designed to look charming without needing external assets.
    """

    def __init__(self, screen_size: tuple[int, int], *, seed: int | None = None):
        self._w, self._h = screen_size
        self._rng = random.Random(seed)

        self._t = 0.0
        self._particles: list[DriftParticle] = [self._spawn_particle() for _ in range(70)]

        # Parallax silhouettes (like distant platforms / city blocks)
        self._blocks: list[pygame.Rect] = []
        x = 0
        while x < self._w + 200:
            bw = self._rng.randint(80, 190)
            bh = self._rng.randint(18, 44)
            y = self._h - self._rng.randint(60, 120)
            self._blocks.append(pygame.Rect(x, y, bw, bh))
            x += bw + self._rng.randint(20, 70)

        self._runner_x = float(self._rng.randint(50, 200))
        self._runner_y = float(self._h - 140)
        self._runner_vy = 0.0
        self._runner_phase = 0.0

    def resize(self, screen_size: tuple[int, int]) -> None:
        self._w, self._h = screen_size

    def _spawn_particle(self) -> DriftParticle:
        return DriftParticle(
            x=float(self._rng.uniform(0, self._w)),
            y=float(self._rng.uniform(0, self._h)),
            speed=float(self._rng.uniform(12.0, 55.0)),
            radius=int(self._rng.choice([1, 1, 2, 2, 3])),
            alpha=int(self._rng.uniform(60, 140)),
        )

    def update(self, dt: float, *, reduce_motion: bool = False) -> None:
        dt = float(dt)
        self._t += dt

        if reduce_motion:
            return

        for p in self._particles:
            p.x -= p.speed * dt
            p.y += math.sin((self._t * 0.8) + (p.alpha * 0.01)) * 10.0 * dt
            if p.x < -20:
                p.x = float(self._w + 20)
                p.y = float(self._rng.uniform(0, self._h))

        # Blocks scroll slowly
        for r in self._blocks:
            r.x -= int(round(22 * dt))
        while self._blocks and self._blocks[0].right < -100:
            self._blocks.pop(0)
        if self._blocks:
            while self._blocks[-1].right < self._w + 200:
                last = self._blocks[-1]
                bw = self._rng.randint(80, 190)
                bh = self._rng.randint(18, 44)
                y = self._h - self._rng.randint(60, 120)
                nx = last.right + self._rng.randint(20, 70)
                self._blocks.append(pygame.Rect(nx, y, bw, bh))

        # Tiny runner hop (purely for charm)
        gravity = 900.0
        if self._runner_y >= self._h - 140 and self._rng.random() < 0.012:
            self._runner_vy = -420.0
        self._runner_vy += gravity * dt
        self._runner_y += self._runner_vy * dt
        if self._runner_y >= self._h - 140:
            self._runner_y = float(self._h - 140)
            self._runner_vy = 0.0

        self._runner_x += 120.0 * dt
        if self._runner_x > self._w + 60:
            self._runner_x = -60.0

        self._runner_phase += dt * 10.0

    def draw(self, screen: pygame.Surface, *, base_color: tuple[int, int, int], accent: tuple[int, int, int], high_contrast: bool = False) -> None:
        screen.fill(base_color)

        # Soft vignette
        vignette = pygame.Surface((self._w, self._h), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 35 if not high_contrast else 60), vignette.get_rect(), width=18)
        screen.blit(vignette, (0, 0))

        # Particles
        for p in self._particles:
            c = (*accent, p.alpha if not high_contrast else min(220, p.alpha + 80))
            pygame.draw.circle(screen, c, (int(p.x), int(p.y)), p.radius)

        # Parallax blocks (distant ground)
        block_color = (20, 20, 20) if high_contrast else (0, 0, 0)
        for r in self._blocks:
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            s.fill((*block_color, 40 if not high_contrast else 80))
            screen.blit(s, r.topleft)

        # Tiny runner silhouette
        rx = int(self._runner_x)
        ry = int(self._runner_y)
        body = pygame.Rect(rx, ry, 18, 26)
        head = pygame.Rect(rx + 12, ry - 10, 10, 10)
        leg_offset = int(4 * math.sin(self._runner_phase))
        leg1 = pygame.Rect(rx + 2, ry + 24, 6, 10 + leg_offset)
        leg2 = pygame.Rect(rx + 10, ry + 24, 6, 10 - leg_offset)

        runner_color = (0, 0, 0) if high_contrast else (15, 15, 15)
        pygame.draw.rect(screen, runner_color, body, border_radius=4)
        pygame.draw.rect(screen, runner_color, head, border_radius=3)
        pygame.draw.rect(screen, runner_color, leg1, border_radius=3)
        pygame.draw.rect(screen, runner_color, leg2, border_radius=3)


def wobble_text(
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    *,
    t: float,
    strength: float = 2.0,
) -> pygame.Surface:
    # Render per-letter with tiny vertical wobble for charm.
    glyphs: list[pygame.Surface] = []
    offsets: list[int] = []

    for i, ch in enumerate(text):
        surf = font.render(ch, True, color)
        glyphs.append(surf)
        offsets.append(int(round(math.sin(t * 2.2 + i * 0.7) * strength)))

    w = sum(g.get_width() for g in glyphs)
    h = max(g.get_height() for g in glyphs) + int(strength * 2) + 6

    out = pygame.Surface((w, h), pygame.SRCALPHA)
    x = 0
    for g, dy in zip(glyphs, offsets):
        out.blit(g, (x, 3 + dy))
        x += g.get_width()

    return out
