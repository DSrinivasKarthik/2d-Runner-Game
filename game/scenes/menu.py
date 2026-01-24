from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

import pygame

from game.scene_manager import Scene, SceneResult
from game.settings import GameConfig
from game.scenes.gameplay import GameplayScene
from game.ui.menu_effects import StarDriftBackground, wobble_text
from game.ui.menu_framework import (
    ButtonItem,
    MenuInput,
    MenuPage,
    MenuStack,
    MenuTheme,
    MenuView,
    SliderItem,
    ToggleItem,
)
from game.ui.menu_transitions import CrossfadeTransition, TransitionState
from game.user_settings import UserSettings, load_user_settings, save_user_settings


@dataclass
class MainMenuScene(Scene):
    config: GameConfig
    screen_size: tuple[int, int]

    def __post_init__(self) -> None:
        self._screen_w, self._screen_h = self.screen_size

        self._t = 0.0
        self._pulse = 0.0

        # Persisted user settings for menu UX (and future use).
        self._settings: UserSettings = load_user_settings("user_settings.json")

        # Charm + ambience
        seed = int(time.time()) ^ (self._screen_w << 8) ^ (self._screen_h << 16)
        self._bg = StarDriftBackground(self.screen_size, seed=seed)
        self._toast: str | None = None
        self._toast_timer = 0.0
        self._toast_duration = 1.6
        self._toast_fade_in = 0.08  # Fast fade-in
        self._toast_fade_out = 0.12  # Fast fade-out when replaced
        self._toast_alpha = 0.0  # 0.0 to 1.0
        self._toast_scale = 1.0  # Scale animation

        # Dynamic Background Reactivity: track selection/hover to drive subtle pulses.
        self._last_focus_key: tuple[int, int] = (0, -1)  # (page_id, selected_index)

        self._shake_timer = 0.0
        self._shake_strength = 0.0

        # Credits scroll state
        self._credits_scroll = 0.0
        self._credits_items: list[tuple[str, str, str]] = []  # (role, name, type)
        self._credits_easter_eggs: dict[str, int] = {}  # name -> click count

        # Page transitions (pluggable). Keep this simple for now.
        self._transition = CrossfadeTransition(duration=0.16)

        # Fade in / out
        self._fade_alpha = 255
        self._fade_dir = -1  # -1 fading in, +1 fading out, 0 none
        self._fade_target: SceneResult | None = None

        # Fonts & theme
        title_font = pygame.font.SysFont(None, 72)
        item_font = pygame.font.SysFont(None, 42)
        small_font = pygame.font.SysFont(None, 24)

        self._theme = MenuTheme(
            bg_color=self.config.background_color,
            fg_color=(20, 20, 20),
            muted_color=(70, 70, 70),
            accent_color=(0, 120, 255),
            danger_color=(200, 40, 40),
            title_font=title_font,
            item_font=item_font,
            small_font=small_font,
            panel_alpha=210,
        )

        self._tagline = self._pick_tagline()
        self._konami: list[int] = []
        self._secret_unlocked = False

        self._stack = MenuStack(self._make_main_page())
        self._view = MenuView(self._theme, self.screen_size)
        self._input = MenuInput(self._stack)

        self._pending: SceneResult | None = None

    def _pick_tagline(self) -> str:
        # Inspiration notes (not copying): the best indie menus feel like a warm
        # moment of calm: subtle motion, readable UI, a little whimsy.
        taglines = [
            "Press Enter. Stay awhile.",
            "A tiny run. A big heart.",
            "Made for late-night smiles.",
            "Run. Jump. Breathe.",
            "Your adventure starts… gently.",
            "Small game. Big feelings.",
        ]
        # Deterministic-ish: stable per day to feel intentional.
        day = int(time.time() // (24 * 60 * 60))
        return taglines[day % len(taglines)]

    def _toast_message(self, msg: str, *, seconds: float = 1.6) -> None:
        if not msg:
            return

        # Instant replace: new message immediately triggers fade-out of old and starts new.
        self._toast = msg
        self._toast_duration = max(0.5, float(seconds))
        self._toast_timer = self._toast_fade_in + self._toast_duration + self._toast_fade_out
        self._toast_alpha = 0.0  # Start faded out, will fade in
        self._toast_scale = 0.92  # Start slightly smaller

    def _thunk(self, msg: str = "Locked — coming soon") -> None:
        self._toast_message(msg)
        self._shake_timer = 0.18
        self._shake_strength = 7.0

        # Stronger background poke for locked items.
        try:
            pos = self._selected_item_center(self._stack.page, self._input.selected_index)
            self._bg.poke(pos, strength=1.35, seconds=0.22)
        except Exception:
            pass

    def _current_focus_pos(self) -> tuple[int, int]:
        # Special case: interactive credits scroll influence
        if self._stack.page.title == "Credits":
            return (self._screen_w // 2, int(self._screen_h * 0.4))

        # Default focus is current selection.
        page = self._stack.page
        sel = int(self._input.selected_index)
        focus = self._selected_item_center(page, sel)

        # If mouse is over an item, use hover as focus.
        if pygame.mouse.get_focused() and page.items:
            mp = pygame.mouse.get_pos()
            self._view.compute_item_rects(page, offset=self._menu_offset())
            for r in self._view.item_rects:
                if r.collidepoint(mp):
                    focus = r.center
                    break

        return (int(focus[0]), int(focus[1]))

    def _update_footer(self, page: MenuPage, selected_index: int, *, can_pop: bool) -> None:
        hint = ""
        if page.items:
            idx = max(0, min(int(selected_index), len(page.items) - 1))
            hint = getattr(page.items[idx], "hint", "") or ""
        back = "Esc: Back" if can_pop else ""
        controls = "Mouse/Keys" if pygame.mouse.get_focused() else "Keys"
        page.footer = "  •  ".join([s for s in [hint, back, controls] if s])

    def _begin_transition(
        self,
        *,
        from_page: MenuPage,
        to_page: MenuPage,
        origin: tuple[int, int],
        from_selected: int,
        to_selected: int,
        from_can_pop: bool,
        to_can_pop: bool,
    ) -> None:
        if self._settings.reduce_motion:
            self._transition.cancel()
            return

        self._update_footer(from_page, from_selected, can_pop=from_can_pop)
        self._update_footer(to_page, to_selected, can_pop=to_can_pop)

        # Render both pages to surfaces and let the transition composite them.
        from_surf = pygame.Surface((self._screen_w, self._screen_h), pygame.SRCALPHA)
        to_surf = pygame.Surface((self._screen_w, self._screen_h), pygame.SRCALPHA)

        self._view.draw(from_surf, page=from_page, selected_index=from_selected, pulse=self._pulse, offset=(0, 0))
        self._view.draw(to_surf, page=to_page, selected_index=to_selected, pulse=self._pulse, offset=(0, 0))

        self._transition.start(
            TransitionState(
                from_surface=from_surf,
                to_surface=to_surf,
                origin=(int(origin[0]), int(origin[1])),
                from_selected=int(from_selected),
                to_selected=int(to_selected),
            )
        )

    def _selected_item_center(self, page: MenuPage, selected_index: int) -> tuple[int, int]:
        if not page.items:
            return (self._screen_w // 2, self._screen_h // 2)
        self._view.compute_item_rects(page, offset=(0, 0))
        idx = max(0, min(int(selected_index), len(self._view.item_rects) - 1))
        return self._view.item_rects[idx].center

    def _push_page(self, page: MenuPage, *, default_selected: int = 0) -> None:
        from_page = self._stack.page
        from_selected = self._input.selected_index
        from_can_pop = self._stack.can_pop()
        origin = self._selected_item_center(from_page, from_selected)

        # Push immediately so stack.page becomes the new page; transition draws from->to.
        self._stack.push(page)
        self._input.selected_index = int(default_selected)
        self._begin_transition(
            from_page=from_page,
            to_page=page,
            origin=origin,
            from_selected=from_selected,
            to_selected=self._input.selected_index,
            from_can_pop=from_can_pop,
            to_can_pop=True,
        )

    def _pop_page(self) -> None:
        if not self._stack.can_pop():
            return

        from_page = self._stack.page
        from_selected = self._input.selected_index
        origin = self._selected_item_center(from_page, from_selected)

        self._stack.pop()
        to_page = self._stack.page
        self._input.selected_index = 0
        self._begin_transition(
            from_page=from_page,
            to_page=to_page,
            origin=origin,
            from_selected=from_selected,
            to_selected=self._input.selected_index,
            from_can_pop=True,
            to_can_pop=self._stack.can_pop(),
        )

    def _menu_offset(self) -> tuple[int, int]:
        if self._settings.reduce_motion:
            return (0, 0)
        if self._shake_timer <= 0.0:
            return (0, 0)

        phase = (0.18 - self._shake_timer) * 80.0
        dx = int(round(math.sin(phase * 1.7) * self._shake_strength))
        dy = int(round(math.cos(phase * 1.2) * (self._shake_strength * 0.35)))
        return (dx, dy)

    def _persist_settings(self) -> None:
        save_user_settings(self._settings, "user_settings.json")

    def _start_fade(self, target: SceneResult) -> None:
        self._fade_target = target
        self._fade_dir = 1
        self._fade_alpha = max(0, int(self._fade_alpha))

    def _apply_accessibility_theme(self) -> None:
        # Keep menu readable even with high contrast.
        if self._settings.high_contrast:
            self._theme.fg_color = (0, 0, 0)
            self._theme.muted_color = (25, 25, 25)
            self._theme.accent_color = (0, 90, 255)
            self._theme.panel_alpha = 235
        else:
            self._theme.fg_color = (20, 20, 20)
            self._theme.muted_color = (70, 70, 70)
            self._theme.accent_color = (0, 120, 255)
            self._theme.panel_alpha = 210

    def _make_main_page(self) -> MenuPage:
        def play() -> None:
            self._toast_message("Good luck. Have fun.")
            self._bg.poke((self._screen_w * 0.5, self._screen_h * 0.5), strength=0.8, seconds=0.22)
            self._start_fade(
                SceneResult.switch(
                    GameplayScene(config=self.config, screen_size=self.screen_size)
                )
            )

        def options() -> None:
            self._push_page(self._make_options_page(), default_selected=0)

        def extras() -> None:
            self._push_page(self._make_extras_page(), default_selected=0)

        def credits() -> None:
            self._push_page(self._make_credits_page(), default_selected=0)

        def quit_game() -> None:
            self._push_page(self._make_quit_confirm_page(), default_selected=1)  # Default to "No"

        items = [
            ButtonItem("Play", play, hint="Start a new run"),
            ButtonItem("Options", options, hint="Audio, visuals, accessibility"),
            ButtonItem("Extras", extras, hint="Cute stuff and future modes"),
            ButtonItem("Credits", credits, hint="Who made this?"),
            ButtonItem("Quit", quit_game, hint="See you soon"),
        ]
        if self._secret_unlocked:
            items.insert(
                3,
                ButtonItem(
                    "Secret",
                    lambda: self._toast_message("You found it. You're unstoppable."),
                    hint="A little surprise",
                ),
            )

        return MenuPage(
            title="Main Menu",
            subtitle="Up/Down • Enter • Esc",
            items=items,
            footer="",
        )

    def _make_options_page(self) -> MenuPage:
        def set_master_volume(v: float) -> None:
            self._settings.master_volume = max(0.0, min(1.0, float(v)))
            self._persist_settings()

        def set_reduce_motion(v: bool) -> None:
            self._settings.reduce_motion = bool(v)
            self._persist_settings()
            self._toast_message("Motion settings updated")

        def set_high_contrast(v: bool) -> None:
            self._settings.high_contrast = bool(v)
            self._persist_settings()
            self._apply_accessibility_theme()

        def set_show_fps(v: bool) -> None:
            self._settings.show_fps = bool(v)
            self._persist_settings()

        def set_fullscreen(v: bool) -> None:
            self._settings.fullscreen = bool(v)
            self._persist_settings()
            self._toast_message("Fullscreen applies on restart")

        def reset() -> None:
            self._settings = UserSettings()
            self._persist_settings()
            self._apply_accessibility_theme()
            self._toast_message("Settings reset")

        return MenuPage(
            title="Options",
            subtitle="Left/Right to change • Esc to go back",
            items=[
                SliderItem(
                    "Master Volume",
                    get_value=lambda: self._settings.master_volume,
                    set_value=set_master_volume,
                    step=0.05,
                    hint="(Placeholder until audio is added)",
                ),
                ToggleItem(
                    "Reduce Motion",
                    get_value=lambda: self._settings.reduce_motion,
                    set_value=set_reduce_motion,
                    hint="Less animation, calmer menu",
                ),
                ToggleItem(
                    "High Contrast",
                    get_value=lambda: self._settings.high_contrast,
                    set_value=set_high_contrast,
                    hint="Improves readability",
                ),
                ToggleItem(
                    "Show FPS",
                    get_value=lambda: self._settings.show_fps,
                    set_value=set_show_fps,
                    hint="Developer-ish overlay (future)",
                ),
                ToggleItem(
                    "Fullscreen",
                    get_value=lambda: self._settings.fullscreen,
                    set_value=set_fullscreen,
                    hint="Applied next launch",
                ),
                ButtonItem("Reset to Defaults", reset, hint="Back to factory feelings"),
            ],
            footer="",
        )

    def _make_extras_page(self) -> MenuPage:
        def locked(msg: str) -> None:
            self._thunk(msg)

        # Locked placeholders (charm > dead-ends): selectable, shows a lock badge
        # and gives a little feedback when pressed.
        assist = ButtonItem(
            "Little Encouragement",
            lambda: locked(
                random.choice(
                    [
                        "Locked — but hey, you're doing great.",
                        "Locked — take breaks, drink water.",
                        "Locked — thanks for playing.",
                        "Locked — may your jumps be true.",
                    ]
                )
            ),
            hint="A tiny heart refill",
            locked=True,
            badge="Locked",
        )

        jukebox = ButtonItem(
            "Jukebox",
            lambda: locked("Locked — soundtrack arrives later"),
            hint="Listen to unlocked tracks",
            locked=True,
            badge="Locked",
        )
        museum = ButtonItem(
            "Museum",
            lambda: locked("Locked — the dev notes will be here"),
            hint="Concept art, dev notes, curios",
            locked=True,
            badge="Locked",
        )
        challenge = ButtonItem(
            "Daily Challenge",
            lambda: locked("Locked — daily runs coming soon"),
            hint="Same seed for everyone",
            locked=True,
            badge="Locked",
        )

        return MenuPage(
            title="Extras",
            subtitle="Optional joy",
            items=[
                assist,
                jukebox,
                museum,
                challenge,
            ],
            footer="",
        )

    def _make_credits_page(self) -> MenuPage:
        # Reset scroll state on entry
        self._credits_scroll = -self._screen_h * 0.6
        self._credits_items = [
            ("Created by", "Srinivas Karthik", "lead"),
            ("", "— A solo indie journey —", "stat"),
            ("Programming", "Srinivas Karthik", "normal"),
            ("Design", "Srinivas Karthik", "normal"),
            ("UI/UX", "Srinivas Karthik", "normal"),
            ("", "☕ Countless cups of coffee", "stat"),
            ("Art Direction", "Procedural Geometry", "normal"),
            ("Particles & VFX", "Mathematical Magic", "normal"),
            ("", "⏱️ Late-night debugging sessions", "stat"),
            ("Engine", "Pygame Community", "normal"),
            ("", "🎮 Made for players who appreciate small games", "stat"),
            ("Special Thanks", "You (The Player)", "heart"),
            ("", "Made with ❤️ and 🐍", "footer"),
            ("", "Keep running. Keep dreaming.", "footer"),
        ]

        # An empty interactive page that effectively acts as a canvas for our custom draw routine
        def go_back() -> None:
            self._pop_page()

        # Invisible giant button to catch clicks anywhere to exit or speed up?
        # For now, just a back button at the bottom.
        back_btn = ButtonItem("Back", go_back, hint="Return to main menu")
        
        return MenuPage(
            title="Credits",
            subtitle="",
            items=[back_btn],
            footer="",
        )

    def _make_quit_confirm_page(self) -> MenuPage:
        def confirm_quit() -> None:
            self._toast_message("See you next time!")
            self._bg.poke((self._screen_w * 0.5, self._screen_h * 0.5), strength=0.9, seconds=0.24)
            self._start_fade(SceneResult.quit())

        def cancel_quit() -> None:
            self._pop_page()

        return MenuPage(
            title="Quit Game",
            subtitle="Are you sure you want to quit?",
            items=[
                ButtonItem("Yes, quit", confirm_quit, hint="Exit to desktop"),
                ButtonItem("No, stay", cancel_quit, hint="Back to the menu"),
            ],
            footer="",
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        # Ignore input during fade-out or transitions.
        if self._fade_dir == 1 or self._transition.active:
            return

        # Credits page: click on names for easter eggs
        if self._stack.page.title == "Credits" and event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            self._handle_credits_click(mx, my)
            return

        # Ensure mouse hit-boxes are computed before input uses them.
        self._view.compute_item_rects(self._stack.page, offset=self._menu_offset())

        if event.type == pygame.KEYDOWN:
            # Scene-level back handling so we can animate and correctly pop.
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                if self._stack.can_pop():
                    self._pop_page()
                else:
                    # On root, Esc opens Quit confirmation (common indie behavior).
                    self._push_page(self._make_quit_confirm_page(), default_selected=1)
                return

            # Secret charm: Konami code unlocks a tiny surprise.
            self._konami.append(int(event.key))
            self._konami = self._konami[-12:]
            code = [
                pygame.K_UP,
                pygame.K_UP,
                pygame.K_DOWN,
                pygame.K_DOWN,
                pygame.K_LEFT,
                pygame.K_RIGHT,
                pygame.K_LEFT,
                pygame.K_RIGHT,
                pygame.K_b,
                pygame.K_a,
            ]
            if not self._secret_unlocked and len(self._konami) >= len(code):
                if self._konami[-len(code) :] == code:
                    self._secret_unlocked = True
                    # Rebuild main page if we're on it.
                    if not self._stack.can_pop():
                        self._stack = MenuStack(self._make_main_page())
                        self._input = MenuInput(self._stack)
                    self._toast_message("Secret unlocked!")

        self._input.handle_event(event, view=self._view)

    def update(self, dt: float):
        self._apply_accessibility_theme()

        dt = float(dt)
        self._t += dt
        self._pulse = 0.5 + 0.5 * math.sin(self._t * 3.0)

        if self._toast_timer > 0.0:
            self._toast_timer -= dt
            total = self._toast_fade_in + self._toast_duration + self._toast_fade_out
            elapsed = total - self._toast_timer

            # Fade in phase
            if elapsed < self._toast_fade_in:
                t = elapsed / max(0.001, self._toast_fade_in)
                self._toast_alpha = t
                self._toast_scale = 0.92 + 0.08 * t
            # Hold phase
            elif elapsed < self._toast_fade_in + self._toast_duration:
                self._toast_alpha = 1.0
                self._toast_scale = 1.0
            # Fade out phase
            else:
                fade_elapsed = elapsed - (self._toast_fade_in + self._toast_duration)
                t = fade_elapsed / max(0.001, self._toast_fade_out)
                self._toast_alpha = 1.0 - t
                self._toast_scale = 1.0 - 0.08 * t

            if self._toast_timer <= 0.0:
                self._toast = None
                self._toast_alpha = 0.0
                self._toast_scale = 1.0

        if self._shake_timer > 0.0:
            self._shake_timer -= dt
            if self._shake_timer <= 0.0:
                self._shake_timer = 0.0
                self._shake_strength = 0.0

        if self._transition.active:
            self._transition.update(dt)

        # Dynamic Background Reactivity: focus follows selection/hover and
        # selection changes trigger a small "poke".
        focus = self._current_focus_pos()
        self._bg.set_focus(focus, amount=0.42 if not self._settings.reduce_motion else 0.18)

        focus_key = (id(self._stack.page), int(self._input.selected_index))
        if (not self._transition.active) and focus_key != self._last_focus_key:
            self._bg.poke(focus, strength=0.55, seconds=0.16)
            self._last_focus_key = focus_key

        self._bg.update(dt, reduce_motion=self._settings.reduce_motion)

        # Credits logic: auto-scroll
        if self._stack.page.title == "Credits" and not self._settings.reduce_motion:
            speed = 45.0
            # Mouse interaction: speed up or reverse slightly based on mouse Y?
            # Let's keep it auto-scrolling upwards but allow mouse wheel to override via standard input handling later?
            # For now: simple auto-scroll.
            self._credits_scroll += speed * dt

        # Fade transitions
        if self._fade_dir != 0:
            speed = 420.0  # alpha per second
            self._fade_alpha = int(max(0, min(255, self._fade_alpha + self._fade_dir * speed * dt)))
            if self._fade_dir == -1 and self._fade_alpha <= 0:
                self._fade_alpha = 0
                self._fade_dir = 0
            elif self._fade_dir == 1 and self._fade_alpha >= 255:
                self._fade_alpha = 255
                target, self._fade_target = self._fade_target, None
                self._fade_dir = 0
                return target

        pending, self._pending = self._pending, None
        return pending

    def _handle_credits_click(self, mx: int, my: int) -> None:
        """Easter eggs for clicking on credit names"""
        cx = self._screen_w // 2
        y_off = 140 - self._credits_scroll
        
        for role, name, kind in self._credits_items:
            if not name or kind in ("stat", "footer"):
                continue
            
            # Compute y position (same logic as draw)
            if kind == "lead":
                gap = 60
                margin = 120
            elif kind == "heart":
                gap = 28
                margin = 90
            else:
                gap = 28
                margin = 90
            
            y_off += gap
            
            # Simple hit test (loose)
            name_font = self._theme.title_font if kind == "lead" else self._theme.item_font
            n_surf = name_font.render(name, True, (0, 0, 0))
            w = n_surf.get_width()
            h = n_surf.get_height()
            
            if (cx - w // 2 < mx < cx + w // 2) and (y_off - 10 < my < y_off + h + 10):
                # Easter egg messages
                messages = {
                    "Srinivas Karthik": "Thanks for checking! This was a fun build 🚀",
                    "Procedural Geometry": "No artists were harmed in the making of this game.",
                    "Mathematical Magic": "sin(), cos(), and a sprinkle of randomness.",
                    "Pygame Community": "🐍 Python game dev forever!",
                    "GitHub Copilot": "Beep boop. Happy to help!",
                    "Celeste, Hollow Knight, Stardew Valley": "These games changed my life.",
                    "You (The Player)": "You're awesome. Seriously. Thank you. ❤️",
                }
                msg = messages.get(name, f"Thanks for clicking on {name}!")
                self._toast_message(msg, seconds=2.2)
                self._bg.poke((cx, y_off + h // 2), strength=0.8, seconds=0.2)
                return
            
            y_off += margin

    def _draw_credits(self, screen: pygame.Surface) -> None:
        cx = self._screen_w // 2
        cy = self._screen_h // 2
        
        # Dark vignette overlay for better text readability
        vignette = pygame.Surface((self._screen_w, self._screen_h), pygame.SRCALPHA)
        for i in range(60):
            alpha = int(i * 1.5)
            pygame.draw.rect(vignette, (0, 0, 0, alpha), vignette.get_rect(), width=1)
        screen.blit(vignette, (0, 0))
        
        # Pulsing title with glow
        title_s = self._theme.title_font.render("Credits", True, self._theme.accent_color)
        scale = 1.0 + 0.08 * math.sin(self._t * 2.5)
        w = int(title_s.get_width() * scale)
        h = int(title_s.get_height() * scale)
        
        # Glow effect
        glow = pygame.Surface((w + 20, h + 20), pygame.SRCALPHA)
        for r in range(5, 15, 2):
            glow_surf = pygame.transform.smoothscale(title_s, (w + r, h + r))
            glow_surf.set_alpha(20)
            glow.blit(glow_surf, (10 - r // 2, 10 - r // 2))
        screen.blit(glow, (cx - w // 2 - 10, 30))
        
        scaled_title = pygame.transform.smoothscale(title_s, (w, h))
        screen.blit(scaled_title, (cx - w // 2, 40))

        y_off = 140 - self._credits_scroll
        
        for idx, (role, name, kind) in enumerate(self._credits_items):
            # Layout based on type
            if kind == "lead":
                role_font = self._theme.item_font
                name_font = self._theme.title_font
                gap = 60
                margin = 120
                color = (255, 215, 0)  # Gold for lead
            elif kind == "heart":
                role_font = self._theme.small_font
                name_font = self._theme.title_font
                gap = 28
                margin = 90
                color = (255, 100, 150)  # Pink/heart color
            elif kind == "stat":
                role_font = self._theme.small_font
                name_font = self._theme.small_font
                gap = 20
                margin = 70
                color = (150, 150, 255)  # Soft purple for stats
            elif kind == "footer":
                role_font = self._theme.small_font
                name_font = self._theme.item_font
                gap = 20
                margin = 180
                color = self._theme.accent_color
            else:
                role_font = self._theme.small_font
                name_font = self._theme.item_font
                gap = 28
                margin = 90
                color = (220, 220, 220)  # Bright white

            # Draw role
            if role:
                r_surf = role_font.render(role, True, self._theme.muted_color)
                # Depth-based alpha
                dist = (y_off - cy) / (self._screen_h * 0.6)
                alpha = max(0, min(255, int(255 - abs(dist) * 280)))
                if alpha > 10:
                    r_surf.set_alpha(alpha)
                    screen.blit(r_surf, (cx - r_surf.get_width() // 2, y_off))
            
            # Draw name
            y_off += gap
            n_surf = name_font.render(name, True, color)
            
            # Smooth depth-based fade with better curve
            dist = (y_off - cy) / (self._screen_h * 0.6)
            fade_curve = 1.0 - min(1.0, abs(dist) ** 1.5)  # Exponential fade
            alpha = int(255 * max(0.0, fade_curve))
            
            if alpha > 10:
                n_surf.set_alpha(alpha)
                nx = cx - n_surf.get_width() // 2
                
                # Sparkle effect on lead credit
                if kind == "lead" and alpha > 200:
                    for _ in range(3):
                        sparkle_x = nx + random.randint(-40, n_surf.get_width() + 40)
                        sparkle_y = y_off + random.randint(-10, n_surf.get_height() + 10)
                        sparkle_life = (self._t * 3 + sparkle_x * 0.01) % 1.0
                        if sparkle_life < 0.3:
                            s_alpha = int(200 * math.sin(sparkle_life * math.pi / 0.3))
                            pygame.draw.circle(screen, (255, 255, 150, s_alpha), (sparkle_x, sparkle_y), 2)
                
                screen.blit(n_surf, (nx, y_off))
            
            y_off += margin

        # Loop scroll smoothly
        total_h = y_off + self._credits_scroll
        if self._credits_scroll > total_h + 200:
             self._credits_scroll = -self._screen_h * 0.6

        # Top and bottom gradient masks for smooth fade
        gradient_h = 120
        top_grad = pygame.Surface((self._screen_w, gradient_h), pygame.SRCALPHA)
        bot_grad = pygame.Surface((self._screen_w, gradient_h), pygame.SRCALPHA)
        for i in range(gradient_h):
            alpha = int(255 * (1.0 - i / gradient_h))
            bg = self.config.background_color
            top_grad.fill((*bg, alpha), pygame.Rect(0, i, self._screen_w, 1))
            bot_grad.fill((*bg, alpha), pygame.Rect(0, gradient_h - i - 1, self._screen_w, 1))
        screen.blit(top_grad, (0, 0))
        screen.blit(bot_grad, (0, self._screen_h - gradient_h))
        
        # Interactive hint
        hint = self._theme.small_font.render("Click on names • Press Esc to Back", True, self._theme.muted_color)
        h_alpha = int(180 + 75 * math.sin(self._t * 2.0))
        hint.set_alpha(h_alpha)
        screen.blit(hint, (cx - hint.get_width() // 2, self._screen_h - 40))

    def draw(self, screen: pygame.Surface) -> None:
        # Background
        self._bg.draw(
            screen,
            base_color=self.config.background_color,
            accent=self._theme.accent_color,
            high_contrast=self._settings.high_contrast,
        )

        # Big title above the panel (a bit of charm)
        title_text = wobble_text(
            self._theme.title_font,
            "2D Runner",
            self._theme.fg_color,
            t=self._t,
            strength=0.0 if self._settings.reduce_motion else 2.2,
        )
        tx = (self._screen_w - title_text.get_width()) // 2
        ty = max(20, (self._screen_h // 2) - 320)

        shadow = pygame.Surface(title_text.get_size(), pygame.SRCALPHA)
        shadow.blit(title_text, (0, 0))
        shadow.fill((0, 0, 0, 60), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(shadow, (tx + 2, ty + 3))
        screen.blit(title_text, (tx, ty))

        # Tagline
        tagline = self._theme.small_font.render(self._tagline, True, self._theme.muted_color)
        screen.blit(tagline, ((self._screen_w - tagline.get_width()) // 2, ty + title_text.get_height() + 8))

        page = self._stack.page

        if self._transition.active and not self._settings.reduce_motion:
            # Transition already contains fully rendered from/to frames.
            self._transition.draw(screen)
        else:
            if page.title == "Credits":
                self._draw_credits(screen)
            else:
                self._update_footer(page, self._input.selected_index, can_pop=self._stack.can_pop())
                self._view.draw(
                    screen,
                    page=page,
                    selected_index=self._input.selected_index,
                    pulse=self._pulse,
                    offset=self._menu_offset(),
                )

        # Toast with smooth fade/scale animation
        if self._toast and self._toast_alpha > 0.01:
            toast_surf = self._theme.small_font.render(self._toast, True, self._theme.fg_color)
            pad = 10
            base_w = toast_surf.get_width() + pad * 2
            base_h = toast_surf.get_height() + pad * 2

            # Apply scale
            scaled_w = int(base_w * self._toast_scale)
            scaled_h = int(base_h * self._toast_scale)
            box = pygame.Rect(0, 0, scaled_w, scaled_h)
            box.center = (self._screen_w // 2, int(self._screen_h * 0.18))

            # Create scaled background
            base_surf = pygame.Surface((base_w, base_h), pygame.SRCALPHA)
            bg_alpha = int((210 if not self._settings.high_contrast else 240) * self._toast_alpha)
            base_surf.fill((255, 255, 255, bg_alpha))
            border_alpha = int(70 * self._toast_alpha)
            pygame.draw.rect(base_surf, (0, 0, 0, border_alpha), base_surf.get_rect(), width=2, border_radius=12)
            base_surf.blit(toast_surf, (pad, pad))

            # Scale and apply overall alpha
            if scaled_w > 0 and scaled_h > 0:
                scaled_surf = pygame.transform.smoothscale(base_surf, (scaled_w, scaled_h))
                scaled_surf.set_alpha(int(255 * self._toast_alpha))
                screen.blit(scaled_surf, box.topleft)

        # Fade overlay
        if self._fade_alpha > 0:
            fade = pygame.Surface((self._screen_w, self._screen_h), pygame.SRCALPHA)
            fade.fill((0, 0, 0, int(self._fade_alpha)))
            screen.blit(fade, (0, 0))
