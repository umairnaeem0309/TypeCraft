"""One product, not nine screens (FR-004, FR-104).

`Rect(20, 20, 120, 50), "Back"` was copy-pasted into six scenes and
`FONT_SIZE_TITLE - 8` into six more places. The convention existed; it just lived in
six copies, so changing the header meant six edits and drift went unnoticed. These
tests assert the shared chrome is actually shared, which is the only way a
convention stays true.

They deliberately check *sameness* rather than specific values, so the design can be
restyled in `ui/screen.py` and `ui/theme.py` without touching this file.
"""

import pygame
import pytest

from typecraft.ui import screen, theme

#: Every screen a child or teacher can reach that offers a way back.
SCENES_WITH_BACK = [
    "profile_select", "lesson_select", "mode_select",
    "leaderboard", "teacher_dashboard", "settings",
]

ALL_SCENES = SCENES_WITH_BACK + ["main_menu", "lesson", "results"]


@pytest.fixture
def app(app_ctx, display, attempt_factory):
    from typecraft.core.game import build_state_manager

    build_state_manager(app_ctx)
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    app_ctx.attempt = attempt_factory(student.id, accuracy=95.0)
    app_ctx.progression.score(app_ctx.attempt, student)
    return app_ctx


def enter(app, name):
    lesson = app.lessons.first_lesson()
    kwargs = {
        "mode_select": {"lesson": lesson},
        "lesson": {"lesson": lesson, "mode_key": "lock_on_error"},
        "results": {"attempt": app.attempt, "lesson": lesson},
    }.get(name, {})
    app.states.change(name, **kwargs)
    return app.states.current


# --------------------------------------------------------------------- back button

@pytest.mark.parametrize("name", SCENES_WITH_BACK)
def test_every_back_button_is_in_the_same_place(app, name):
    """A child should not have to hunt for Back — it is the same target on every
    screen, which is only true if they all come from one definition."""
    scene = enter(app, name)
    assert tuple(scene.back_button.rect) == tuple(screen.BACK_RECT)


@pytest.mark.parametrize("name", SCENES_WITH_BACK)
def test_every_back_button_looks_the_same(app, name):
    """Back is never the action to draw a child towards, so it is grey everywhere."""
    scene = enter(app, name)
    assert scene.back_button.bg_color == theme.COLOR_NEUTRAL
    assert scene.back_button.label == "Back"


def test_the_back_buttons_are_all_the_same_object_shape(app):
    """Same size as well as same position — one of the six used to differ in colour
    only, which is the kind of drift copy-paste produces."""
    rects, colours = set(), set()
    for name in SCENES_WITH_BACK:
        scene = enter(app, name)
        rects.add(tuple(scene.back_button.rect))
        colours.add(tuple(scene.back_button.bg_color))
    assert len(rects) == 1, f"{len(rects)} different Back geometries"
    assert len(colours) == 1, f"{len(colours)} different Back colours"


def test_no_scene_hard_codes_the_back_button_any_more():
    """Guards the consolidation itself: a new scene must use the shared helper."""
    import pathlib

    import typecraft
    offenders = []
    for path in (pathlib.Path(typecraft.__path__[0]) / "scenes").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if 'pygame.Rect(20, 20, 120, 50), "Back"' in text:
            offenders.append(path.name)
    assert not offenders, f"hard-coded Back button in {offenders}"


# --------------------------------------------------------------------- typography

def test_page_titles_all_use_one_named_size():
    """Six scenes each wrote `FONT_SIZE_TITLE - 8`. Naming it means the header can be
    restyled in one place."""
    import pathlib

    import typecraft
    offenders = []
    for path in (pathlib.Path(typecraft.__path__[0]) / "scenes").glob("*.py"):
        if "FONT_SIZE_TITLE - 8" in path.read_text(encoding="utf-8"):
            offenders.append(path.name)
    assert not offenders, f"ad-hoc title size in {offenders}"


def test_the_type_scale_is_ordered():
    """A scale only reads as a scale if the steps are distinct and ordered."""
    sizes = [theme.FONT_SIZE_SMALL, theme.FONT_SIZE_BODY, theme.FONT_SIZE_HEADING,
             theme.FONT_SIZE_PAGE_TITLE, theme.FONT_SIZE_TITLE]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == len(sizes)


