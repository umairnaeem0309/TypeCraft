"""Render budget tests for TC-018 (NFR-007, NFR-014).

These tests assert that the LessonScene does not re-rasterise text every frame
and that the text cache cannot grow without bound across a classroom session.
"""

import pygame
import pytest

from typecraft.models.attempt import AttemptStatus


def test_text_cache_stays_bounded(app_ctx, display):
    """NFR-014: rendering many distinct strings must not exhaust memory."""
    resources = app_ctx.resources

    for i in range(resources.MAX_TEXT_CACHE + 200):
        resources.text_surface(f"string {i}",
                                 resources.font("default", 24),
                                 (i % 256, i % 256, i % 256))

    assert len(resources._text_cache) <= resources.MAX_TEXT_CACHE


def test_lesson_scene_does_not_rasterise_text_per_frame(app_ctx, display):
    """NFR-007. After the first frame, the lesson scene should blit cached
    surfaces and not call ResourceManager.text_surface() again."""
    student = app_ctx.profiles.create("Perf", "avatar_fox")
    app_ctx.active_profile = student

    lesson = app_ctx.lessons.first_lesson()
    app_ctx.states.change("lesson", lesson=lesson, mode_key="lock_on_error")

    # Warm-up frame: this is allowed to rasterise the initial layout.
    app_ctx.states.render(display)

    # Now every surface the scene needs should be cached.
    calls = []

    def _spy_text_surface(text, font, color):
        calls.append(text)
        raise AssertionError("text_surface should not be called after warm-up")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(app_ctx.resources, "text_surface", _spy_text_surface)
    try:
        # Render a few more frames with no new keystrokes.
        for _ in range(5):
            app_ctx.states.update(1 / 30)
            app_ctx.states.render(display)
    finally:
        monkeypatch.undo()

    assert not calls, "ResourceManager.text_surface() was called during LessonScene.render() after warm-up"


def test_lesson_scene_renders_only_changed_lines_on_keystroke(app_ctx, display):
    """TC-018: a keystroke should dirty the target-text line and keyboard area,
    not the whole scene."""
    student = app_ctx.profiles.create("Line", "avatar_owl")
    app_ctx.active_profile = student

    lesson = app_ctx.lessons.first_lesson()
    app_ctx.states.change("lesson", lesson=lesson, mode_key="lock_on_error")
    scene = app_ctx.states.current

    # Clear dirty rects from scene change.
    scene.dirty_rects.clear()

    char = lesson.target_text()[0]
    event = pygame.event.Event(pygame.KEYDOWN, key=ord(char), unicode=char)
    scene.handle_event(event)

    assert scene.dirty_rects, "keystroke did not mark any area dirty"
    # The dirty rects should include the target text line and keyboard, not the
    # whole screen.
    dirty = [r for r in scene.dirty_rects if r.width < 1280]
    assert dirty, "dirty rect should be a partial-screen region, not full screen"
