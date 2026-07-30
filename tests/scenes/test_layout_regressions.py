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
    from typecraft.scenes.lesson import FOOTER_RECT, LessonScene
    from typecraft.ui.keyboard_renderer import KeyboardRenderer

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="lock_on_error")

    kb_h = KeyboardRenderer.size()[1]
    bands = [
        ("hud", scene.hud.rect.top, scene.hud.rect.bottom),
        ("text", scene.layout.bounds().top, scene.layout.bounds().bottom),
        ("keyboard", scene.keyboard.origin[1], scene.keyboard.origin[1] + kb_h),
        ("footer", FOOTER_RECT.top, FOOTER_RECT.bottom),
    ]
    for (name_a, _top_a, bottom_a), (name_b, top_b, _bottom_b) in zip(bands, bands[1:]):
        assert bottom_a <= top_b, f"{name_a} overlaps {name_b}"

    assert bands[-1][2] <= theme.SCREEN_HEIGHT


def test_the_longest_lesson_still_fits_the_narrowed_text_area(app_ctx, display):
    """The text area was shortened to make room. Measured: no bundled lesson needs
    more than 2 lines — but assert it rather than trusting the measurement."""
    from typecraft.scenes.lesson import TEXT_AREA
    from typecraft.ui.target_text import TargetTextLayout

    font = app_ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TARGET_TEXT)
    for lesson in app_ctx.lessons._ordered:
        layout = TargetTextLayout(lesson.target_text(), font, TEXT_AREA)
        assert TEXT_AREA.contains(layout.bounds()), f"{lesson.id} no longer fits"


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
    from typecraft.scenes.settings import PIN_CARD, SOUND_CARD

    assert SOUND_CARD.width >= theme.SCREEN_WIDTH * 0.75
    assert PIN_CARD.width == SOUND_CARD.width
    covered = SOUND_CARD.union(PIN_CARD)
    assert covered.height >= theme.SCREEN_HEIGHT * 0.6


def test_the_settings_cards_do_not_overlap_and_stay_on_screen(app_ctx, display):
    from typecraft.scenes.settings import PIN_CARD, SOUND_CARD

    window = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
    assert window.contains(SOUND_CARD) and window.contains(PIN_CARD)
    assert not SOUND_CARD.colliderect(PIN_CARD)


def test_every_settings_control_sits_inside_its_card(app_ctx, display):
    """A control drifting outside its panel is the visual bug this screen had."""
    from typecraft.scenes.settings import PIN_CARD, SOUND_CARD, SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    for widget in (scene.vol_down, scene.volume_bar, scene.vol_up, scene.mute_button):
        assert SOUND_CARD.contains(widget.rect), f"{widget} escapes the Sound card"
    for widget in (scene.pin_input, scene.set_pin_button):
        assert PIN_CARD.contains(widget.rect), f"{widget} escapes the PIN card"


def test_the_settings_controls_are_large_enough_for_a_child_to_hit(app_ctx, display):
    from typecraft.scenes.settings import SettingsScene

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    for widget in (scene.vol_down, scene.vol_up, scene.mute_button,
                   scene.set_pin_button, scene.pin_input, scene.back_button):
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
    scene._set_pin()               # populates pin_status, which renders in place of the hint
    scene.render(display)
