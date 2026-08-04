"""
scenes/lesson.py

Drives TypingEngine + KeyboardRenderer + HUD. Input is captured only in
handle_event (§1.3) and pushed straight into TypingEngine.feed_key().
"""

import string

import pygame

from typecraft.core.scene import Scene
from typecraft.engine.input_modes import create_mode
from typecraft.engine.typing_engine import TypingEngine
from typecraft.models.attempt import AttemptStatus, CharStatus
from typecraft.ui import theme
from typecraft.ui.button import Button
from typecraft.ui.hud import HUD
from typecraft.ui.keyboard_renderer import KeyboardRenderer
from typecraft.ui.target_text import TargetTextLayout

# Full printable set: lessons.json content includes capitals (Shift keys),
# commas, periods, question marks — not just lowercase home-row characters.
TYPABLE = set(string.ascii_letters + string.digits + string.punctuation + " ")

INSTRUCTION_PANEL = pygame.Rect(210, 120, 860, 430)
INSTRUCTION_START_RECT = pygame.Rect(500, 470, 280, 58)

# --- Vertical rhythm -------------------------------------------------------
# Derived rather than hand-picked, because the keyboard used to overlap the footer
# hint by 5 px: the board is 245 px tall and started at y=440, ending at 685, while
# the hint sat at 680. Measured: the drill text never needs more than 2 lines
# (74 px) even for the longest bundled lesson, so the space it had reserved was
# spent on the overlap instead. Paragraph lessons now use the same viewport with a
# virtual layout and a small automatic scroll as the cursor advances.

#: Where the drill text is laid out. The layout is clamped to it so nothing can be
#: drawn past the window edge (FR-102).
TEXT_AREA = pygame.Rect(60, 200, theme.SCREEN_WIDTH - 120, 130)

#: Footer band, flush with the bottom of the window.
FOOTER_RECT = pygame.Rect(0, theme.SCREEN_HEIGHT - theme.LAYOUT_FOOTER_HEIGHT,
                          theme.SCREEN_WIDTH, theme.LAYOUT_FOOTER_HEIGHT)

