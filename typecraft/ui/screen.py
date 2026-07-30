"""
ui/screen.py

The chrome every screen shares: a page title, an optional subtitle, a Back button,
and a footer note.

Before this, `Rect(20, 20, 120, 50), "Back"` was copy-pasted into six scenes and
`FONT_SIZE_TITLE - 8` into six, and four scenes each built their own italic subtitle
font. The convention already existed — it just lived in six places, so a change to
the header meant six edits and any drift went unnoticed.

Everything is authored in the 1280x720 design canvas; `pygame.SCALED` maps it to the
real window (see core/window.py), so nothing here needs to know the display size.
"""

import pygame

from typecraft.ui import theme
from typecraft.ui.button import Button

#: The one Back button geometry, top-left on every screen that has one.
BACK_RECT = pygame.Rect(theme.SPACE_LG, theme.SPACE_LG, 120, 50)

#: Page title baseline. Derived from BACK_RECT so the title stays optically aligned
#: with the Back button instead of six scenes each writing
#: `self.back_button.rect.centery + 8` and hoping.
TITLE_Y = BACK_RECT.centery + 8

#: Subtitle baseline. Scenes had drifted to 105 and 108 independently.
SUBTITLE_Y = 108

#: Footer band, matching the lesson screen so the app has one footer, not two.
FOOTER_RECT = pygame.Rect(0, theme.SCREEN_HEIGHT - theme.LAYOUT_FOOTER_HEIGHT,
                          theme.SCREEN_WIDTH, theme.LAYOUT_FOOTER_HEIGHT)


def back_button(ctx, destination="main_menu", label="Back") -> Button:
    """The standard Back button. Grey everywhere, because it is never the action a
    child should be drawn towards."""
    return Button(BACK_RECT.copy(), label,
                  lambda: ctx.states.change(destination), ctx.resources,
                  bg_color=theme.COLOR_NEUTRAL)


class PageHeader:
    """Title, optional subtitle, and the vertical rhythm beneath them.

    Cached surfaces: a page title never changes while its scene is open, so it is
    rasterised once rather than every frame (NFR-007).
    """

    def __init__(self, ctx, title: str, subtitle: str = ""):
        self.ctx = ctx
        self.title = title
        self.subtitle = subtitle

        title_font = ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_PAGE_TITLE)
        self._title_surf = ctx.resources.text_surface(title, title_font, theme.COLOR_TEXT)

        self._subtitle_surf = None
        if subtitle:
            font = pygame.font.Font(None, theme.FONT_SIZE_BODY)
            font.set_italic(True)
            self._subtitle_surf = ctx.resources.text_surface(
                subtitle, font, theme.COLOR_TEXT_MUTED)

    @property
    def content_top(self) -> int:
        """Where a scene's own content may start, clear of the header."""
        return (SUBTITLE_Y if self.subtitle else TITLE_Y) + theme.SPACE_XL

    def render(self, surface) -> None:
        cx = theme.SCREEN_WIDTH // 2
        surface.blit(self._title_surf, self._title_surf.get_rect(center=(cx, TITLE_Y)))
        if self._subtitle_surf is not None:
            surface.blit(self._subtitle_surf,
                         self._subtitle_surf.get_rect(center=(cx, SUBTITLE_Y)))


def render_footer(ctx, surface, note: str, align="left") -> pygame.Rect:
    """Draw the shared footer band with a note in it.

    Returns the band's rect so a scene using dirty-rect rendering can mark it.
    """
    pygame.draw.rect(surface, theme.COLOR_CARD_BG, FOOTER_RECT)
    pygame.draw.line(surface, theme.COLOR_LOCKED,
                     FOOTER_RECT.topleft, FOOTER_RECT.topright, 2)

    font = ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
    surf = ctx.resources.text_surface(note, font, theme.COLOR_TEXT_MUTED)
    if align == "center":
        position = surf.get_rect(center=FOOTER_RECT.center)
    else:
        position = surf.get_rect(midleft=(theme.SPACE_XL, FOOTER_RECT.centery))
    surface.blit(surf, position)
    return FOOTER_RECT
