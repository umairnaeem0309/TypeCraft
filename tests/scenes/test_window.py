"""Window sizing and fullscreen (FR-005 revised, 2026-07-31).

TypeCraft draws into a fixed 1280x720 design canvas and lets `pygame.SCALED` map it
onto the real window. That part was already right. What was wrong: the window always
*opened* at exactly 1280x720, so the app looked correct on a 1366x768 laptop and
like a small box on a 1920x1080 desktop — worse on newer hardware than on old.

`initial_window_size()` is pure, so the rule is tested at resolutions no developer
machine has: 4K, ultra-wide, and the awkward small panels a donated school PC has.
"""

import pygame
import pytest

from typecraft.core import window
from typecraft.ui import theme

DESIGN_W, DESIGN_H = window.DESIGN_SIZE
ASPECT = DESIGN_W / DESIGN_H


def aspect_of(size):
    return size[0] / size[1]


# --------------------------------------------------------------------- sizing rule

@pytest.mark.parametrize("desktop,label", [
    ((1366, 768), "common budget laptop"),
    ((1440, 900), "MacBook-class laptop"),
    ((1536, 864), "scaled 1080p laptop"),
    ((1600, 900), "laptop"),
    ((1920, 1080), "desktop 1080p"),
    ((1920, 1200), "16:10 desktop"),
    ((2560, 1440), "desktop 1440p"),
    ((3840, 2160), "4K desktop"),
    ((3440, 1440), "ultra-wide"),
    ((1024, 768), "old 4:3 school PC"),
    ((1280, 720), "exactly the design size"),
])
def test_the_window_fits_the_desktop_and_keeps_its_shape(desktop, label):
    """The two properties that matter on every screen: it fits, and it is not
    stretched. A distorted canvas would misalign every click."""
    size = window.initial_window_size(desktop)

    assert size[0] <= desktop[0], f"too wide for {label}"
    assert size[1] <= desktop[1], f"too tall for {label}"
    assert aspect_of(size) == pytest.approx(ASPECT, abs=0.01), f"stretched on {label}"


@pytest.mark.parametrize("desktop", [(1920, 1080), (2560, 1440), (3840, 2160)])
def test_a_larger_desktop_gets_a_larger_window(desktop):
    """The actual defect: 1280x720 on a 1440p screen is a postage stamp."""
    size = window.initial_window_size(desktop)
    assert size[0] > DESIGN_W, f"{desktop} still opens at the design size"


def test_a_laptop_screen_is_not_overfilled():
    """Leaving room for the taskbar and title bar, so the window is not partly
    off-screen and undraggable."""
    size = window.initial_window_size((1366, 768))
    assert size[1] <= 768 * 0.95


def test_the_sizing_rule_is_advisory_only():
    """`initial_window_size()` is no longer applied to the OS window: the code that
    did used pygame's private `_sdl2.video.Window`, whose finalizer destroyed the
    display and crashed the app (see tests/integration/test_no_native_crash.py).
    The rule is kept because it documents the intended presentation size and is what
    fullscreen effectively achieves — but nothing may call into `_sdl2` again."""
    assert not hasattr(window, "apply_window_size"), (
        "the unsafe OS-window resize must stay removed")
    assert not hasattr(window, "_resize_os_window")


def test_the_window_never_grows_absurdly_on_a_4k_panel():
    """A 3x window would be mostly empty, and the upscale costs fill-rate on
    integrated graphics for nothing (NFR-006)."""
    size = window.initial_window_size((3840, 2160))
    assert size[0] <= DESIGN_W * window.MAX_SCALE


def test_a_small_screen_still_gets_a_usable_window():
    """On a 1024x768 panel the design size does not fit, so it must scale down —
    but not so far that 40 px drill text stops being legible for a child."""
    size = window.initial_window_size((1024, 768))
    assert size[0] <= 1024
    assert size[0] >= DESIGN_W * window.MIN_SCALE


def test_an_ultrawide_desktop_is_limited_by_its_height():
    """3440x1440 has width to spare; the height is the binding constraint, and the
    result must not be a letterboxed sliver."""
    size = window.initial_window_size((3440, 1440))
    assert size[1] <= 1440 * window.DESKTOP_FRACTION
    assert aspect_of(size) == pytest.approx(ASPECT, abs=0.01)


def test_an_unknown_desktop_size_falls_back_to_the_design_size():
    """Headless and odd drivers report nonsense; a working window beats a clever
    one."""
    assert window.initial_window_size((0, 0)) == window.DESIGN_SIZE
    assert window.initial_window_size((-1, -1)) == window.DESIGN_SIZE


def test_sizing_is_deterministic():
    """Same screen, same window — no drift between launches."""
    assert window.initial_window_size((1920, 1080)) == window.initial_window_size((1920, 1080))


# --------------------------------------------------------------------- the canvas

def test_the_logical_canvas_matches_the_theme(display):
    """Every scene and every layout test assumes these numbers; the window module
    must not disagree with `theme`."""
    assert window.DESIGN_SIZE == (theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)


