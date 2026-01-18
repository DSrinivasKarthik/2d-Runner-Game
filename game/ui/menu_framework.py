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
    def __init__(self, label: str, *, hint: str = "", enabled: bool = True):
        self.label = label
        self.hint = hint
        self.enabled = enabled

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
    ):
        super().__init__(label, hint=hint, enabled=enabled)
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

    def _compute_item_gap(self, n_items: int) -> int:
        # Keep items from overlapping the footer by compressing spacing when needed.
        # This makes pages with many items (e.g., Options) readable without resizing.
        if n_items <= 1:
            return self._layout.item_gap

        start_y = self._layout.item_start[1]
        footer_y = self._layout.footer_pos[1]
        item_height = 44
        # Space available for the list area (leave a little breathing room).
        available = max(0, (footer_y - 10) - start_y)
        # Total height is item_height + (n-1)*gap.
        max_gap = (available - item_height) // max(1, (n_items - 1))
        # Clamp: don't get too tight, don't exceed the designed gap.
        return int(max(38, min(self._layout.item_gap, max_gap)))

    @property
    def item_rects(self) -> Sequence[pygame.Rect]:
        return self._item_rects

    def compute_item_rects(self, page: MenuPage) -> None:
        self._item_rects = []
        self._computed_item_gap = self._compute_item_gap(len(page.items))
        x, y = self._layout.item_start
        for _ in page.items:
            self._item_rects.append(pygame.Rect(x - 8, y - 6, self._layout.panel_rect.w - 40, 44))
            y += self._computed_item_gap

    def draw(
        self,
        screen: pygame.Surface,
        *,
        page: MenuPage,
        selected_index: int,
        pulse: float,
    ) -> None:
        # Panel
        panel = pygame.Surface(self._layout.panel_rect.size, pygame.SRCALPHA)
        panel.fill((255, 255, 255, self._theme.panel_alpha))
        pygame.draw.rect(panel, (0, 0, 0, 50), panel.get_rect(), width=2, border_radius=14)
        screen.blit(panel, self._layout.panel_rect.topleft)

        # Title & subtitle
        title = self._theme.title_font.render(page.title, True, self._theme.fg_color)
        screen.blit(title, self._layout.title_pos)

        if page.subtitle:
            subtitle = self._theme.small_font.render(page.subtitle, True, self._theme.muted_color)
            screen.blit(subtitle, self._layout.subtitle_pos)

        # Items
        self.compute_item_rects(page)
        x, y = self._layout.item_start
        for i, item in enumerate(page.items):
            is_selected = i == selected_index
            enabled = item.enabled

            label_color = self._theme.fg_color if enabled else self._theme.muted_color
            value_color = self._theme.muted_color if enabled else (140, 140, 140)

            if is_selected:
                # Selection highlight
                r = self._item_rects[i]
                highlight = pygame.Surface(r.size, pygame.SRCALPHA)
                highlight.fill((*self._theme.accent_color, int(30 + 25 * pulse)))
                screen.blit(highlight, r.topleft)
                pygame.draw.rect(screen, (*self._theme.accent_color, 90), r, width=2, border_radius=10)

                # Little marker
                marker_x = x - 18
                marker_y = y + 14 + int(2 * pulse)
                pygame.draw.circle(screen, self._theme.accent_color, (marker_x, marker_y), 5)

            label = self._theme.item_font.render(item.label, True, label_color)
            screen.blit(label, (x, y))

            value = item.value_text()
            if value:
                value_surf = self._theme.item_font.render(value, True, value_color)
                vx = self._layout.item_value_x - value_surf.get_width()
                screen.blit(value_surf, (vx, y))

            y += self._computed_item_gap

        # Footer
        footer_text = page.footer
        if footer_text:
            footer = self._theme.small_font.render(footer_text, True, self._theme.muted_color)
            screen.blit(footer, self._layout.footer_pos)


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
