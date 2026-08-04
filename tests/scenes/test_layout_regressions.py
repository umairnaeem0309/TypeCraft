"""Layout and colour regressions reported from playtesting (2026-07-31).

Four faults a user found by looking at the running app, which no existing test
could have caught because they are about geometry and meaning rather than
behaviour:

  1. the Results buttons all read as equally important
  2. the on-screen keyboard overlapped the lesson footer by 5 px
  3. the reset confirmation read "Reset Amina?", as though the child were being
     deleted rather than their work
  4. the Settings screen used a narrow centre strip of a 1280x720 window

Geometry is asserted arithmetically here so it stays fixed. Everything is in the
development source; the release folder is regenerated from it by
`scripts/build_release.py`.
"""

import pygame
import pytest

from typecraft.ui import theme


# --------------------------------------------------------------------- 1. results colours

@pytest.fixture
def results(app_ctx, display, attempt_factory):
    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    attempt = attempt_factory(student.id, accuracy=95.0)
    app_ctx.progression.score(attempt, student)

    from typecraft.core.game import build_state_manager
    build_state_manager(app_ctx)
    app_ctx.states.change("results", attempt=attempt, lesson=app_ctx.lessons.first_lesson())
    return app_ctx.states.current


def test_the_results_buttons_are_colour_coded_by_intent(results):
    """Colour carries the meaning before the word does: grey to go back, green for
    the way onward, orange for the optional detour."""
    retry, continue_button, leaderboard = results.buttons

    assert retry.label == "Retry"
    assert retry.bg_color == theme.COLOR_NEUTRAL

    assert continue_button.label == "Continue"
    assert continue_button.bg_color == theme.COLOR_PRIMARY

    assert leaderboard.label == "Leaderboard"
    assert leaderboard.bg_color == theme.COLOR_WARNING


def test_the_three_results_buttons_have_distinct_colours(results):
    colours = {tuple(b.bg_color) for b in results.buttons}
    assert len(colours) == 3, "two buttons share a colour, so the coding says nothing"


def test_the_results_buttons_stay_inside_the_window(results):
    window = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
    for button in results.buttons:
        assert window.contains(button.rect), f"{button.label} is off-screen"


# --------------------------------------------------------------------- 2. lesson spacing

def test_the_keyboard_does_not_overlap_the_footer():
    """The reported defect, as arithmetic. The board is 245 px tall and used to
    start at y=440, ending at 685, while the hint sat at 680."""
    from typecraft.scenes.lesson import FOOTER_RECT, KEYBOARD_Y
    from typecraft.ui.keyboard_renderer import KeyboardRenderer

    keyboard_bottom = KEYBOARD_Y + KeyboardRenderer.size()[1]

    assert keyboard_bottom <= FOOTER_RECT.top
    assert FOOTER_RECT.top - keyboard_bottom >= theme.LAYOUT_FOOTER_MARGIN


def test_the_keyboard_caption_clears_the_drill_text(app_ctx, display):
    """The caption is drawn *above* the board, so it must not land on the text."""
    from typecraft.scenes.lesson import KEYBOARD_Y, TEXT_AREA

    caption_y = KEYBOARD_Y - theme.FONT_SIZE_BODY - 8
    assert caption_y > TEXT_AREA.bottom


def test_the_footer_is_a_readable_band_not_a_thin_line():
    """"Increase the size of the footer": body-sized text in a band tall enough for
    it, flush with the bottom of the window."""
    from typecraft.scenes.lesson import FOOTER_RECT

    assert FOOTER_RECT.height >= 56
    assert FOOTER_RECT.bottom == theme.SCREEN_HEIGHT
    assert FOOTER_RECT.width == theme.SCREEN_WIDTH


def test_the_lesson_hint_sits_inside_the_footer_band(app_ctx, display):
    from typecraft.scenes.lesson import FOOTER_RECT, LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="lock_on_error")

    hint = pygame.Rect(scene._hint_pos, scene._hint_surf.get_size())
    assert FOOTER_RECT.contains(hint), "the quit hint escapes its own footer band"
    assert hint.height >= 20, "the hint should be body-sized, not small print"