#: Top of the keyboard. Placed so the board clears the footer band by
#: LAYOUT_FOOTER_MARGIN, and so its caption (drawn above the board) clears the text
#: area. Asserted in tests/scenes/test_lesson_layout.py rather than trusted.
KEYBOARD_Y = (FOOTER_RECT.top - theme.LAYOUT_FOOTER_MARGIN
              - KeyboardRenderer.size()[1])


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
            self.ctx.resources, origin=((theme.SCREEN_WIDTH - kb_w) // 2, KEYBOARD_Y))
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
        self._line_sprites = []  # list of (virtual rect, surface)
        self._build_line_sprites()
        self._last_cursor_line = 0
        self.text_scroll_y = 0

        self._instruction_visible = True
        self._instruction_shade = pygame.Surface(
            (theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.SRCALPHA)
        self._instruction_shade.fill((20, 25, 35, 150))
        self._instruction_surfaces = self._build_instruction_surfaces()
        self.start_button = Button(
            INSTRUCTION_START_RECT, "Start Typing", self._dismiss_instructions,
            self.ctx.resources, bg_color=theme.COLOR_PRIMARY,
            font_size=theme.FONT_SIZE_BODY,
        )

        self._quit_requested = False
        self._update_keyboard_hint()

        # The "Esc to quit" hint never changes; render it once. Body-sized rather
        # than small — it is the only way out of the lesson, so a child has to be
        # able to read it.
        self._hint_surf = self.ctx.resources.text_surface(
            "Esc to quit and save progress",
            self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY),
            theme.COLOR_TEXT_MUTED,
        )
        self._hint_pos = self._hint_surf.get_rect(
            midleft=(60, FOOTER_RECT.centery)).topleft

        # HUD metrics are updated each frame; the renderer is cheap and drawing it
        # unconditionally avoids a one-frame clear/draw race under dirty-rect mode.

        # Crash recovery (FR-073): the row id reserved by the first checkpoint, and
        # the time since the last one. Both reset per attempt.
        self._attempt_row_id = None
        self._since_checkpoint = 0.0

    def on_exit(self) -> None:
        pass

    def _build_instruction_surfaces(self):
        """Cache the static keyboard guide so the overlay is cheap to redraw."""
        title_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_HEADING)
        body_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
        small_font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        return {
            "title": self.ctx.resources.text_surface(
                "Before you start", title_font, theme.COLOR_TEXT),
            "intro": self.ctx.resources.text_surface(
                "Use the on-screen keyboard to learn the right finger.",
                body_font, theme.COLOR_TEXT_MUTED),
            "lines": [self.ctx.resources.text_surface(text, small_font, theme.COLOR_TEXT)
                      for text in (
                          "• Type the key outlined on the keyboard next.",
                          "• Use the finger named above the keyboard.",
                          "• For a capital, hold the opposite hand's Shift key.",
                          "• Backspace corrects mistakes in Backspace mode.",
                          "• Press Escape to save and leave the lesson.",
                      )],
            "prompt": self.ctx.resources.text_surface(
                "Press Enter, Space, or click Start Typing",
                small_font, theme.COLOR_TEXT_MUTED),
            "start": self.ctx.resources.text_surface(
                "Start Typing", body_font, theme.COLOR_BUTTON_TEXT),
        }

    def _dismiss_instructions(self) -> None:
        self._instruction_visible = False
        self.start_button._hovered = False
        self.mark_dirty(pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))

    def _update_text_scroll(self) -> None:
        """Keep the next character visible while typing a long paragraph."""
        current = self.layout.rect_for(self.engine.cursor)
        if current is None:
            current = self.layout.rect_for(max(0, self.engine.cursor - 1))
        if current is None:
            return

        viewport_top = TEXT_AREA.top
        viewport_bottom = TEXT_AREA.bottom
        if current.top - self.text_scroll_y < viewport_top:
            self.text_scroll_y = current.top - viewport_top
        elif current.bottom - self.text_scroll_y > viewport_bottom:
            self.text_scroll_y = current.bottom - viewport_bottom

        content_bottom = self.layout.bounds().bottom if self.layout.glyphs else viewport_bottom
        max_scroll = max(0, content_bottom - viewport_bottom)
        self.text_scroll_y = max(0, min(self.text_scroll_y, max_scroll))

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
        if self._instruction_visible:
            if self.start_button.handle_event(event):
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Escape keeps its established meaning: leave and save.
                    self._quit_lesson()
                    return
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._dismiss_instructions()
                    return
                if event.unicode in TYPABLE:
                    # A child can begin immediately; do not lose that first key.
                    self._dismiss_instructions()
                else:
                    return
            elif event.type != pygame.MOUSEMOTION:
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._quit_lesson()
                return

            if event.key == pygame.K_BACKSPACE:
                self.engine.feed_key("\b")
                self.ctx.audio.play("key_click.wav")
                self._update_text_scroll()
                self._update_target_text_sprite()
                self._update_keyboard_hint()
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

                self._update_text_scroll()
                self._update_target_text_sprite()
                self._update_keyboard_hint()

                if self.engine.is_finished():
                    scored = self._finish(AttemptStatus.COMPLETE)
                    self.ctx.audio.play("success.wav")
                    self.ctx.states.change("results", attempt=scored, lesson=self.lesson)

    def update(self, dt: float) -> None:
        # Keep the HUD metrics in sync with the running attempt. The renderer is
        # cheap, so there is no need to throttle it.
        self.hud.update_metrics(self.engine.metrics())

        # Checkpoint on a timer, not per keystroke: database I/O on the keystroke
        # path would be felt as stutter on the target hardware (NFR-007).
        if self._has_started() and not self.engine.is_finished():
            self._since_checkpoint += dt
            if self._since_checkpoint >= self.ctx.progression.CHECKPOINT_INTERVAL_SEC:
                self._checkpoint()

    def render(self, surface) -> None:
        self.hud.render(surface)
        self.mark_dirty(self.hud.rect)

        self.keyboard.render(surface)
        self._render_target_text(surface)

        self._render_footer(surface)
        if self._instruction_visible:
            self._render_instructions(surface)

    def _render_footer(self, surface) -> None:
        """A distinct band at the bottom holding the quit hint.

        Drawn as a band with a top rule rather than floating text, so the keyboard
        has an unambiguous boundary to sit above and the hint reads as chrome rather
        than as part of the drill.
        """
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, FOOTER_RECT)
        pygame.draw.line(surface, theme.COLOR_LOCKED,
                         FOOTER_RECT.topleft, FOOTER_RECT.topright, 2)
        surface.blit(self._hint_surf, self._hint_pos)
        self.mark_dirty(FOOTER_RECT)

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
        # Scrolling can move many cached lines at once, so the viewport—not a
        # single virtual line rect—is the correct dirty region.
        self.mark_dirty(TEXT_AREA)
        self._last_cursor_line = current_line

    def _render_target_text(self, surface) -> None:
        """Draw the pre-computed layout. Positions never change during an attempt \u2014
        only the per-character colours \u2014 so nothing is measured here."""
        old_clip = surface.get_clip()
        surface.set_clip(TEXT_AREA)
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, TEXT_AREA, border_radius=10)
        pygame.draw.rect(surface, theme.COLOR_LOCKED, TEXT_AREA, width=2, border_radius=10)

        cursor = self.engine.cursor

        # A soft block behind the current character, plus the caret on its left
        # edge: two independent cues, so the position is unambiguous even where a
        # glyph is narrow (FR-101).
        current = self.layout.rect_for(cursor)
        if current is not None:
            current = current.move(0, -self.text_scroll_y)
            pygame.draw.rect(surface, theme.COLOR_CARD_BG, current, border_radius=4)

        # Blit the cached line surfaces instead of each glyph every frame.
        for rect, surf in self._line_sprites:
            if surf is not None:
                surface.blit(surf, (rect.x, rect.y - self.text_scroll_y))

        caret = self.layout.caret_rect(cursor).move(0, -self.text_scroll_y)
        pygame.draw.rect(surface, theme.COLOR_ACCENT, caret)
        surface.set_clip(old_clip)

    def _render_instructions(self, surface) -> None:
        """Render a modal-looking, child-readable keyboard guide."""
        surface.blit(self._instruction_shade, (0, 0))
        pygame.draw.rect(surface, theme.COLOR_CARD_BG, INSTRUCTION_PANEL, border_radius=18)
        pygame.draw.rect(surface, theme.COLOR_ACCENT, INSTRUCTION_PANEL, width=3,
                         border_radius=18)

        surfaces = self._instruction_surfaces
        cx = INSTRUCTION_PANEL.centerx
        surface.blit(surfaces["title"], surfaces["title"].get_rect(center=(cx, 165)))
        surface.blit(surfaces["intro"], surfaces["intro"].get_rect(center=(cx, 215)))
        for index, line in enumerate(surfaces["lines"]):
            surface.blit(line, line.get_rect(midleft=(300, 270 + index * 36)))
        surface.blit(surfaces["prompt"], surfaces["prompt"].get_rect(center=(cx, 445)))
        button_color = self.start_button.bg_color
        if self.start_button._hovered:
            button_color = tuple(max(0, channel - 20) for channel in button_color)
        pygame.draw.rect(surface, button_color, self.start_button.rect, border_radius=10)
        start_label = surfaces["start"]
        surface.blit(start_label, start_label.get_rect(center=self.start_button.rect.center))
