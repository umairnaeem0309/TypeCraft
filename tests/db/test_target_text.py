"""Target-text layout and cursor (FR-100..FR-104).

The inherited renderer blitted one glyph at a time, advanced `x`, and wrapped when
`x > max_width + 60`. Three faults, all of them visible to a child:

  - it wrapped mid-word, so "practice" could break as "practi" / "ce"
  - the `+ 60` slack meant the wrap test fired only *after* the offending glyph had
    been drawn, so the last character on a line overhung the text area
  - the caret was drawn after `x` had already advanced, so it marked the gap to the
    right of the character it was supposed to point at

The bounds and word-integrity tests below are the contract; the rest guard the
cursor, which is the thing a child actually follows.
"""

import pygame
import pytest

from typecraft.ui import theme
from typecraft.ui.target_text import SPACE_GLYPH, TargetTextLayout
from typecraft.scenes.lesson import TEXT_AREA

AREA = pygame.Rect(60, 150, 600, 250)


@pytest.fixture
def font(app_ctx, display):
    return app_ctx.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_TARGET_TEXT)


def words_on_each_line(layout):
    """Reconstruct the visible text line by line, for word-integrity checks."""
    lines = []
    for indices in layout.lines:
        lines.append("".join(layout.text[i] for i in indices))
    return lines


# --------------------------------------------------------------------- bounds

def test_every_glyph_stays_inside_the_text_area(font):
    """FR-102 — the defect D-17 regression test."""
    text = " ".join(["practice"] * 40)
    layout = TargetTextLayout(text, font, AREA)

    for index, _char, rect in layout.glyphs:
        assert rect.right <= AREA.right, f"{text[index]!r} at {index} overhangs the right edge"
        assert rect.left >= AREA.left
        assert rect.top >= AREA.top


def test_the_longest_bundled_lesson_fits_the_real_text_area(app_ctx, font):
    """The check that matters in the field: real content, real geometry."""
    longest = max(app_ctx.lessons._ordered, key=lambda l: len(l.target_text()))
    layout = TargetTextLayout(longest.target_text(), font, TEXT_AREA)

    assert layout.bounds().right <= TEXT_AREA.right
    assert layout.bounds().bottom <= TEXT_AREA.bottom, (
        f"{longest.id} needs {layout.line_count()} lines and does not fit")


@pytest.mark.parametrize("lesson_index", range(20))
def test_every_lesson_fits_without_clipping(app_ctx, font, lesson_index):
    lesson = app_ctx.lessons._ordered[lesson_index]
    layout = TargetTextLayout(lesson.target_text(), font, TEXT_AREA)

    assert TEXT_AREA.contains(layout.bounds()), f"{lesson.id} is clipped"


# --------------------------------------------------------------------- word integrity

def test_words_are_never_split_across_lines(font):
    """FR-102. A broken word is unreadable for a child still sounding words out."""
    text = "the quick brown fox jumps over the lazy dog again and again and again"
    layout = TargetTextLayout(text, font, AREA)

    assert layout.line_count() > 1, "the fixture must actually wrap"
    for line in words_on_each_line(layout):
        for word in line.split():
            assert word in text.split(), f"{word!r} is not a whole word from the text"


def test_wrapping_preserves_the_text_exactly(font):
    """No character may be lost or duplicated by the layout."""
    text = "The Bridge School has bright, curious students. We practice every day."
    layout = TargetTextLayout(text, font, AREA)

    assert [i for i, _c, _r in layout.glyphs] == list(range(len(text)))
    assert "".join(layout.text[i] for line in layout.lines for i in line) == text


def test_a_word_longer_than_a_line_is_broken_rather_than_overflowing(font):
    """A teacher can type anything, so an unbreakable 200-character token must still
    stay inside the area."""
    layout = TargetTextLayout("x" * 200, font, AREA)

    assert layout.line_count() > 1
    for _index, _char, rect in layout.glyphs:
        assert rect.right <= AREA.right