def test_no_lesson_element_overlaps_another(app_ctx, display):
    """One assertion covering the whole screen: HUD, drill text, keyboard and footer
    must occupy four separate horizontal bands."""
    from typecraft.scenes.lesson import FOOTER_RECT, TEXT_AREA, LessonScene
    from typecraft.ui.keyboard_renderer import KeyboardRenderer

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="lock_on_error")

    kb_h = KeyboardRenderer.size()[1]
    bands = [
        ("hud", scene.hud.rect.top, scene.hud.rect.bottom),
        ("text", TEXT_AREA.top, TEXT_AREA.bottom),
        ("keyboard", scene.keyboard.origin[1], scene.keyboard.origin[1] + kb_h),
        ("footer", FOOTER_RECT.top, FOOTER_RECT.bottom),
    ]
    for (name_a, _top_a, bottom_a), (name_b, top_b, _bottom_b) in zip(bands, bands[1:]):
        assert bottom_a <= top_b, f"{name_a} overlaps {name_b}"

    assert bands[-1][2] <= theme.SCREEN_HEIGHT


def test_paragraph_lessons_scroll_beyond_the_fixed_text_viewport(app_ctx, display):
    """Long lessons use a clipped virtual viewport rather than rendering off-screen."""
    from typecraft.scenes.lesson import LessonScene, TEXT_AREA

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.get("t5l4"), mode_key="free_advance")

    assert scene.layout.bounds().bottom > TEXT_AREA.bottom
    for ch in scene.engine.target:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
        if scene.__class__.__name__ != "LessonScene" or scene.text_scroll_y > 0:
            break
    assert scene.text_scroll_y > 0, "typing through the paragraph never scrolled the viewport"
    scene.render(display)


def test_the_lesson_screen_renders_after_the_reflow(app_ctx, display):
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="free_advance")
    for ch in scene.engine.target[:5]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    scene.render(display)


# --------------------------------------------------------------------- 3. reset wording

def test_the_reset_confirmation_says_whose_data_not_whose_person(app_ctx, display,
                                                                attempt_factory):
    """"Reset Amina?" reads as though the child is being removed. The profile is
    kept — it is the work that goes."""
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene._ask_reset(scene.summaries[0])

    heading = f"Reset {scene.pending_reset['name']}'s data?"
    assert heading == "Reset Amina's data?"
    scene.render(display)          # the wording is rendered, not just computed


# --------------------------------------------------------------------- 4. settings size

def test_the_settings_cards_use_most_of_the_window(app_ctx, display):
    """The controls used to sit in a ~360 px strip of a 1280 px window."""
    from typecraft.scenes.settings import SOUND_CARD

    assert SOUND_CARD.width >= theme.SCREEN_WIDTH * 0.75


def test_the_settings_card_stays_on_screen(app_ctx, display):
    from typecraft.scenes.settings import SOUND_CARD

    window = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
    assert window.contains(SOUND_CARD)


def test_every_settings_control_sits_inside_the_sound_card(app_ctx, display):
    """A control drifting outside its panel is the visual bug this screen had."""
    from typecraft.scenes.settings import SOUND_CARD, SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    for widget in (scene.vol_down, scene.volume_bar, scene.vol_up, scene.mute_button):
        assert SOUND_CARD.contains(widget.rect), f"{widget} escapes the Sound card"


def test_the_settings_screen_has_no_pin_mutation_controls(app_ctx, display):
    """Changing a teacher PIN is available only inside the authenticated dashboard."""
    from typecraft.scenes.settings import SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    assert not hasattr(scene, "pin_input")
    assert not hasattr(scene, "set_pin_button")


def test_the_settings_controls_are_large_enough_for_a_child_to_hit(app_ctx, display):
    from typecraft.scenes.settings import SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    for widget in (scene.vol_down, scene.vol_up, scene.mute_button, scene.back_button):
        assert widget.rect.height >= 50, f"{widget.rect} is too short to tap reliably"
    assert scene.volume_bar.rect.width >= 400, "the volume bar is still a thin strip"


def test_the_mute_button_changes_colour_with_its_state(app_ctx, display):
    """A silent machine should be obvious at a glance, not only from the label."""
    from typecraft.scenes.settings import SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()
    assert scene.muted is False
    unmuted_colour = scene.mute_button.bg_color

    scene._toggle_mute()

    assert scene.muted is True
    assert scene.mute_button.label == "Unmute"
    assert scene.mute_button.bg_color != unmuted_colour
    scene.render(display)


def test_the_settings_screen_renders_in_both_mute_states(app_ctx, display):
    from typecraft.scenes.settings import SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()
    scene.render(display)
    scene._toggle_mute()
    scene.render(display)


# --------------------------------------------------------------------- 5. dashboard table

@pytest.fixture
def dashboard(app_ctx, display):
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    return app_ctx, scene


