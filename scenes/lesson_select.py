"""scenes/lesson_select.py — tiered lesson grid with lock icons and star badges."""

import pygame

from TypeCraft.core.scene import Scene
from TypeCraft.ui import theme
from TypeCraft.ui.button import Button
from TypeCraft.ui.star_rating import StarRating


class LessonSelectScene(Scene):
    def on_enter(self, **kwargs) -> None:
        self.profile = self.ctx.active_profile
        self.back_button = Button(
            pygame.Rect(20, 20, 160, 44), "Switch Profile",
            lambda: self.ctx.states.change("profile_select"), self.ctx.resources,
            bg_color=theme.COLOR_TEXT_MUTED,
        )
        self._build_cards()

    def _build_cards(self) -> None:
        self.cards = []
        cols = 5
        card_w, card_h, gap = 220, 130, 20
        start_x = (theme.SCREEN_WIDTH - (cols * card_w + (cols - 1) * gap)) // 2
        y = 120
        i = 0
        for tier_block in self.ctx.lessons.tiers():
            for raw in sorted(tier_block["lessons"], key=lambda l: l["order"]):
                lesson = self.ctx.lessons.get(raw["id"])
                unlocked = self.ctx.lessons.is_unlocked(self.profile, lesson.id)
                progress_rows = self.ctx.db.query(
                    "SELECT best_stars FROM lesson_progress WHERE profile_id=? AND lesson_id=?",
                    (self.profile.id, lesson.id),
                )
                stars = progress_rows[0]["best_stars"] if progress_rows else 0

                col = i % cols
                row = i // cols
                rect = pygame.Rect(start_x + col * (card_w + gap), y + row * (card_h + gap),
                                    card_w, card_h)
                self.cards.append((lesson, unlocked, stars, rect))
                i += 1

    def _select_lesson(self, lesson) -> None:
        self.ctx.states.change("mode_select", lesson=lesson)

    def handle_event(self, event) -> None:
        if self.back_button.handle_event(event):
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for lesson, unlocked, stars, rect in self.cards:
                if unlocked and rect.collidepoint(event.pos):
                    self._select_lesson(lesson)
                    return

    def update(self, dt: float) -> None:
        pass

    def render(self, surface) -> None:
        font_h = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        heading = self.ctx.resources.text_surface(
            f"{self.profile.name}'s Lessons", font_h, theme.COLOR_TEXT)
        surface.blit(heading, heading.get_rect(center=(theme.SCREEN_WIDTH // 2, 60)))

        font_body = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        for lesson, unlocked, stars, rect in self.cards:
            border_color = pygame.Color(lesson.tier_color) if unlocked else theme.COLOR_LOCKED
            bg = theme.COLOR_CARD_BG if unlocked else (230, 230, 233)
            pygame.draw.rect(surface, bg, rect, border_radius=12)
            pygame.draw.rect(surface, border_color, rect, width=3, border_radius=12)

            title = lesson.title if unlocked else "Locked"
            color = theme.COLOR_TEXT if unlocked else theme.COLOR_TEXT_MUTED
            title_surf = self.ctx.resources.text_surface(title, font_body, color)
            title_rect = title_surf.get_rect(center=(rect.centerx, rect.y + 30))
            surface.blit(title_surf, title_rect)

            if unlocked:
                star_widget = StarRating(pygame.Rect(rect.x, rect.centery, rect.width, 40), stars=stars)
                star_widget.render(surface)

    def _unused_prevent_lint(self):
        pass
