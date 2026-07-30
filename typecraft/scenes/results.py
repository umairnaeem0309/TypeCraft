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
        w, h, gap = 220, 56, 20
        y = 560

        self.buttons = [
            Button(pygame.Rect(cx - int(1.5 * w) - gap, y, w, h), "Retry",
                   self._retry, self.ctx.resources),
            Button(pygame.Rect(cx - w // 2, y, w, h), "Continue",
                   lambda: self.ctx.states.change("lesson_select"), self.ctx.resources,
                   bg_color=theme.COLOR_ACCENT),
            Button(pygame.Rect(cx + int(0.5 * w) + gap, y, w, h), "Leaderboard",
                   lambda: self.ctx.states.change("leaderboard"), self.ctx.resources,
                   bg_color=theme.COLOR_TEXT_MUTED),
        ]
        self.stars = StarRating(pygame.Rect(cx - 100, 260, 200, 60), stars=attempt.stars)

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
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        title = "Lesson Complete!" if self.attempt.accuracy >= 85 else "Keep Practising!"
        title_surf = self.ctx.resources.text_surface(title, font_h, theme.COLOR_TEXT)
        surface.blit(title_surf, title_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, 120)))

        self.stars.render(surface)

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        stats = [
            f"Net WPM: {self.attempt.wpm_net:.0f}",
            f"Accuracy: {self.attempt.accuracy:.0f}%",
            f"Max Combo: {self.attempt.max_combo}",
            f"XP Earned: +{self.attempt.xp_awarded}",
        ]
        y = 360
        for line in stats:
            surf = self.ctx.resources.text_surface(line, font_body, theme.COLOR_TEXT)
            surface.blit(surf, surf.get_rect(center=(theme.SCREEN_WIDTH // 2, y)))
            y += 34

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        msg_surf = self.ctx.resources.text_surface(self.message, font_small, theme.COLOR_PRIMARY_DARK)
        surface.blit(msg_surf, msg_surf.get_rect(center=(theme.SCREEN_WIDTH // 2, y + 20)))

        for btn in self.buttons:
            btn.render(surface)
