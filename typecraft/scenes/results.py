"""scenes/results.py — stars, XP gain, encouragement message, Retry/Continue/Leaderboard."""

import json
import random

import pygame

from typecraft.core.paths import resource_path, writable_data_dir
from typecraft.core.scene import Scene
from typecraft.ui import theme
from typecraft.ui.button import Button
from typecraft.ui.star_rating import StarRating


class ResultsScene(Scene):
    def on_enter(self, attempt=None, lesson=None, **kwargs) -> None:
        self.attempt = attempt
        self.lesson = lesson
        self.message = self._pick_message(attempt.accuracy)

        cx = theme.SCREEN_WIDTH // 2
        w, h, gap = 220, 56, 30
        y = 600

        # Colour carries the meaning here, because a child reads the colour before
        # the word: grey for "go back and try again", green for the way onward,
        # orange for the optional detour.
        self.buttons = [
            Button(pygame.Rect(cx - int(1.5 * w) - gap, y, w, h), "Retry",
                   self._retry, self.ctx.resources,
                   bg_color=theme.COLOR_NEUTRAL),
            Button(pygame.Rect(cx - w // 2, y, w, h), "Continue",
                   lambda: self.ctx.states.change("lesson_select"), self.ctx.resources,
                   bg_color=theme.COLOR_PRIMARY),
            Button(pygame.Rect(cx + int(0.5 * w) + gap, y, w, h), "Leaderboard",
                   lambda: self.ctx.states.change("leaderboard"), self.ctx.resources,
                   bg_color=theme.COLOR_WARNING),
        ]
        self.stars = StarRating(pygame.Rect(cx - 100, 250, 200, 60), stars=attempt.stars)
        # Italic font for the bottom encouragement message.
        self._message_font = pygame.font.Font(None, theme.FONT_SIZE_BODY)
        self._message_font.set_italic(True)

    def _retry(self) -> None:
        self.ctx.states.change("mode_select", lesson=self.lesson)

    def _pick_message(self, accuracy: float) -> str:
        band = "encourage_low"
        if accuracy >= 100:
            band = "encourage_perfect"
        elif accuracy >= 92:
            band = "encourage_high"
        elif accuracy >= 85:
            band = "encourage_mid"

        live = writable_data_dir() / "messages.json"
        path = live if live.exists() else resource_path("data/messages.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            options = data.get(band, ["Great effort!"])
            return random.choice(options)
        except (FileNotFoundError, json.JSONDecodeError):
            return "Great effort!"

    def handle_event(self, event) -> None:
        for btn in self.buttons:
            if btn.handle_event(event):
                return

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TITLE - 8)
        title = "Lesson Complete!" if self.attempt.accuracy >= 85 else "Keep Practising!"
        title_surf = self.ctx.resources.text_surface(title, font_h, theme.COLOR_TEXT)
        surface.blit(title_surf, title_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 53)))

        self.stars.render(surface)

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        stats = [
            ("Net WPM", f"{self.attempt.wpm_net:.0f}"),
            ("Accuracy", f"{self.attempt.accuracy:.0f}%"),
            ("Max Combo", str(self.attempt.max_combo)),
            ("XP Earned", f"+{self.attempt.xp_awarded}"),
        ]

        # Draw stat cards in a tidy 2x2 grid.
        card_w, card_h, gap = 240, 90, 24
        start_x = (theme.SCREEN_WIDTH - (2 * card_w + gap)) // 2
        start_y = 350
        for i, (label, value) in enumerate(stats):
            col = i % 2
            row = i // 2
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(surface, theme.COLOR_CARD_BG, rect, border_radius=12)
            pygame.draw.rect(surface, theme.COLOR_LOCKED, rect, width=2, border_radius=12)
            label_surf = self.ctx.resources.text_surface(label, font_body, theme.COLOR_TEXT_MUTED)
            surface.blit(label_surf, label_surf.get_rect(center=(rect.centerx, rect.y + 30)))
            value_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
            value_surf = self.ctx.resources.text_surface(value, value_font, theme.COLOR_PRIMARY_DARK)
            surface.blit(value_surf, value_surf.get_rect(center=(rect.centerx, rect.y + 58)))

        msg_surf = self.ctx.resources.text_surface(self.message, self._message_font, theme.COLOR_PRIMARY_DARK)
        surface.blit(msg_surf, msg_surf.get_rect(center=(theme.SCREEN_WIDTH // 2,
                                                          theme.SCREEN_HEIGHT - 30)))

        for btn in self.buttons:
            btn.render(surface)
