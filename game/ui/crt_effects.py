from __future__ import annotations

import random
from dataclasses import dataclass

import pygame


@dataclass
class CRTParams:
    intensity: float = 0.65  # 0..1


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


class CRTEffect:
    """Lightweight CRT-ish post-processing for pygame.

    Designed to be dependency-free (no numpy) and fast enough for 800x600.
    """

    def __init__(self, size: tuple[int, int], *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._size = (int(size[0]), int(size[1]))

        self._scanlines = self._build_scanlines(self._size)
        self._vignette = self._build_vignette(self._size)
        self._phosphor = self._build_phosphor_mask(self._size)

        self._noise_tex = self._build_noise_texture((256, 256))

    def resize(self, size: tuple[int, int]) -> None:
        size = (int(size[0]), int(size[1]))
        if size == self._size:
            return
        self._size = size
        self._scanlines = self._build_scanlines(self._size)
        self._vignette = self._build_vignette(self._size)
        self._phosphor = self._build_phosphor_mask(self._size)

    def apply(
        self,
        source: pygame.Surface,
        target: pygame.Surface,
        *,
        intensity: float = 0.65,
        time_s: float = 0.0,
    ) -> None:
        """Blit `source` to `target` and apply CRT overlay effects."""

        intensity = _clamp01(intensity)
        w, h = target.get_size()
        if (w, h) != self._size:
            self.resize((w, h))

        # Slight horizontal jitter to mimic signal instability.
        jitter = 0
        if intensity > 0.05 and self._rng.random() < (0.035 * intensity):
            jitter = self._rng.choice([-1, 1])

        if jitter:
            target.fill((0, 0, 0))
            target.blit(source, (jitter, 0))
        else:
            target.blit(source, (0, 0))

        if intensity <= 0.0:
            return

        # Subtle global flicker / brightness pumping.
        flicker = (self._rng.random() - 0.5) * (0.06 * intensity)
        mult_f = 255 * max(0.88, min(1.08, 1.0 + flicker))
        mult = max(0, min(255, int(mult_f)))
        target.fill((mult, mult, mult), special_flags=pygame.BLEND_RGB_MULT)

        # Scanlines
        scan_alpha = int(95 * intensity)
        self._scanlines.set_alpha(scan_alpha)
        target.blit(self._scanlines, (0, 0))

        # Phosphor / subpixel hinting
        phosphor_alpha = int(35 * intensity)
        self._phosphor.set_alpha(phosphor_alpha)
        target.blit(self._phosphor, (0, 0))

        # Film grain / static (tile a pre-baked texture with random offset)
        noise_alpha = int(28 * intensity)
        self._noise_tex.set_alpha(noise_alpha)
        ox = self._rng.randrange(0, self._noise_tex.get_width())
        oy = self._rng.randrange(0, self._noise_tex.get_height())
        x0 = -ox
        y0 = -oy
        nw = self._noise_tex.get_width()
        nh = self._noise_tex.get_height()
        for x in (x0, x0 + nw):
            for y in (y0, y0 + nh):
                target.blit(self._noise_tex, (x, y), special_flags=pygame.BLEND_ADD)

        # Vignette (darken edges)
        vign_alpha = int(170 * intensity)
        self._vignette.set_alpha(vign_alpha)
        target.blit(self._vignette, (0, 0))

        # Intentionally no "rolling line"; it read as distracting in practice.

    def _build_scanlines(self, size: tuple[int, int]) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Dark every other line.
        for y in range(0, h, 2):
            pygame.draw.line(surf, (0, 0, 0, 120), (0, y), (w, y))

        # A touch of vertical banding.
        for x in range(0, w, 9):
            pygame.draw.line(surf, (0, 0, 0, 18), (x, 0), (x, h))

        return surf

    def _build_vignette(self, size: tuple[int, int]) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Layered outlines approximate a radial vignette without per-pixel work.
        steps = 24
        for i in range(steps):
            t = i / max(1, steps - 1)
            a = int((t * t) * 255)
            rect = pygame.Rect(0, 0, w, h).inflate(-i * 10, -i * 10)
            if rect.width <= 0 or rect.height <= 0:
                break
            pygame.draw.rect(surf, (0, 0, 0, a), rect, width=10)

        return surf

    def _build_phosphor_mask(self, size: tuple[int, int]) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Subtle RGB stripes. Keep alpha low; main intensity scales it.
        for x in range(0, w, 3):
            pygame.draw.line(surf, (255, 0, 0, 20), (x, 0), (x, h))
            if x + 1 < w:
                pygame.draw.line(surf, (0, 255, 0, 18), (x + 1, 0), (x + 1, h))
            if x + 2 < w:
                pygame.draw.line(surf, (0, 0, 255, 20), (x + 2, 0), (x + 2, h))

        return surf

    def _build_noise_texture(self, size: tuple[int, int]) -> pygame.Surface:
        w, h = size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        # Dots
        for _ in range(2800):
            x = self._rng.randrange(0, w)
            y = self._rng.randrange(0, h)
            v = self._rng.randrange(30, 180)
            a = self._rng.randrange(10, 70)
            surf.set_at((x, y), (v, v, v, a))

        # A few micro streaks
        for _ in range(120):
            x = self._rng.randrange(0, w)
            y = self._rng.randrange(0, h)
            length = self._rng.randrange(2, 10)
            v = self._rng.randrange(80, 220)
            a = self._rng.randrange(8, 35)
            pygame.draw.line(surf, (v, v, v, a), (x, y), (min(w - 1, x + length), y))

        return surf