def test_the_drawing_surface_stays_the_design_size_whatever_the_window(app_ctx, display,
                                                                      monkeypatch):
    """The property that makes all the hard-coded scene coordinates safe: however
    large the window, scenes still draw into 1280x720."""
    from typecraft.core.game import Game

    monkeypatch.setattr(window, "create_display", lambda fullscreen=False: display)
    monkeypatch.setattr(window, "desktop_size", lambda: (2560, 1440))

    game = Game()
    try:
        assert game.screen.get_size() == window.DESIGN_SIZE
    finally:
        game.ctx.db.close()


def test_scenes_render_correctly_regardless_of_window_size(app_ctx, display, monkeypatch):
    """Sanity check that the canvas indirection does not change what a scene draws:
    the same scene rendered under two different notional desktops is identical."""
    from typecraft.core.game import build_state_manager

    build_state_manager(app_ctx)
    app_ctx.profiles.create("Amina", "avatar_fox")

    frames = []
    for desktop in ((1366, 768), (2560, 1440)):
        monkeypatch.setattr(window, "desktop_size", lambda d=desktop: d)
        app_ctx.states.change("main_menu")
        display.fill(theme.COLOR_BG)
        app_ctx.states.render(display)
        frames.append(pygame.image.tostring(display, "RGB"))

    assert frames[0] == frames[1], "the canvas contents depend on the window size"


# --------------------------------------------------------------------- fullscreen

def test_fullscreen_is_toggled_by_f11_and_alt_enter(app_ctx, display, monkeypatch):
    """FR-005 revised. Both bindings, because F11 is the convention and Alt+Enter is
    what a Windows user tries first."""
    from typecraft.core.game import Game

    monkeypatch.setattr(window, "create_display", lambda fullscreen=False: display)

    toggles = []
    monkeypatch.setattr(window, "toggle_fullscreen",
                        lambda: (toggles.append(True), len(toggles) % 2 == 1)[1])

    game = Game()
    try:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0))
        game._process_events()
        assert len(toggles) == 1 and game.fullscreen is True

        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_RETURN, mod=pygame.KMOD_ALT, unicode="\r"))
        game._process_events()
        assert len(toggles) == 2 and game.fullscreen is False
    finally:
        game.ctx.db.close()


def test_a_plain_return_does_not_toggle_fullscreen(app_ctx, display, monkeypatch):
    """Return submits a PIN and a profile name; only Alt+Enter is the window
    shortcut, or a teacher would flip to fullscreen while typing."""
    from typecraft.core.game import Game

    monkeypatch.setattr(window, "create_display", lambda fullscreen=False: display)
    toggles = []
    monkeypatch.setattr(window, "toggle_fullscreen", lambda: toggles.append(True))

    game = Game()
    try:
        pygame.event.post(pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r"))
        game._process_events()
        assert toggles == []
    finally:
        game.ctx.db.close()


def test_a_resize_repaints_the_whole_canvas(app_ctx, display, monkeypatch):
    """Under dirty-rect mode a resize must invalidate everything, or the new window
    shows stale fragments of the old frame."""
    from typecraft.core.game import Game

    monkeypatch.setattr(window, "create_display", lambda fullscreen=False: display)

    game = Game()
    try:
        game.states.current.dirty_rects.clear()
        pygame.event.post(pygame.event.Event(pygame.VIDEORESIZE, size=(1600, 900),
                                             w=1600, h=900))
        game._process_events()

        dirty = game.states.current.dirty_rects
        assert dirty, "a resize left nothing marked dirty"
        assert dirty[-1].size == window.DESIGN_SIZE
    finally:
        game.ctx.db.close()


def test_toggling_fullscreen_does_not_move_any_widget(app_ctx, display, monkeypatch):
    """SCALED letterboxes rather than reflowing, so coordinates must be untouched —
    otherwise every click target would shift on toggle."""
    from typecraft.core.game import Game

    monkeypatch.setattr(window, "create_display", lambda fullscreen=False: display)
    monkeypatch.setattr(window, "toggle_fullscreen", lambda: True)

    game = Game()
    try:
        before = [tuple(w.rect) for w in game.states.current.widgets]
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11, mod=0))
        game._process_events()
        after = [tuple(w.rect) for w in game.states.current.widgets]
        assert before == after
    finally:
        game.ctx.db.close()


def test_a_screen_that_fits_the_canvas_natively_is_never_downscaled():
    """1366x768 — the commonest machine in a school lab — has room for 1280x720.
    Shrinking it to 0.96 to respect DESKTOP_FRACTION would blur every glyph for no
    gain, so a native fit always wins."""
    for desktop in ((1366, 768), (1440, 900), (1280, 800)):
        size = window.initial_window_size(desktop)
        assert size[0] >= DESIGN_W, f"{desktop} was needlessly downscaled to {size}"


def test_only_genuinely_smaller_screens_are_downscaled():
    """A 1024x768 panel cannot show 1280 px wide, so it must scale down."""
    assert window.initial_window_size((1024, 768))[0] < DESIGN_W


def test_a_short_screen_leaves_room_for_the_title_bar():
    """1280x720 exactly: the canvas fits the width but there is no room for window
    chrome, so it must not claim a native fit and end up partly off-screen."""
    size = window.initial_window_size((1280, 720))
    assert size[1] <= 720
