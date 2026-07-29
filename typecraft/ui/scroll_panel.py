"""
ui/scroll_panel.py

A clipping viewport over content taller than itself (FR-014, FR-026, FR-124).

Three screens laid content out beyond the 1280x720 window and simply let it fall
off the bottom: Profile Select past the 8th child, Lesson Select's fourth row of
cards, and the dashboard for any class bigger than about twelve. On a school
machine that means students who cannot be selected and lessons that cannot be
started — invisible, because nothing errors.

The model is deliberately simple: **children keep their positions in content
coordinates and never move.** The panel translates in two directions instead:

    render  — content coordinates are shifted up by `offset` and clipped
    input   — an incoming mouse position is shifted back down before dispatch

so a scene's hit-testing and layout code is identical whether it is scrolled or
not, and a scene cannot get the two out of step.
"""

from contextlib import contextmanager

import pygame

#: Pixels per wheel notch / arrow press. Roughly one row.
DEFAULT_STEP = 48


class ScrollPanel:
    def __init__(self, rect, content_height: int = 0, step: int = DEFAULT_STEP):
        self.rect = pygame.Rect(rect)
        self.step = step
        self.offset = 0
        self._content_height = 0
        self._dragging = False
        self._drag_anchor = 0
        self.set_content_height(content_height)

    # --- geometry ----------------------------------------------------------

    def set_content_height(self, height: int) -> None:
        """Call when the number of children changes; keeps the offset in range so
        deleting the last row cannot leave the view stranded past the end."""
        self._content_height = max(0, int(height))
        self.offset = min(self.offset, self.max_offset)

    @property
    def content_height(self) -> int:
        return self._content_height

    @property
    def max_offset(self) -> int:
        return max(0, self._content_height - self.rect.height)

    @property
    def scrollable(self) -> bool:
        return self.max_offset > 0

    def scroll_by(self, dy: int) -> None:
        self.offset = max(0, min(self.max_offset, self.offset + dy))

    def scroll_to(self, y: int) -> None:
        self.offset = max(0, min(self.max_offset, int(y)))

    def screen_rect(self, content_rect) -> pygame.Rect:
        """Where a content-space rect currently appears on screen.

        Content space is absolute in x — scenes centre against the window width —
        and relative in y, with 0 at the top of the content. So a scene lays its
        first row out at y = 0 and never has to know where the viewport sits.
        """
        return pygame.Rect(content_rect).move(0, self.rect.y - self.offset)

    def is_visible(self, content_rect) -> bool:
        return self.screen_rect(content_rect).colliderect(self.rect)

    def content_pos(self, pos):
        """Translate a screen position into content space (inverse of screen_rect)."""
        return (pos[0], pos[1] - self.rect.y + self.offset)

    # --- input -------------------------------------------------------------

    def handle_event(self, event) -> bool:
        """Consume scrolling input. Returns True if the panel used the event.

        Only acts on positions inside the viewport, so two panels on one screen
        (or a panel beside a fixed toolbar) cannot both react to one wheel notch.
        """
        if not self.scrollable:
            return False

        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_by(-event.y * self.step)
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            # Older SDL wheel encoding, still emitted by some drivers.
            if self.rect.collidepoint(event.pos):
                self.scroll_by(-self.step if event.button == 4 else self.step)
                return True
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self._drag_anchor = event.pos[1]
                return True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 2 and self._dragging:
            self._dragging = False
            return True

        if event.type == pygame.MOUSEMOTION and self._dragging:
            self.scroll_by(self._drag_anchor - event.pos[1])
            self._drag_anchor = event.pos[1]
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PAGEDOWN:
                self.scroll_by(self.rect.height)
                return True
            if event.key == pygame.K_PAGEUP:
                self.scroll_by(-self.rect.height)
                return True
            if event.key == pygame.K_HOME:
                self.scroll_to(0)
                return True
            if event.key == pygame.K_END:
                self.scroll_to(self.max_offset)
                return True

        return False

    def translated(self, event):
        """A copy of a mouse event in content coordinates, or None if it happened
        outside the viewport.

        Returning None is the important half: without it a click just below the
        panel would be translated into a child's row and select the wrong student.
        """
        if not hasattr(event, "pos"):
            return event
        if not self.rect.collidepoint(event.pos):
            return None
        return pygame.event.Event(event.type, {**event.dict, "pos": self.content_pos(event.pos)})

    # --- rendering ---------------------------------------------------------

    @contextmanager
    def clipped(self, surface):
        """Restrict drawing to the viewport for the duration of the block."""
        previous = surface.get_clip()
        surface.set_clip(self.rect)
        try:
            yield
        finally:
            surface.set_clip(previous)

    def render_children(self, surface, widgets) -> None:
        """Draw widgets whose `rect` is in content coordinates.

        Each rect is moved for the duration of its own draw and put straight back,
        so the widget's stored geometry stays authoritative and hit-testing (which
        works in content space) keeps matching it.
        """
        with self.clipped(surface):
            for widget in widgets:
                if not self.is_visible(widget.rect):
                    continue
                original = widget.rect
                widget.rect = self.screen_rect(original)
                try:
                    widget.render(surface)
                finally:
                    widget.rect = original

    def render_scrollbar(self, surface, color, track_color=None, width: int = 8) -> None:
        """A minimal indicator, drawn only when there is something to scroll — a
        child needs to see that more exists below."""
        if not self.scrollable:
            return
        x = self.rect.right - width - 2
        if track_color is not None:
            pygame.draw.rect(surface, track_color,
                             pygame.Rect(x, self.rect.y, width, self.rect.height),
                             border_radius=width // 2)
        visible_fraction = self.rect.height / self._content_height
        thumb_height = max(24, int(self.rect.height * visible_fraction))
        travel = self.rect.height - thumb_height
        thumb_y = self.rect.y + (int(travel * self.offset / self.max_offset) if travel else 0)
        pygame.draw.rect(surface, color, pygame.Rect(x, thumb_y, width, thumb_height),
                         border_radius=width // 2)
