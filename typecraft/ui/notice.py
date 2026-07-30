"""ui/notice.py — teacher-facing warning banner.

Startup problems such as a malformed `settings.json` or a missing asset are
recorded on `AppContext.notices`. This bar renders them in every scene and
lets the teacher dismiss them with a click.
"""

import pygame

from typecraft.ui import theme


class NoticeBar:
    """Renders a stack of notice messages at the top of the window.

    The bar is intentionally simple: it reads the notices list from the
    AppContext, draws each as a coloured strip, and removes a notice when its
    strip is clicked. It does not block gameplay; it is drawn after the active
    scene so it appears as an translucent overlay.
    """

    #: Minimum height of one notice strip in pixels.
    STRIP_HEIGHT = 34
    #: Padding around the text.
    PADDING = 8

    def __init__(self, ctx):
        self.ctx = ctx
        self._rects = []  # (rect, notice_index) pairs from the last render

    def handle_event(self, event) -> bool:
        """Return True if a click hit a notice strip and dismissed it."""
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        for rect, idx in self._rects:
            if rect.collidepoint(event.pos):
                if 0 <= idx < len(self.ctx.notices):
                    self.ctx.notices.pop(idx)
                return True
        return False

    def render(self, surface) -> None:
        """Draw notices at the top of the window, tracking hit rects."""
        self._rects = []
        if not self.ctx.notices:
            return

        font = self.ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        y = 0
        width = surface.get_width()

        for idx, notice in enumerate(self.ctx.notices):
            text_surf = self.ctx.resources.text_surface(
                notice, font, theme.COLOR_TEXT)
            height = max(self.STRIP_HEIGHT, text_surf.get_height() + self.PADDING * 2)
            rect = pygame.Rect(0, y, width, height)
            self._rects.append((rect, idx))

            # Semi-opaque warning background so text remains readable over the scene.
            bg = pygame.Surface((width, height), pygame.SRCALPHA)
            bg.fill((255, 243, 224, 250))
            surface.blit(bg, (rect.x, rect.y))

            pygame.draw.rect(surface, theme.COLOR_ERROR, rect, width=2)
            surface.blit(text_surf, (self.PADDING, y + self.PADDING))

            y += height

