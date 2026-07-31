"""The app must not die a native death (reported 2026-07-31).

Bug: clicking a student on Profile Select closed the application instantly, with
`typecraft.log` containing nothing but "starting" lines. Cause was a
use-after-free: `core/window.py` used pygame's private
`_sdl2.video.Window.from_display_module()` to resize the OS window, and that object
destroys the underlying SDL window when garbage-collected. Under faulthandler:

    Windows fatal exception: access violation
    Current thread ...: Garbage-collecting

**Why these tests run in a subprocess.** An access violation terminates the
process; it raises no Python exception, so no in-process test can catch it — a
pytest assertion would never run because the interpreter is already gone. Only an
exit code and captured output can prove the absence of a native crash, and that
needs a child process. Every other test in this suite would have passed while the
app was unusable, which is exactly what happened.

These run under the real SDL video driver where possible, because the dummy driver
did not reproduce the fault.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

#: Symptoms of a native crash in captured output.
CRASH_MARKERS = ("access violation", "Segmentation fault", "Fatal Python error",
                 "Fatal error", "fatal exception")


def run_script(body: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a script in a child process with faulthandler on and output unbuffered.

    PREAMBLE and body are dedented separately: dedenting the concatenation strips
    only the *common* prefix and leaves the body over-indented.
    """
    script = REPO_ROOT / "_native_crash_probe.py"
    script.write_text(textwrap.dedent(PREAMBLE) + textwrap.dedent(body),
                      encoding="utf-8")
    try:
        return subprocess.run(
            [sys.executable, "-u", "-X", "faulthandler", str(script)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout,
        )
    finally:
        script.unlink(missing_ok=True)


def assert_no_native_crash(result, what: str):
    combined = f"{result.stdout}\n{result.stderr}"
    for marker in CRASH_MARKERS:
        assert marker.lower() not in combined.lower(), (
            f"native crash during {what}:\n{combined[-2000:]}")
    assert "PROBE-OK" in result.stdout, (
        f"{what} did not run to completion:\n{combined[-2000:]}")
    assert result.returncode == 0, f"{what} exited {result.returncode}:\n{combined[-2000:]}"


PREAMBLE = """
    import faulthandler, gc, pathlib, shutil, tempfile
    faulthandler.enable()
    import pygame
    tmp = pathlib.Path(tempfile.mkdtemp())
    import typecraft.core.paths as paths
    paths.writable_data_dir = lambda: tmp
    from typecraft.core.game import Game
"""


def test_no_unsafe_sdl2_window_is_used():
    """The direct cause, guarded at the source level so it cannot come back.

    `_sdl2.video.Window` is private pygame API whose finalizer destroys the display
    window; there is no safe way to hold one alongside `display.set_mode()`.
    """
    offenders = []
    for path in (REPO_ROOT / "typecraft").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue                      # the post-mortem comment is allowed
            if "_sdl2" in stripped:
                offenders.append(f"{path.name}: {stripped}")
    assert not offenders, f"private pygame _sdl2 API in use: {offenders}"


def test_set_mode_is_called_exactly_once():
    """Calling it twice frees the surface `Game.screen` still points at."""
    text = (REPO_ROOT / "typecraft").joinpath("core", "window.py").read_text(encoding="utf-8")
    calls = [line for line in text.splitlines()
             if "set_mode(" in line and not line.strip().startswith("#")]
    assert len(calls) == 1, f"expected one set_mode call, found {len(calls)}: {calls}"


@pytest.mark.slow
def test_selecting_a_profile_does_not_crash_the_process():
    """The exact reported symptom, driven through Game._process_events."""
    result = run_script("""
        game = Game(full_repaint=False)
        game.ctx.profiles.create("Amina", "avatar_fox")
        game.states.change("profile_select")
        scene = game.states.current
        _profile, card = scene.profile_buttons[0]
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=scene.panel.screen_rect(card).center))
        game._process_events()
        assert type(game.states.current).__name__ == "LessonSelectScene"
        for _ in range(5):
            game._update(1 / 30)
            game._render()
        gc.collect()
        game.ctx.db.close()
        print("PROBE-OK")
    """)
    assert_no_native_crash(result, "selecting a profile")


@pytest.mark.slow
def test_repeated_scene_changes_and_gc_do_not_crash():
    """The fault surfaced during garbage collection, so force plenty of it. Scene
    changes allocate heavily, which is what made GC fire mid-lesson for the user."""
    result = run_script("""
        game = Game(full_repaint=False)
        game.ctx.profiles.create("Amina", "avatar_fox")
        game.ctx.active_profile = game.ctx.profiles.list_all()[0]
        for cycle in range(10):
            for name in ("main_menu", "profile_select", "lesson_select",
                         "leaderboard", "settings", "teacher_dashboard"):
                game.states.change(name)
                game._update(1 / 30)
                game._render()
            gc.collect()
        game.ctx.db.close()
        print("PROBE-OK")
    """)
    assert_no_native_crash(result, "repeated scene changes with GC")


@pytest.mark.slow
def test_a_full_lesson_playthrough_does_not_crash():
    """End to end through the real loop: menu to Results, then shut down cleanly."""
    result = run_script("""
        game = Game(full_repaint=False)
        student = game.ctx.profiles.create("Amina", "avatar_fox")
        game.ctx.active_profile = student
        lesson = game.ctx.lessons.first_lesson()
        game.states.change("lesson", lesson=lesson, mode_key="free_advance")
        target = game.states.current.engine.target
        for ch in target:
            if type(game.states.current).__name__ != "LessonScene":
                break
            pygame.event.post(pygame.event.Event(
                pygame.KEYDOWN, key=ord(ch), unicode=ch))
            game._process_events()
            game._update(1 / 30)
            game._render()
        assert type(game.states.current).__name__ == "ResultsScene", \\
            type(game.states.current).__name__
        gc.collect()
        game.ctx.db.close()
        print("PROBE-OK")
    """)
    assert_no_native_crash(result, "a full lesson playthrough")


@pytest.mark.slow
def test_the_process_exits_cleanly_after_a_quit():
    """Shutdown is where the use-after-free surfaced most reliably."""
    result = run_script("""
        game = Game(full_repaint=False)
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        game.run()
        gc.collect()
        pygame.quit()
        print("PROBE-OK")
    """)
    assert_no_native_crash(result, "quit and shutdown")


@pytest.mark.slow
def test_toggling_fullscreen_does_not_crash():
    """The other half of TC-025 touches the display mode, so prove it is safe too."""
    result = run_script("""
        from typecraft.core import window
        game = Game(full_repaint=False)
        for _ in range(3):
            window.toggle_fullscreen()
            game._update(1 / 30)
            game._render()
        gc.collect()
        game.ctx.db.close()
        print("PROBE-OK")
    """)
    assert_no_native_crash(result, "fullscreen toggling")