def test_lines_advance_downwards_by_one_line_height(font):
    layout = TargetTextLayout(" ".join(["word"] * 30), font, AREA)
    tops = sorted({rect.y for _i, _c, rect in layout.glyphs})

    for previous, following in zip(tops, tops[1:]):
        assert following - previous == layout.line_height


# --------------------------------------------------------------------- spaces

def test_spaces_are_drawn_as_a_visible_marker(font):
    """FR-103: a child cannot count invisible spaces."""
    layout = TargetTextLayout("a b", font, AREA)
    assert [c for _i, c, _r in layout.glyphs] == ["a", SPACE_GLYPH, "b"]


def test_the_space_marker_is_measured_not_assumed(font):
    """Layout measures the *displayed* glyph, so the caret and the text can never
    disagree about where a character sits — the marker is wider than a space."""
    layout = TargetTextLayout("a b", font, AREA)
    space_rect = layout.rect_for(1)

    assert space_rect.width == font.size(SPACE_GLYPH)[0]
    assert layout.rect_for(2).x == space_rect.right


# --------------------------------------------------------------------- the cursor

def test_the_caret_sits_on_the_left_edge_of_the_next_character(font):
    """FR-101 — the other half of D-17. The caret marks the character about to be
    typed, so it belongs at its left edge, not past it."""
    layout = TargetTextLayout("abc", font, AREA)

    for cursor in range(3):
        glyph = layout.rect_for(cursor)
        caret = layout.caret_rect(cursor)
        assert caret.x == glyph.x, f"caret is offset from character {cursor}"
        assert caret.y == glyph.y


def test_the_caret_follows_the_cursor_onto_the_next_line(font):
    layout = TargetTextLayout(" ".join(["word"] * 30), font, AREA)
    last_index = len(layout.text) - 1

    first = layout.caret_rect(0)
    last = layout.caret_rect(last_index)

    assert last.y > first.y
    assert AREA.contains(last)


def test_the_caret_rests_after_the_last_character_when_finished(font):
    """At the end there is no next character; the caret must not vanish, nor look
    as though one more keystroke is expected."""
    layout = TargetTextLayout("abc", font, AREA)
    final = layout.rect_for(2)

    caret = layout.caret_rect(3)

    assert caret.x == final.right
    assert caret.y == final.y


def test_an_empty_target_still_produces_a_caret(font):
    """Degenerate, but it must not raise while a scene is rendering."""
    layout = TargetTextLayout("", font, AREA)

    assert layout.glyphs == []
    assert layout.caret_rect(0).topleft == (AREA.x, AREA.y)


# --------------------------------------------------------------------- scene integration

def test_the_lesson_scene_lays_the_text_out_once(app_ctx, display):
    """NFR-007: positions are fixed for the whole attempt, so measuring belongs in
    on_enter, never in render."""
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="free_advance")

    before = scene.layout
    for _ in range(5):
        scene.render(display)
        scene.update(1 / 30)

    assert scene.layout is before, "the layout was rebuilt during rendering"


def test_rendering_the_text_rasterises_nothing_new_after_the_first_frame(app_ctx, display):
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=app_ctx.lessons.first_lesson(), mode_key="free_advance")
    scene.render(display)

    before = len(app_ctx.resources._text_cache)
    for _ in range(10):
        scene.render(display)

    assert len(app_ctx.resources._text_cache) == before


def test_typing_moves_the_caret_and_recolours_only_what_was_typed(app_ctx, display):
    from typecraft.models.attempt import CharStatus
    from typecraft.scenes.lesson import LessonScene

    student = app_ctx.profiles.create("Amina", "avatar_fox")
    app_ctx.active_profile = student
    lesson = app_ctx.lessons.first_lesson()
    target = lesson.target_text()

    scene = LessonScene(app_ctx)
    scene.on_enter(lesson=lesson, mode_key="free_advance")
    start = scene.layout.caret_rect(scene.engine.cursor).topleft

    for ch in target[:4]:
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))

    assert scene.layout.caret_rect(scene.engine.cursor).topleft != start
    assert scene.engine.char_status[:4] == [CharStatus.CORRECT] * 4
    assert scene.engine.char_status[4] is CharStatus.PENDING
    scene.render(display)
