from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Sequence

import pygame


MenuCallback = Callable[[], None]


@dataclass
class MenuTheme:
    bg_color: tuple[int, int, int]
    fg_color: tuple[int, int, int]
    muted_color: tuple[int, int, int]
    accent_color: tuple[int, int, int]
    danger_color: tuple[int, int, int]

    title_font: pygame.font.Font
    item_font: pygame.font.Font
    small_font: pygame.font.Font

    panel_alpha: int = 200


class MenuItem:
    def __init__(
        self,
        label: str,
        *,
        hint: str = "",
        enabled: bool = True,
        locked: bool = False,
        badge: str = "",
    ):
        self.label = label
        self.hint = hint
        self.enabled = enabled
        self.locked = locked
        self.badge = badge

    def value_text(self) -> str:
        return ""

    def on_left(self) -> None:
        return

    def on_right(self) -> None:
        return

    def on_activate(self) -> None:
        return


class ButtonItem(MenuItem):
    def __init__(
        self,
        label: str,
        on_activate: MenuCallback,
        *,
        hint: str = "",
        enabled: bool = True,
        locked: bool = False,
        badge: str = "",
    ):
        super().__init__(label, hint=hint, enabled=enabled, locked=locked, badge=badge)
        self._cb = on_activate

    def on_activate(self) -> None:
        if self.enabled:
            self._cb()


class ToggleItem(MenuItem):
    def __init__(
        self,
        label: str,
        get_value: Callable[[], bool],
        set_value: Callable[[bool], None],
        *,
        hint: str = "",
        enabled: bool = True,
    ):
        super().__init__(label, hint=hint, enabled=enabled)
        self._get = get_value
        self._set = set_value

    def value_text(self) -> str:
        return "On" if self._get() else "Off"

    def on_left(self) -> None:
        if self.enabled:
            self._set(False)

    def on_right(self) -> None:
        if self.enabled:
            self._set(True)

    def on_activate(self) -> None:
        if self.enabled:
            self._set(not self._get())


class SliderItem(MenuItem):
    def __init__(
        self,
        label: str,
        get_value: Callable[[], float],
        set_value: Callable[[float], None],
        *,
        min_value: float = 0.0,
        max_value: float = 1.0,
        step: float = 0.05,
        fmt: Callable[[float], str] | None = None,
        hint: str = "",
        enabled: bool = True,
    ):
        super().__init__(label, hint=hint, enabled=enabled)
        self._get = get_value
        self._set = set_value
        self._min = float(min_value)
        self._max = float(max_value)
        self._step = float(step)
        self._fmt = fmt

    def value_text(self) -> str:
        v = float(self._get())
        if self._fmt is not None:
            return self._fmt(v)
        return f"{int(round(v * 100))}%"

    def _nudge(self, direction: float) -> None:
        v = float(self._get())
        v += direction * self._step
        v = max(self._min, min(self._max, v))
        self._set(v)

    def on_left(self) -> None:
        if self.enabled:
            self._nudge(-1.0)

    def on_right(self) -> None:
        if self.enabled:
            self._nudge(+1.0)


@dataclass
class MenuPage:
    title: str
    items: Sequence[MenuItem]
    subtitle: str = ""
    footer: str = ""


class MenuStack:
    def __init__(self, root: MenuPage):
        self._stack: List[MenuPage] = [root]

    @property
    def page(self) -> MenuPage:
        return self._stack[-1]

    def can_pop(self) -> bool:
        return len(self._stack) > 1

    def push(self, page: MenuPage) -> None:
        self._stack.append(page)

    def pop(self) -> None:
        if self.can_pop():
            self._stack.pop()


@dataclass
class MenuLayout:
    panel_rect: pygame.Rect
    title_pos: tuple[int, int]
    subtitle_pos: tuple[int, int]
    footer_pos: tuple[int, int]
    item_start: tuple[int, int]
    item_gap: int
    item_value_x: int


