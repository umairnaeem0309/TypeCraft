"""
scenes/lesson.py

Drives TypingEngine + KeyboardRenderer + HUD. Input is captured only in
handle_event (§1.3) and pushed straight into TypingEngine.feed_key().
Metrics are recomputed on keystroke, not every frame (§5.5) — update()
only advances the live timer display via engine.metrics(), which itself
is cheap (no rasterisation happens there).
"""

import string

import pygame

from typecraft.core.scene import Scene
from typecraft.engine.input_modes import create_mode
from typecraft.engine.typing_engine import TypingEngine
from typecraft.models.attempt import AttemptStatus, CharStatus
from typecraft.ui import theme
from typecraft.ui.hud import HUD
from typecraft.ui.keyboard_renderer import KeyboardRenderer

# Full printable set: lessons.json content includes capitals (Shift keys),
# commas, periods, question marks — not just lowercase home-row characters.
TYPABLE = set(string.ascii_letters + string.digits + string.punctuation + " ")


class LessonScene(Scene):
    def on_enter(self, lesson=None, mode_key=None, **kwargs) -> None:
        self.lesson = lesson
        self.mode_key = mode_key
        self.profile = self.ctx.active_profile

        mode = create_mode(mode_key)
        self.engine = TypingEngine(
            target=lesson.target_text(), mode=mode, profile_id=self.profile.id,
            lesson_id=lesson.id, mode_key=mode_key, tier=lesson.tier,
        )

        kb_w, _kb_h = KeyboardRenderer.size()
        self.keyboard = KeyboardRenderer(
            self.ctx.resources, origin=((theme.SCREEN_WIDTH - kb_w) // 2, 440))
        self.keyboard.prerender()

        self.hud = HUD(pygame.Rect(60, 60, 800, 40), self.ctx.resources)

        self._quit_requested = False
        self._update_keyboard_hint()

        # Crash recovery (FR-073): the row id reserved by the first checkpoint, and
        # the time since the last one. Both reset per attempt.
        self._attempt_row_id = None
        self._since_checkpoint = 0.0

    def on_exit(self) -> None:
        pass

    def _update_keyboard_hint(self) -> None:
        """Point the keyboard at the character the student must type next (FR-092).

        The inherited code highlighted the character just *pressed*, which taught
        nothing: by the time the key lit up the student had already found it.
        """
        engine = self.engine
        expected = None if engine.is_finished() else engine.target[engine.cursor]
        self.keyboard.highlight_expected(expected)

    def _has_started(self) -> bool:
        return self.engine.total_keystrokes > 0

    def _checkpoint(self) -> None:
        """Write the in-flight attempt so a power cut leaves a recoverable row."""
        self._attempt_row_id = self.ctx.progression.checkpoint(
            self.engine, self._attempt_row_id)
        self._since_checkpoint = 0.0

    def _finish(self, status: AttemptStatus):
        """Single exit point for an attempt, so Esc, window-close and completion
        cannot drift apart in how they persist (FR-070, FR-071, FR-076)."""
        attempt = self.engine.result(status=status)
        return self.ctx.progression.score(attempt, self.profile, self._attempt_row_id)

    def on_quit_requested(self) -> None:
        """Window close mid-lesson (FR-071): save what the student has done.

        Routed through the same `_finish()` as Esc and completion, so the three
        exit paths cannot disagree about what gets persisted.
        """
        if self._has_started() and not self.engine.is_finished():
            self._finish(AttemptStatus.INCOMPLETE)

    def _quit_lesson(self) -> None:
        """Esc mid-lesson (decision D3): persist as incomplete, return to lesson select."""
        if self._has_started() and not self.engine.is_finished():
            self._finish(AttemptStatus.INCOMPLETE)
        self.ctx.states.change("lesson_select")

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._quit_lesson()
                return

            if event.key == pygame.K_BACKSPACE:
                self.engine.feed_key("\b")
                self.hud.update_metrics(self.engine.metrics())
                # A backspace moves the cursor, so the expected key changes too.
                self._update_keyboard_hint()
                return

            char = event.unicode
            if char in TYPABLE:
                self.engine.feed_key(char)
                self.hud.update_metrics(self.engine.metrics())
                self._update_keyboard_hint()

                if self.engine.is_finished():
                    scored = self._finish(AttemptStatus.COMPLETE)
                    self.ctx.states.change("results", attempt=scored, lesson=self.lesson)

    def update(self, dt: float) -> None:
        # Timer display should keep advancing even without a keystroke, so
        # refresh the elapsed-time field each frame — cheap, no rasterisation.
        self.hud.update_metrics(self.engine.metrics())

        # Checkpoint on a timer, not per keystroke: database I/O on the keystroke
        # path would be felt as stutter on the target hardware (NFR-007).
        if self._has_started() and not self.engine.is_finished():
            self._since_checkpoint += dt
            if self._since_checkpoint >= self.ctx.progression.CHECKPOINT_INTERVAL_SEC:
                self._checkpoint()

    def render(self, surface) -> None:
        self.hud.render(surface)
        self.keyboard.render(surface)
        self._render_target_text(surface)

        font_small = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        hint = self.ctx.resources.text_surface("Esc to quit and save progress", font_small,
                                                theme.COLOR_TEXT_MUTED)
        surface.blit(hint, (60, theme.SCREEN_HEIGHT - 40))

    def _render_target_text(self, surface) -> None:
        font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TARGET_TEXT)
        x, y = 60, 200
        max_width = theme.SCREEN_WIDTH - 120
        line_height = font.get_height() + 8

        for i, ch in enumerate(self.engine.target):
            status = self.engine.char_status[i]
            if status == CharStatus.CORRECT:
                color = theme.COLOR_CORRECT
            elif status == CharStatus.ERROR:
                color = theme.COLOR_ERROR
            else:
                color = theme.COLOR_PENDING

            glyph = self.ctx.resources.text_surface(ch if ch != " " else "\u00b7", font, color)
            surface.blit(glyph, (x, y))
            x += glyph.get_width()
            if x > max_width + 60:
                x = 60
                y += line_height

            if i == self.engine.cursor:
                pygame.draw.line(surface, theme.COLOR_ACCENT, (x, y), (x, y + font.get_height()), 3)
