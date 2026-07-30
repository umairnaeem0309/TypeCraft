"""
core/window.py

Choosing how big the window opens, and switching to fullscreen (FR-005 revised).

TypeCraft draws into a fixed 1280x720 **design canvas**: every scene, widget and
test reasons in those coordinates, and `pygame.SCALED` maps that canvas onto
whatever the real window happens to be, translating mouse positions back for us.
That is what makes the app resolution-independent without any scene knowing.

What the canvas does *not* decide is how large the window should be when it opens.
Fixed at 1280x720 it filled a 1366x768 laptop screen nicely but sat as a small
box on a 1920x1080 desktop and a postage stamp on 2560x1440 — the app looked
broken on exactly the newer hardware a school is most likely to have donated.

`initial_window_size()` is a pure function so the sizing rule can be tested at
resolutions no developer machine has.
"""

import pygame

#: The design canvas. All layout is authored against this; never change it lightly,
#: because every scene's coordinates and every layout test assume it.
DESIGN_SIZE = (1280, 720)

#: Fraction of the desktop the window may occupy, leaving room for the taskbar and
#: window chrome so the title bar is never pushed off-screen.
DESKTOP_FRACTION = 0.9

#: Never scale below this: past it, 40 px drill text stops being comfortably legible
#: for a child, which matters more than fitting an unusually small screen.
MIN_SCALE = 0.75

#: Never scale above this. On a 4K panel a 3x window would be mostly empty space,
#: and the upscale costs fill-rate on integrated graphics for no benefit (NFR-006).
MAX_SCALE = 2.0

#: Vertical room left for the title bar and taskbar when deciding whether the design
#: canvas fits a screen 1:1.
CHROME_ALLOWANCE = 48


def initial_window_size(desktop_size, design_size=DESIGN_SIZE) -> tuple:
    """Largest window that fits the desktop while preserving the design aspect.

    Args:
        desktop_size: (width, height) of the display, as pygame reports it.
        design_size: the logical canvas being scaled.

    Returns:
        (width, height) in physical pixels, aspect-matched to `design_size` so
        `SCALED` never has to letterbox at startup.
    """
    design_w, design_h = design_size
    desktop_w, desktop_h = desktop_size

    if desktop_w <= 0 or desktop_h <= 0:      # headless / unknown display
        return design_size

    scale = min(desktop_w * DESKTOP_FRACTION / design_w,
                desktop_h * DESKTOP_FRACTION / design_h)

    # Never scale *down* when the canvas fits natively. A 1366x768 laptop — the
    # commonest machine in a school lab — has room for 1280x720, and shrinking it to
    # 0.96 to respect DESKTOP_FRACTION would blur every glyph for no gain. Only
    # genuinely smaller screens get a downscale.
    if design_w <= desktop_w and design_h + CHROME_ALLOWANCE <= desktop_h:
        scale = max(1.0, scale)

    scale = max(MIN_SCALE, min(MAX_SCALE, scale))

    return (int(design_w * scale), int(design_h * scale))


def desktop_size() -> tuple:
    """The primary display's size, or the design size if pygame cannot say.

    Wrapped because `get_desktop_sizes()` needs the display module initialised and
    returns nothing useful under the dummy driver used by the tests.
    """
    try:
        sizes = pygame.display.get_desktop_sizes()
    except pygame.error:
        return DESIGN_SIZE
    return sizes[0] if sizes else DESIGN_SIZE


def create_display(fullscreen: bool = False):
    """Open the window and return its 1280x720 logical surface.

    `SCALED` is what keeps the surface at the design size whatever the window does;
    `RESIZABLE` lets a teacher drag the window; `DOUBLEBUF` avoids tearing.
    """
    flags = pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE
    if fullscreen:
        flags |= pygame.FULLSCREEN

    surface = pygame.display.set_mode(DESIGN_SIZE, flags,
                                      vsync=0)
    pygame.display.set_caption("TypeCraft")
    return surface


def apply_window_size(size) -> None:
    """Resize the OS window without disturbing the logical canvas.

    Called once at startup so the app opens at a sensible size for the screen it
    finds itself on. Failures are swallowed: an unusual driver refusing the resize
    should leave a working 1280x720 window, not stop the class typing.
    """
    try:
        window = pygame.display.get_wm_info().get("window")
    except pygame.error:
        window = None
    if not window:
        return

    try:
        pygame.display.set_mode(
            DESIGN_SIZE,
            pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE,
            vsync=0,
        )
        pygame.display.get_surface()
        _resize_os_window(size)
    except pygame.error:
        pass


def _resize_os_window(size) -> None:
    """Ask SDL to resize the window itself, leaving the scaled canvas alone."""
    try:
        from pygame._sdl2.video import Window  # noqa: PLC0415 - optional backend
    except ImportError:
        return
    try:
        window = Window.from_display_module()
        window.size = size
        window.position = pygame.WINDOWPOS_CENTERED
    except Exception:      # pragma: no cover - backend-specific
        pass


def toggle_fullscreen() -> bool:
    """Flip between fullscreen and windowed. Returns the new fullscreen state.

    With `SCALED` this keeps the logical surface at 1280x720 and letterboxes as
    needed, so no layout changes and no coordinates move.
    """
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        return bool(pygame.display.get_surface()
                    and pygame.display.get_surface().get_flags() & pygame.FULLSCREEN)
    surface = pygame.display.get_surface()
    return bool(surface and surface.get_flags() & pygame.FULLSCREEN)
