"""
tests/conftest.py — shared fixtures.

The single most important job of this file is **data isolation**. TypeCraft's
writable data directory is a real folder holding a real SQLite database; when
running from source that is `<repo>/_dev_data`, and on a school PC it is the
folder beside TypeCraft.exe. No test may ever touch either. Every fixture that
can reach the filesystem routes through `writable_dir`, which redirects
`writable_data_dir()` into pytest's `tmp_path`.

Why the redirect patches several modules instead of one: production modules use
`from typecraft.core.paths import writable_data_dir`, which binds the function
object into each importing module's namespace at import time. Patching only
`typecraft.core.paths` would leave those bindings pointing at the real folder.
The fixture therefore patches every already-imported `typecraft.*` module that
holds such a binding, *and* the `paths` module itself so modules imported later
pick up the redirect too. (Recorded in ARCHITECTURE.md §15 as a design smell:
calling `paths.writable_data_dir()` would need no patching at all.)
"""

import os
import sys

import pytest

# SDL must be told to use non-display drivers before pygame initialises anything,
# so this runs at import time rather than inside a fixture.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PACKAGE = "typecraft"

#: Files the application seeds into the writable directory on first launch.
SEED_FILES = ["lessons.json", "badges.json", "messages.json", "settings.json"]


def _patch_writable_dir(monkeypatch, target):
    """Point every binding of writable_data_dir() at `target`."""
    from typecraft.core import paths

    replacement = lambda: target  # noqa: E731 - a lambda is the clearest thing here

    monkeypatch.setattr(paths, "writable_data_dir", replacement)
    for name, module in list(sys.modules.items()):
        if name.startswith(PACKAGE) and getattr(module, "writable_data_dir", None) is not None:
            monkeypatch.setattr(module, "writable_data_dir", replacement, raising=False)


@pytest.fixture
def writable_dir(tmp_path, monkeypatch):
    """An empty, isolated stand-in for the writable data directory.

    Yields the Path. Nothing is seeded into it — a test that wants the JSON
    present should use `seeded_dir` instead, so first-run behaviour stays
    testable.
    """
    target = tmp_path / "writable"
    target.mkdir()
    _patch_writable_dir(monkeypatch, target)
    yield target

    # Release the rotating log handler, or Windows refuses to delete tmp_path.
    from typecraft.core.logging_setup import reset_logging

    reset_logging()


@pytest.fixture
def seeded_dir(writable_dir):
    """`writable_dir` after first-run seeding, i.e. the steady state a second
    launch sees. Use for tests about normal operation rather than first launch."""
    from typecraft.core.paths import ensure_seeded

    ensure_seeded(SEED_FILES)
    return writable_dir


@pytest.fixture
def db(writable_dir):
    """A Database on a throwaway SQLite file inside `writable_dir`.

    Schema bootstrap and the startup in_progress->incomplete reclassification
    both run, exactly as they do in production.
    """
    from typecraft.managers.database import Database

    database = Database()
    yield database
    database.close()


@pytest.fixture
def display():
    """A headless 1280x720 pygame display.

    Required by anything that rasterises text or constructs a widget. Uses the
    dummy SDL video driver set at module import, so no window ever appears and
    the fixture works on a machine with no graphics stack at all.
    """
    import pygame

    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((1280, 720))
    yield screen
    pygame.display.quit()


@pytest.fixture
def app_ctx(writable_dir, display):
    """A fully-wired AppContext on isolated paths, with no active profile.

    This is the object every scene reads from, so scene tests take this rather
    than assembling managers by hand.
    """
    from typecraft.core.app_context import AppContext

    ctx = AppContext()
    yield ctx
    ctx.db.close()


@pytest.fixture
def attempt_factory():
    """Build an AttemptResult the way TypingEngine.result() would.

    Stars and XP are derived through the real formulas rather than hard-coded, so
    a test states the performance ("95 % at 20 wpm") and cannot drift out of step
    with engine/metrics.py.
    """
    from typecraft.engine import metrics as m
    from typecraft.models.attempt import AttemptResult, AttemptStatus

    def make(profile_id, lesson_id="t1l1", *, accuracy=95.0, wpm_net=20.0, tier=1,
             status=AttemptStatus.COMPLETE, total_keystrokes=100, max_combo=30,
             mode="lock_on_error", duration_sec=60.0):
        complete = status is AttemptStatus.COMPLETE
        stars = m.stars_for(accuracy) if complete else 0
        errors = round(total_keystrokes * (100.0 - accuracy) / 100.0)
        return AttemptResult(
            profile_id=profile_id, lesson_id=lesson_id, status=status, mode=mode,
            wpm_net=wpm_net, wpm_gross=wpm_net / (accuracy / 100.0) if accuracy else 0.0,
            accuracy=accuracy,
            total_keystrokes=total_keystrokes,
            errors=errors,
            correct_keystrokes=total_keystrokes - errors,
            combo=0, max_combo=max_combo, duration_sec=duration_sec,
            stars=stars,
            xp_awarded=m.xp_for(accuracy, wpm_net, stars, tier) if complete else 0,
            started_at="2026-07-29T10:00:00",
            completed_at="2026-07-29T10:01:00" if complete else "",
        )

    return make


@pytest.fixture
def profile(app_ctx):
    """One student profile with the first lesson unlocked, as ProfileManager
    creates it. Returns (ctx, profile) so a test needs only this one fixture."""
    created = app_ctx.profiles.create("Test Student", "avatar_fox")
    app_ctx.active_profile = created
    return app_ctx, created
