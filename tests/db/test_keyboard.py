"""The teaching keyboard (FR-090..FR-096).

The inherited widget was a 4x10 grid of letters. It had no Space — the most-typed
character in every lesson — no Shift, and none of the punctuation Tier 4 is built
from, so a third of the lesson content could not be shown at all. It highlighted
the key the student had *just pressed*, which teaches nothing: by the time the key
lit up they had already found it. And it never said which finger to use.

The first test below is the one that matters: every character of every bundled
lesson must map to a key and a named finger. It is a coverage proof over the real
content, so adding a lesson with an unsupported character fails the suite instead
of silently leaving a child with no guidance.
"""

import pygame
import pytest

from typecraft.ui import keyboard_renderer as kb
from typecraft.ui.keyboard_renderer import KeyboardRenderer


@pytest.fixture
def keyboard(app_ctx, display):
    board = KeyboardRenderer(app_ctx.resources, origin=(20, 400))
    board.prerender()
    return board


# --------------------------------------------------------------------- content coverage

def test_every_character_in_every_lesson_has_a_key_and_a_finger(app_ctx, keyboard):
    """FR-094 — the coverage proof over the real lesson content."""
    missing = {}
    for lesson in app_ctx.lessons._ordered:
        for char in lesson.target_text():
            if kb.CHAR_TO_KEY.get(char) is None or kb.finger_for(char) is None:
                missing.setdefault(char, []).append(lesson.id)

    assert not missing, f"characters with no key/finger: { {c: v[:2] for c, v in missing.items()} }"


def test_every_lesson_character_resolves_to_a_drawn_key(app_ctx, keyboard):
    """A mapping is not enough — the key must actually exist on the board."""
    for lesson in app_ctx.lessons._ordered:
        for char in set(lesson.target_text()):
            base, _shift = kb.CHAR_TO_KEY[char]
            assert base in keyboard.key_rects, f"{char!r} maps to undrawn key {base!r}"


def test_space_is_a_key_with_a_finger(keyboard):
    """It was absent entirely, and it is the most-typed character in the course."""
    assert " " in keyboard.key_rects
    assert kb.finger_for(" ") == "thumb"
    assert kb.FINGER_LABELS["thumb"]


def test_both_shift_keys_exist(keyboard):
    assert "LSHIFT" in keyboard.key_rects
    assert "RSHIFT" in keyboard.key_rects


@pytest.mark.parametrize("char", list("abcdefghijklmnopqrstuvwxyz0123456789"))
def test_letters_and_digits_need_no_shift(char):
    assert kb.shift_side_for(char) is None
    assert kb.finger_for(char) is not None


@pytest.mark.parametrize("char", list(",.;'-/[]`") + ["="])
def test_unshifted_punctuation_is_covered(char):
    assert kb.shift_side_for(char) is None
    assert kb.finger_for(char) is not None


@pytest.mark.parametrize("char", list("?!:\"<>_+{}|~@#$%^&*()"))
def test_shifted_punctuation_is_covered_and_needs_shift(char):
    assert kb.finger_for(char) is not None
    assert kb.shift_side_for(char) in ("LSHIFT", "RSHIFT")


# --------------------------------------------------------------------- shift guidance

@pytest.mark.parametrize("char,expected", [
    ("A", "RSHIFT"), ("S", "RSHIFT"), ("F", "RSHIFT"), ("T", "RSHIFT"),  # left hand
    ("J", "LSHIFT"), ("K", "LSHIFT"), ("P", "LSHIFT"), ("N", "LSHIFT"),  # right hand
])
def test_a_capital_uses_the_opposite_hands_shift(char, expected):
    """FR-095, and the technique being taught: reach across rather than contort one
    hand. A left-hand letter takes the right Shift and vice versa."""
    assert kb.shift_side_for(char) == expected


def test_a_capital_keeps_the_base_letters_finger(keyboard):
    """Shift changes which hand holds a modifier, not which finger types the letter."""
    assert kb.finger_for("A") == kb.finger_for("a") == "left_pinky"
    assert kb.finger_for("J") == kb.finger_for("j") == "right_index"


def test_a_question_mark_needs_a_shift_and_the_right_little_finger(keyboard):
    """Tier 4's Question Practice lesson is built from these."""
    assert kb.finger_for("?") == "right_pinky"
    assert kb.shift_side_for("?") == "LSHIFT"


# --------------------------------------------------------------------- next-key guidance

def test_guidance_points_at_the_next_key_and_names_the_finger(keyboard):
    """FR-092/FR-093."""
    keyboard.highlight_expected("f")

    assert keyboard.active_keys == ("f",)
    assert keyboard.expected_finger_label == "left index finger"