def test_the_column_headings_are_bold_and_body_sized(dashboard):
    """They were small and muted, so they read as a caption rather than as the labels
    for the numbers below — and a teacher scans the headings first."""
    _ctx, scene = dashboard
    small = pygame.font.Font(None, theme.FONT_SIZE_SMALL)

    assert scene._header_font.get_bold() is True
    # Compared against the font it replaced rather than against a pixel figure:
    # pygame's nominal size is not its rendered height (Font(None, 28) is 19 px tall).
    assert scene._header_font.get_height() > small.get_height()
    assert scene._header_font.size("STUDENT")[0] > small.size("STUDENT")[0], \
        "the heading font must be larger than the old small one"


def test_no_two_column_headings_overlap(dashboard):
    """The bug the measured layout fixes: bold upper-case headings are wider than the
    values under them, and hard-coded x positions put STREAK on top of BEST."""
    from typecraft.scenes.teacher_dashboard import COLUMNS

    _ctx, scene = dashboard
    previous_right = 0
    for (heading, _key, _fmt), x in zip(COLUMNS, scene._column_x):
        assert x >= previous_right, f"{heading} at {x} overlaps the column ending at {previous_right}"
        previous_right = x + scene._header_font.size(heading.upper())[0]


def test_the_table_stays_clear_of_the_reset_buttons(dashboard):
    from typecraft.scenes.teacher_dashboard import ACTIONS_WIDTH

    _ctx, scene = dashboard
    reset_left = min(button.rect.x for _s, button in scene.reset_buttons) \
        if scene.reset_buttons else theme.SCREEN_WIDTH - ACTIONS_WIDTH
    assert scene.table_right <= reset_left


def test_the_columns_are_ordered_left_to_right(dashboard):
    _ctx, scene = dashboard
    assert scene._column_x == sorted(scene._column_x)
    assert scene._column_x[0] >= 0


def test_the_headings_sit_above_the_scrolling_rows(dashboard):
    """A heading drawn inside the panel would scroll away with the rows."""
    from typecraft.scenes.teacher_dashboard import HEADER_RULE_Y, HEADER_Y

    _ctx, scene = dashboard
    assert HEADER_Y + scene._header_font.get_height() <= scene.panel.rect.top
    assert HEADER_Y < HEADER_RULE_Y <= scene.panel.rect.top


def test_the_empty_message_is_centred_in_the_table_area(dashboard):
    """It used to sit at the far left immediately under the headings, reading as a
    stray row rather than the state of the screen."""
    _ctx, scene = dashboard
    assert scene.summaries == [], "fixture should have no students"

    _title, title_rect, _hint, hint_rect = scene.empty_state_layout()
    area = scene.panel.rect

    for rect in (title_rect, hint_rect):
        assert rect.centerx == area.centerx, "not horizontally centred"
        assert area.contains(rect), "the message escapes the table area"
    assert abs(title_rect.centery - area.centery) < area.height * 0.25, \
        "not vertically centred in the table area"
    assert title_rect.bottom < hint_rect.top, "title and hint overlap"


def test_the_empty_message_is_large_enough_to_read(dashboard):
    """It was FONT_SIZE_SMALL, the same size as a footnote."""
    _ctx, scene = dashboard
    _title, title_rect, _hint, hint_rect = scene.empty_state_layout()
    assert title_rect.height > pygame.font.Font(
        None, theme.FONT_SIZE_SMALL).get_height()
    assert hint_rect.height >= pygame.font.Font(
        None, theme.FONT_SIZE_SMALL).get_height()


def test_the_empty_message_is_well_below_the_headings(dashboard):
    """The specific complaint: it appeared "as left top just below table header"."""
    from typecraft.scenes.teacher_dashboard import HEADER_RULE_Y

    _ctx, scene = dashboard
    _title, title_rect, _hint, _hint_rect = scene.empty_state_layout()
    assert title_rect.top > HEADER_RULE_Y + 100


def test_the_dashboard_renders_empty_and_populated(app_ctx, display, attempt_factory):
    from typecraft.scenes.teacher_dashboard import TeacherDashboardScene

    scene = TeacherDashboardScene(app_ctx)
    scene.on_enter()
    scene.render(display)                      # empty

    student = app_ctx.profiles.create("Mustafa Iqbal", "avatar_fox")
    app_ctx.progression.score(attempt_factory(student.id, accuracy=95.0), student)
    scene.on_enter()
    scene.render(display)                      # populated
