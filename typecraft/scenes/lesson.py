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
from typecraft.ui.target_text import TargetTextLayout

# Full printable set: lessons.json content includes capitals (Shift keys),
# commas, periods, question marks — not just lowercase home-row characters.
TYPABLE = set(string.ascii_letters + string.digits + string.punctuation + " ")

#: Where the drill text is laid out. Sits between the HUD and the keyboard, and the
#: layout is clamped to it so nothing can be drawn past the window edge (FR-102).
TEXT_AREA = pygame.Rect(60, 150, theme.SCREEN_WIDTH - 120, 250)


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

        # Computed once: the target text is fixed for the whole attempt, so only the
        # per-character colours change from frame to frame (NFR-007).
        self.layout = TargetTextLayout(
            self.engine.target,
            self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TARGET_TEXT),
            TEXT_AREA,
        )

        # Pre-composite the target text into per-line surfaces. Only the line
        # containing the cursor is re-rendered on a keystroke, so we avoid
        # ~150 individual glyph blits per frame (NFR-007, TC-018).
        self._line_sprites = []  # list of (rect, surface)
        self._build_line_sprites()
        self._last_cursor_line = 0

        self._quit_requested = False
        self._update_keyboard_hint()

        # The "Esc to quit" hint never changes; render it once.
        self._hint_surf = self.ctx.resources.text_surface(
            "Esc to quit and save progress",
            self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL),
            theme.COLOR_TEXT_MUTED,
        )

        # Throttle HUD re-renders: the timer only changes once per second.
        self._hud_dirty = True
        self._last_hud_elapsed = 0

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
        # The keyboard visual changed, so the whole keyboard area needs updating.
        self.mark_dirty(self.keyboard.dirty_rect())

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
                self.ctx.audio.play("key_click.wav")
                self._update_target_text_sprite()
                self._update_keyboard_hint()
                self._hud_dirty = True
                return

            char = event.unicode
            if char in TYPABLE:
                result = self.engine.feed_key(char)
                # Sound feedback: a soft click on every keystroke, an error tone
                # when the wrong key was typed, and a success fanfare on completion.
                if result.is_error:
                    self.ctx.audio.play("error.wav")
                else:
                    self.ctx.audio.play("key_click.wav")

                self._update_target_text_sprite()
                self._update_keyboard_hint()
                self._hud_dirty = True

                if self.engine.is_finished():
                    scored = self._finish(AttemptStatus.COMPLETE)
                    self.ctx.audio.play("success.wav")
                    self.ctx.states.change("results", attempt=scored, lesson=self.lesson)

    def update(self, dt: float) -> None:
        # Timer display should keep advancing even without a keystroke, but
        # there is no need to rasterise it more than once per second (TC-018).
        metrics = self.engine.metrics()
        current_elapsed = int(metrics["elapsed_sec"])
        if current_elapsed != self._last_hud_elapsed:
            self._last_hud_elapsed = current_elapsed
            self._hud_dirty = True
        if self._hud_dirty:
            self.hud.update_metrics(metrics)

        # Checkpoint on a timer, not per keystroke: database I/O on the keystroke
        # path would be felt as stutter on the target hardware (NFR-007).
        if self._has_started() and not self.engine.is_finished():
            self._since_checkpoint += dt
            if self._since_checkpoint >= self.ctx.progression.CHECKPOINT_INTERVAL_SEC:
                self._checkpoint()

    def render(self, surface) -> None:
        if self._hud_dirty:
            self.hud.render(surface)
            self.mark_dirty(self.hud.rect)
            self._hud_dirty = False

        self.keyboard.render(surface)
        self._render_target_text(surface)

        surface.blit(self._hint_surf, (60, theme.SCREEN_HEIGHT - 40))
        self.mark_dirty(pygame.Rect(60, theme.SCREEN_HEIGHT - 40,
                                    self._hint_surf.get_width(), self._hint_surf.get_height()))

    def _build_line_sprites(self) -> None:
        """Create a cached surface for every line in the pre-computed layout."""
        self._line_sprites = []
        for line_indices in self.layout.lines:
            if not line_indices:
                self._line_sprites.append((pygame.Rect(), None))
                continue
            first = self.layout.glyphs[line_indices[0]][2]
            last = self.layout.glyphs[line_indices[-1]][2]
            rect = pygame.Rect(first.x, first.y, last.right - first.x, first.height)
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            self._line_sprites.append((rect, surf))
        self._render_all_line_sprites()

    def _render_all_line_sprites(self) -> None:
        for line_index in range(len(self._line_sprites)):
            self._render_line_sprite(line_index)

    def _render_line_sprite(self, line_index: int) -> None:
        """Re-render one line surface from the current engine state."""
        rect, surf = self._line_sprites[line_index]
        if surf is None:
            return
        line_indices = self.layout.lines[line_index]
        font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TARGET_TEXT)
        surf.fill((0, 0, 0, 0))
        for index in line_indices:
            _idx, glyph_char, glyph_rect = self.layout.glyphs[index]
            status = self.engine.char_status[index]
            if status == CharStatus.CORRECT:
                color = theme.COLOR_CORRECT
            elif status == CharStatus.ERROR:
                color = theme.COLOR_ERROR
            else:
                color = theme.COLOR_PENDING
            glyph = self.ctx.resources.text_surface(glyph_char, font, color)
            surf.blit(glyph, (glyph_rect.x - rect.x, glyph_rect.y - rect.y))

    def _line_index_for_cursor(self, cursor: int) -> int:
        """Return the line index that contains the given cursor position."""
        for i, line_indices in enumerate(self.layout.lines):
            if line_indices and cursor in line_indices:
                return i
        # Cursor at end or empty: last line.
        return max(0, len(self.layout.lines) - 1)

    def _update_target_text_sprite(self) -> None:
        """Re-render the line containing the cursor and mark it dirty.

        The cursor may have crossed a line boundary (e.g. typing the last
        character of a line), so we also re-render the previous cursor line.
        """
        current_line = self._line_index_for_cursor(self.engine.cursor)
        for line_index in {self._last_cursor_line, current_line}:
            self._render_line_sprite(line_index)
            rect, _surf = self._line_sprites[line_index]
            self.mark_dirty(rect)
        self._last_cursor_line = current_line

    def _render_target_text(self, surface) -> None:
        """Draw the pre-computed layout. Positions never change during an attempt \u2014
        only the per-character colours \u2014 so nothing is measured here."""
        cursor = self.engine.cursor

        # A soft block behind the current character, plus the caret on its left
        # edge: two independent cues, so the position is unambiguous even where a
        # glyph is narrow (FR-101).
        current = self.layout.rect_for(cursor)
        if current is not None:
            pygame.draw.rect(surface, theme.COLOR_CARD_BG, current, border_radius=4)

        # Blit the cached line surfaces instead of each glyph every frame.
        for rect, surf in self._line_sprites:
            if surf is not None:
                surface.blit(surf, (rect.x, rect.y))

        pygame.draw.rect(surface, theme.COLOR_ACCENT, self.layout.caret_rect(cursor))