def test_body_text_is_large_enough_for_a_child(app):
    """FR-104: body >= 24 px, drill text >= 32 px at the design size."""
    assert theme.FONT_SIZE_BODY >= 24
    assert theme.FONT_SIZE_TARGET_TEXT >= 32


def test_the_spacing_scale_is_ordered():
    steps = [theme.SPACE_XS, theme.SPACE_SM, theme.SPACE_MD,
             theme.SPACE_LG, theme.SPACE_XL, theme.SPACE_XXL]
    assert steps == sorted(steps)
    assert len(set(steps)) == len(steps)


# --------------------------------------------------------------------- colour language

def test_button_colours_carry_one_consistent_meaning(app):
    """Colour is the first thing a child reads. Grey must never be the primary
    action, and the danger colour must never be a routine one."""
    menu = enter(app, "main_menu")
    colours = {w.label: tuple(w.bg_color) for w in menu.widgets}

    assert colours["PLAY"] == tuple(theme.COLOR_PRIMARY), "the main action must be primary"
    assert tuple(theme.COLOR_NEUTRAL) not in [
        c for label, c in colours.items() if label == "PLAY"]


def test_the_danger_colour_is_only_used_for_destructive_actions(app):
    """A red button anywhere else teaches a child to ignore red."""
    dashboard = enter(app, "teacher_dashboard")
    red = tuple(theme.COLOR_ERROR)

    for _summary, button in dashboard.reset_buttons:
        assert tuple(button.bg_color) == red, "Reset should be the danger colour"
    assert tuple(dashboard.back_button.bg_color) != red
    assert tuple(dashboard.cancel_button.bg_color) != red


# --------------------------------------------------------------------- layout hygiene

@pytest.mark.parametrize("name", ALL_SCENES)
def test_no_widget_falls_outside_the_design_canvas(app, name):
    """Everything is authored in 1280x720 and scaled to the window, so anything
    outside the canvas is invisible at every resolution."""
    scene = enter(app, name)
    canvas = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)

    for attr in dir(scene):
        if attr.startswith("__"):
            continue
        value = getattr(scene, attr, None)
        widgets = value if isinstance(value, list) else [value]
        for widget in widgets:
            rect = getattr(widget, "rect", None)
            if isinstance(rect, pygame.Rect) and rect.width and rect.height:
                # Scroll-panel children live in content space, not screen space.
                if getattr(scene, "panel", None) is not None and rect.height <= 60:
                    continue
                assert canvas.colliderect(rect), f"{name}.{attr} at {tuple(rect)} is off-canvas"


@pytest.mark.parametrize("name", ALL_SCENES)
def test_every_interactive_target_is_large_enough(app, name):
    """A child with a trackpad needs a target they can hit; 44 px is the usual floor
    and every control here is at least that tall."""
    scene = enter(app, name)
    small = []
    for attr in dir(scene):
        if attr.startswith("__"):
            continue
        value = getattr(scene, attr, None)
        candidates = value if isinstance(value, list) else [value]
        for widget in candidates:
            if isinstance(widget, tuple):
                widget = widget[-1]
            if hasattr(widget, "on_click") and hasattr(widget, "rect"):
                if widget.rect.height < 44:
                    small.append((attr, tuple(widget.rect)))
    assert not small, f"{name}: controls under 44 px tall: {small}"


# --------------------------------------------------------------------- header rhythm

def test_the_header_rhythm_has_one_definition():
    """Titles were positioned by six copies of `back_button.rect.centery + 8`, and
    subtitles had drifted to 105 in one scene and 108 in three others."""
    import pathlib

    import typecraft
    offenders = []
    for path in (pathlib.Path(typecraft.__path__[0]) / "scenes").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "back_button.rect.centery + 8" in text:
            offenders.append(f"{path.name}: ad-hoc title baseline")
        if "// 2, 105))" in text or "// 2, 108))" in text:
            offenders.append(f"{path.name}: ad-hoc subtitle baseline")
    assert not offenders, offenders


def test_the_title_stays_aligned_with_the_back_button():
    """TITLE_Y is derived from BACK_RECT, so moving the button moves the title with
    it rather than leaving the two visibly out of line."""
    assert screen.TITLE_Y == screen.BACK_RECT.centery + 8


def test_the_subtitle_sits_below_the_title_and_above_the_content():
    header = screen.PageHeader.__new__(screen.PageHeader)
    header.subtitle = "x"
    assert screen.SUBTITLE_Y > screen.TITLE_Y
    assert header.content_top > screen.SUBTITLE_Y
