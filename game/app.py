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
LOGICAL_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)


def _create_display(settings: UserSettings) -> tuple[pygame.Surface, tuple[int, int]]:
    if settings.fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    window_size = screen.get_size()
    return screen, window_size


def _compute_viewport(window_size: tuple[int, int]) -> pygame.Rect:
    win_w, win_h = int(window_size[0]), int(window_size[1])
    base_w, base_h = LOGICAL_SIZE

    if win_w <= 0 or win_h <= 0:
        return pygame.Rect(0, 0, base_w, base_h)

    scale = min(win_w / base_w, win_h / base_h)
    view_w = max(1, int(round(base_w * scale)))
    view_h = max(1, int(round(base_h * scale)))
    view_x = (win_w - view_w) // 2
    view_y = (win_h - view_h) // 2
    return pygame.Rect(view_x, view_y, view_w, view_h)


def _build_present_targets(
    window_size: tuple[int, int],
) -> tuple[pygame.Rect, pygame.Surface | None, pygame.Surface, CRTEffect]:
    viewport = _compute_viewport(window_size)
    scaled_frame = pygame.Surface(viewport.size) if viewport.size != LOGICAL_SIZE else None
    present_frame = pygame.Surface(viewport.size)
    crt = CRTEffect(viewport.size)
    return viewport, scaled_frame, present_frame, crt


def _map_mouse_pos_to_logical(
    pos: tuple[int, int],
    viewport: pygame.Rect,
) -> tuple[int, int] | None:
    if viewport.width <= 0 or viewport.height <= 0:
        return None
    if not viewport.collidepoint(pos):
        return None

    px = pos[0] - viewport.x
    py = pos[1] - viewport.y

    lx = int((px * SCREEN_WIDTH) / viewport.width)
    ly = int((py * SCREEN_HEIGHT) / viewport.height)

    lx = max(0, min(SCREEN_WIDTH - 1, lx))
    ly = max(0, min(SCREEN_HEIGHT - 1, ly))
    return lx, ly


def _remap_mouse_event(event: pygame.event.Event, viewport: pygame.Rect) -> pygame.event.Event | None:
    if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        return event
    if "pos" not in event.dict:
        return event

    mapped_pos = _map_mouse_pos_to_logical(event.pos, viewport)
    if mapped_pos is None:
        return None

    payload = dict(event.dict)
    payload["pos"] = mapped_pos

    if event.type == pygame.MOUSEMOTION and "rel" in payload:
        rel_x, rel_y = payload["rel"]
        sx = SCREEN_WIDTH / max(1, viewport.width)
        sy = SCREEN_HEIGHT / max(1, viewport.height)
        payload["rel"] = (int(round(rel_x * sx)), int(round(rel_y * sy)))

    return pygame.event.Event(event.type, payload)


def _draw_fps_overlay(
    screen: pygame.Surface,
    font: pygame.font.Font,
    fps: float,
    *,
    high_contrast: bool,
    origin: tuple[int, int] = (10, 10),
) -> None:
    label = f"{fps:5.1f} FPS"
    text_color = (0, 0, 0) if high_contrast else (255, 255, 255)
    box_color = (255, 255, 255, 235) if high_contrast else (0, 0, 0, 165)
    border_color = (0, 0, 0, 110) if high_contrast else (255, 255, 255, 70)

    text = font.render(label, True, text_color)
    pad_x = 8
    pad_y = 4
    box = pygame.Surface((text.get_width() + pad_x * 2, text.get_height() + pad_y * 2), pygame.SRCALPHA)
    box.fill(box_color)
    pygame.draw.rect(box, border_color, box.get_rect(), width=1, border_radius=6)

    ox, oy = int(origin[0]), int(origin[1])
    screen.blit(box, (ox, oy))
    screen.blit(text, (ox + pad_x, oy + pad_y))


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

    screen, window_size = _create_display(settings)
    pygame.display.set_caption("2D Runner Platform Game")

    frame = pygame.Surface(LOGICAL_SIZE)
    viewport, scaled_frame, present_frame, crt = _build_present_targets(window_size)

    clock = pygame.time.Clock()
    fps_font = pygame.font.SysFont(None, 22)

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
                    updated = load_user_settings(settings_path)
                    if updated.fullscreen != settings.fullscreen:
                        settings = updated
                        screen, window_size = _create_display(settings)
                        pygame.display.set_caption("2D Runner Platform Game")
                        viewport, scaled_frame, present_frame, crt = _build_present_targets(window_size)
                    else:
                        settings = updated
            except Exception:
                # Missing/locked file shouldn't break the game loop.
                pass

        latest_window_size = screen.get_size()
        if latest_window_size != window_size:
            window_size = latest_window_size
            viewport, scaled_frame, present_frame, crt = _build_present_targets(window_size)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            mapped_event = _remap_mouse_event(event, viewport)
            if mapped_event is None:
                continue

            manager.scene.handle_event(mapped_event)

        if not running:
            break

        result = manager.scene.update(dt)
        running = manager.apply(result)

        manager.scene.draw(frame)

        if scaled_frame is not None:
            pygame.transform.smoothscale(frame, viewport.size, scaled_frame)
            source = scaled_frame
        else:
            source = frame

        screen.fill((0, 0, 0))

        if settings.crt_enabled and settings.crt_intensity > 0.0:
            crt.apply(source, present_frame, intensity=settings.crt_intensity, time_s=now)
        else:
            present_frame.blit(source, (0, 0))

        screen.blit(present_frame, viewport.topleft)

        if settings.show_fps:
            _draw_fps_overlay(
                screen,
                fps_font,
                clock.get_fps(),
                high_contrast=settings.high_contrast,
                origin=(viewport.left + 10, viewport.top + 10),
            )

        pygame.display.flip()

    pygame.quit()