def test_a_capital_highlights_both_the_letter_and_a_shift(keyboard):
    keyboard.highlight_expected("A")

    assert set(keyboard.active_keys) == {"a", "RSHIFT"}
    assert keyboard.expected_finger_label == "left little finger"


def test_space_is_highlighted_rather_than_clearing_the_guidance(keyboard):
    """The old code passed None for Space, so the busiest key was never shown."""
    keyboard.highlight_expected(" ")

    assert keyboard.active_keys == (" ",)
    assert keyboard.expected_finger_label == "either thumb"


def test_finishing_a_lesson_clears_the_guidance(keyboard):
    """Leaving the last key lit would invite one more keystroke."""
    keyboard.highlight_expected("f")
    keyboard.highlight_expected(None)

    assert keyboard.active_keys == ()
    assert keyboard.expected_finger_label is None


def test_an_unsupported_character_guides_nothing_rather_than_the_wrong_key(keyboard):
    """Better no guidance than confident wrong guidance. The coverage test above is
    what keeps lesson content out of this branch."""
    keyboard.highlight_expected("é")

    assert keyboard.active_keys == ()
    assert keyboard.expected_finger_label is None


# --------------------------------------------------------------------- performance

def test_the_board_is_prerendered_once_not_per_frame(keyboard, display):
    """FR-096/§5.3: 60+ keys drawn once at entry, then one blit and two outlines."""
    assert keyboard.prerender_count == 1

    for _ in range(30):
        keyboard.highlight_expected("j")
        keyboard.render(display)

    assert keyboard.prerender_count == 1


def test_rendering_rasterises_no_new_text(app_ctx, keyboard, display):
    """NFR-007: nothing is rasterised on the frame path.

    Asserted through the ResourceManager's cache rather than by patching
    `pygame.font.Font.render`, which is an immutable C type: once the caption for a
    given key has been drawn, redrawing the same frame must add no cache entries.
    """
    keyboard.highlight_expected("j")
    keyboard.render(display)                     # warm the caption into the cache

    before = len(app_ctx.resources._text_cache)
    for _ in range(10):
        keyboard.render(display)

    assert len(app_ctx.resources._text_cache) == before, "render() rasterised new text"


def test_the_board_fits_the_window():
    width, height = KeyboardRenderer.size()
    assert width <= 1280, f"keyboard is {width}px wide"
    assert height <= 300


# --------------------------------------------------------------------- lesson integration

def test_the_lesson_scene_guides_the_next_character_from_the_start(app_ctx, display):
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="lock_on_error")

    first_char = lesson.target_text()[0]
    assert scene.keyboard.active_keys == (first_char,)
    assert scene.keyboard.expected_finger_label is not None


def test_the_guidance_advances_with_the_cursor(app_ctx, display):
    """The inherited behaviour was to light the key just pressed; this asserts the
    opposite — the guidance is always one step ahead."""
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()
    target = lesson.target_text()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="free_advance")

    for i in range(6):
        expected = target[i]
        assert scene.keyboard.active_keys[0] == kb.CHAR_TO_KEY[expected][0], (
            f"at index {i} the board should point at {expected!r}")
        scene.handle_event(pygame.event.Event(
            pygame.KEYDOWN, key=ord(expected), unicode=expected))

    assert scene.keyboard.active_keys[0] == kb.CHAR_TO_KEY[target[6]][0]


def test_a_wrong_key_does_not_move_the_guidance_in_lock_mode(app_ctx, display):
    """In LockOnErrorMode the cursor stays put, so the hint must stay put too —
    otherwise the child is told to press a key that will be rejected."""
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="lock_on_error")
    before = scene.keyboard.active_keys

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord("z"), unicode="z"))

    assert scene.keyboard.active_keys == before


def test_backspace_moves_the_guidance_back(app_ctx, display):
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()
    target = lesson.target_text()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="backspace")
    for ch in target[:3]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
    assert scene.keyboard.active_keys[0] == kb.CHAR_TO_KEY[target[3]][0]

    scene.handle_event(pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))

    assert scene.keyboard.active_keys[0] == kb.CHAR_TO_KEY[target[2]][0]


def test_a_capitals_lesson_shows_shift_guidance(app_ctx, display):
    """Tier 4 lesson 1 is "My Name Is Sam" — the first character is a capital, so
    the board must call for a Shift straight away."""
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.get("t4l1")

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="free_advance")

    assert len(scene.keyboard.active_keys) == 2
    assert any(k in ("LSHIFT", "RSHIFT") for k in scene.keyboard.active_keys)
    scene.render(display)