class MenuView:
    def __init__(
        self,
        theme: MenuTheme,
        screen_size: tuple[int, int],
        *,
        panel_width: int = 520,
        panel_padding: int = 28,
    ):
        self._theme = theme
        self._screen_w, self._screen_h = screen_size

        self._panel_padding = int(panel_padding)

        panel_w = min(panel_width, self._screen_w - 80)
        panel_h = min(460, self._screen_h - 80)
        panel_x = (self._screen_w - panel_w) // 2
        panel_y = (self._screen_h - panel_h) // 2

        self._layout = MenuLayout(
            panel_rect=pygame.Rect(panel_x, panel_y, panel_w, panel_h),
            title_pos=(panel_x + panel_padding, panel_y + panel_padding),
            subtitle_pos=(panel_x + panel_padding, panel_y + panel_padding + 54),
            item_start=(panel_x + panel_padding, panel_y + panel_padding + 110),
            item_gap=52,
            item_value_x=panel_x + panel_w - panel_padding,
            footer_pos=(panel_x + panel_padding, panel_y + panel_h - panel_padding - 22),
        )

        self._item_rects: List[pygame.Rect] = []
        self._computed_item_gap: int = self._layout.item_gap
        self._row_h: int = max(36, int(self._theme.item_font.get_linesize() + 10))
        self._scroll_y: int = 0
        self._offset: tuple[int, int] = (0, 0)

    def _ellipsize(self, font: pygame.font.Font, text: str, max_w: int) -> str:
        if max_w <= 0:
            return ""
        if not text:
            return ""
        if font.size(text)[0] <= max_w:
            return text

        ell = "…"
        ell_w = font.size(ell)[0]
        if ell_w >= max_w:
            return ""

        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            candidate = text[:mid] + ell
            if font.size(candidate)[0] <= max_w:
                lo = mid + 1
            else:
                hi = mid
        cut = max(0, lo - 1)
        return text[:cut] + ell

    def _compute_item_gap(self, n_items: int) -> int:
        # Font-driven row size.
        self._row_h = max(36, int(self._theme.item_font.get_linesize() + 10))

        if n_items <= 1:
            return 0

        start_y = self._layout.item_start[1]
        footer_y = self._layout.footer_pos[1]

        # List area height (leave breathing room above footer).
        available = max(0, (footer_y - 14) - start_y)

        default_gap = 14
        min_gap = 6
        needed_default = n_items * self._row_h + (n_items - 1) * default_gap
        if needed_default <= available:
            return default_gap

        spare = available - n_items * self._row_h
        gap = spare // max(1, (n_items - 1))
        return int(max(min_gap, min(default_gap, gap)))

    @property
    def item_rects(self) -> Sequence[pygame.Rect]:
        return self._item_rects

    def compute_item_rects(
        self,
        page: MenuPage,
        *,
        selected_index: int = 0,
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        self._item_rects = []
        self._offset = (int(offset[0]), int(offset[1]))
        self._computed_item_gap = self._compute_item_gap(len(page.items))

        pad = int(self._layout.title_pos[0] - self._layout.panel_rect.x)
        inner_left = self._layout.panel_rect.x + pad + self._offset[0]
        inner_w = self._layout.panel_rect.w - pad * 2

        list_top = self._layout.item_start[1] + self._offset[1]
        list_bottom = self._layout.footer_pos[1] - 14 + self._offset[1]
        list_h = max(0, list_bottom - list_top)

        n = len(page.items)
        if n <= 0:
            self._scroll_y = 0
            return

        content_h = n * self._row_h + (n - 1) * self._computed_item_gap
        max_scroll = max(0, content_h - list_h)

        idx = max(0, min(int(selected_index), n - 1))
        sel_center = idx * (self._row_h + self._computed_item_gap) + self._row_h // 2
        self._scroll_y = int(max(0, min(max_scroll, sel_center - list_h * 0.5)))

        for i in range(n):
            y = list_top + i * (self._row_h + self._computed_item_gap) - self._scroll_y
            self._item_rects.append(pygame.Rect(inner_left, y, inner_w, self._row_h))

    def _draw_lock_icon(self, screen: pygame.Surface, x: int, y: int, *, color: tuple[int, int, int]) -> None:
        # Simple vector lock icon: body + shackle.
        body = pygame.Rect(x, y + 8, 16, 14)
        pygame.draw.rect(screen, color, body, width=2, border_radius=3)
        pygame.draw.arc(screen, color, pygame.Rect(x + 2, y, 12, 14), 0, 3.14159, width=2)

    def draw(
        self,
        screen: pygame.Surface,
        *,
        page: MenuPage,
        selected_index: int,
        pulse: float,
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        self._offset = (int(offset[0]), int(offset[1]))

        # Panel
        panel = pygame.Surface(self._layout.panel_rect.size, pygame.SRCALPHA)
        panel.fill((255, 255, 255, self._theme.panel_alpha))
        pygame.draw.rect(panel, (0, 0, 0, 50), panel.get_rect(), width=2, border_radius=14)
        panel_pos = (self._layout.panel_rect.x + self._offset[0], self._layout.panel_rect.y + self._offset[1])
        screen.blit(panel, panel_pos)

        # Title & subtitle
        title = self._theme.title_font.render(page.title, True, self._theme.fg_color)
        screen.blit(title, (self._layout.title_pos[0] + self._offset[0], self._layout.title_pos[1] + self._offset[1]))

        if page.subtitle:
            subtitle = self._theme.small_font.render(page.subtitle, True, self._theme.muted_color)
            screen.blit(
                subtitle,
                (
                    self._layout.subtitle_pos[0] + self._offset[0],
                    self._layout.subtitle_pos[1] + self._offset[1],
                ),
            )

        # Items
        self.compute_item_rects(page, selected_index=selected_index, offset=self._offset)

        pad = int(self._layout.title_pos[0] - self._layout.panel_rect.x)
        list_left = self._layout.panel_rect.x + pad + self._offset[0]
        list_w = self._layout.panel_rect.w - pad * 2
        list_top = self._layout.item_start[1] + self._offset[1]
        list_bottom = self._layout.footer_pos[1] - 14 + self._offset[1]
        list_rect = pygame.Rect(list_left, list_top, list_w, max(0, list_bottom - list_top))

        prev_clip = screen.get_clip()
        screen.set_clip(list_rect)
        for i, item in enumerate(page.items):
            is_selected = i == selected_index
            enabled = item.enabled

            label_color = self._theme.fg_color if enabled else self._theme.muted_color
            value_color = self._theme.muted_color if enabled else (140, 140, 140)

            if item.locked:
                label_color = self._theme.muted_color
                value_color = self._theme.muted_color

            if is_selected:
                # Selection highlight
                r = self._item_rects[i]
                highlight = pygame.Surface(r.size, pygame.SRCALPHA)
                highlight.fill((*self._theme.accent_color, int(30 + 25 * pulse)))
                screen.blit(highlight, r.topleft)
                pygame.draw.rect(screen, (*self._theme.accent_color, 90), r, width=2, border_radius=10)

                # Little marker
                marker_x = r.x + 12
                marker_y = r.centery + int(1 * pulse)
                pygame.draw.circle(screen, self._theme.accent_color, (marker_x, marker_y), 5)

            r = self._item_rects[i]

            right_x = self._layout.item_value_x + self._offset[0]
            label_x = r.x + 20
            label_y = r.y + (r.h - self._theme.item_font.get_height()) // 2

            # Reserve space on the right for value or badge so the label can't overlap.
            reserved_right = 0
            value = item.value_text() or ""
            value_surf = None
            if value:
                value_fit = self._ellipsize(self._theme.item_font, value, max_w=int(r.w * 0.35))
                value_surf = self._theme.item_font.render(value_fit, True, value_color)
                reserved_right = max(reserved_right, value_surf.get_width() + 8)

            badge = item.badge
            if item.locked and not badge:
                badge = "Coming soon"

            badge_box = None
            badge_surf = None
            if item.locked or badge:
                badge_text = badge
                badge_surf = self._theme.small_font.render(badge_text, True, self._theme.fg_color)
                pad_x = 10
                pad_y = 5
                bw = badge_surf.get_width() + pad_x * 2
                bh = badge_surf.get_height() + pad_y * 2
                bx = right_x - bw
                by = r.y + (r.h - bh) // 2
                badge_box = pygame.Rect(bx, by, bw, bh)
                reserved_right = max(reserved_right, bw + 12 + (24 if item.locked else 0))

            max_label_w = max(0, (right_x - reserved_right) - label_x)
            label_fit = self._ellipsize(self._theme.item_font, item.label, max_w=max_label_w)
            label = self._theme.item_font.render(label_fit, True, label_color)
            screen.blit(label, (label_x, label_y))

            if value_surf is not None and badge_box is None:
                vx = right_x - value_surf.get_width()
                vy = r.y + (r.h - value_surf.get_height()) // 2
                screen.blit(value_surf, (vx, vy))

            # Locked + badge treatment
            if badge_box is not None and badge_surf is not None:
                bsurf = pygame.Surface(badge_box.size, pygame.SRCALPHA)
                base = self._theme.accent_color if not item.locked else (90, 90, 90)
                alpha = 70 if not is_selected else int(90 + 30 * pulse)
                bsurf.fill((*base, alpha))
                pygame.draw.rect(bsurf, (0, 0, 0, 60), bsurf.get_rect(), width=2, border_radius=999)
                screen.blit(bsurf, badge_box.topleft)
                pad_x = 10
                pad_y = 5
                screen.blit(badge_surf, (badge_box.x + pad_x, badge_box.y + pad_y))
                if item.locked:
                    self._draw_lock_icon(screen, badge_box.x - 24, badge_box.y, color=self._theme.muted_color)

        screen.set_clip(prev_clip)

        # Footer
        footer_text = page.footer
        if footer_text:
            pad = int(self._layout.title_pos[0] - self._layout.panel_rect.x)
            max_footer_w = max(0, self._layout.panel_rect.w - pad * 2)
            footer_fit = self._ellipsize(self._theme.small_font, footer_text, max_w=max_footer_w)
            footer = self._theme.small_font.render(footer_fit, True, self._theme.muted_color)
            screen.blit(
                footer,
                (
                    self._layout.footer_pos[0] + self._offset[0],
                    self._layout.footer_pos[1] + self._offset[1],
                ),
            )


class MenuInput:
    def __init__(self, stack: MenuStack):
        self._stack = stack
        self.selected_index = 0
        self._mouse_down = False

    def _clamp_index(self) -> None:
        n = len(self._stack.page.items)
        if n <= 0:
            self.selected_index = 0
        else:
            self.selected_index = max(0, min(self.selected_index, n - 1))

    def move(self, delta: int) -> None:
        items = self._stack.page.items
        if not items:
            return

        # Allow focusing disabled items too, so players can discover "Coming soon"
        # entries and read their hints (activation still no-ops when disabled).
        n = len(items)
        self.selected_index = (self.selected_index + delta) % n

    def back(self) -> None:
        if self._stack.can_pop():
            self._stack.pop()
            self.selected_index = 0

    def handle_event(
        self,
        event: pygame.event.Event,
        *,
        view: MenuView,
    ) -> None:
        page = self._stack.page
        self._clamp_index()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move(+1)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                page.items[self.selected_index].on_left()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                page.items[self.selected_index].on_right()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                page.items[self.selected_index].on_activate()
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.back()

        elif event.type == pygame.MOUSEMOTION:
            pos = event.pos
            for i, r in enumerate(view.item_rects):
                if r.collidepoint(pos):
                    self.selected_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_down = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_down = self._mouse_down
            self._mouse_down = False
            if not was_down:
                return
            pos = event.pos
            for i, r in enumerate(view.item_rects):
                if r.collidepoint(pos) and page.items[i].enabled:
                    self.selected_index = i
                    page.items[i].on_activate()
                    break
