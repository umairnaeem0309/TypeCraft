"""Sound settings: loaded at startup, applied, and persisted (FR-130..FR-134).

Before TC-011 the Settings screen hard-coded 0.7/unmuted on entry and never wrote
either value, so a classroom that muted a machine found it noisy again after a
restart, and the screen contradicted the app it was configuring.
"""

import json
import logging

import pytest

from typecraft.managers.config_manager import ConfigManager
from typecraft.scenes.settings import SettingsScene


def settings_file(writable_dir):
    return writable_dir / "settings.json"


def write_settings(writable_dir, text):
    settings_file(writable_dir).write_text(text, encoding="utf-8")


# --------------------------------------------------------------------- startup wiring

def test_stored_volume_and_mute_are_applied_at_startup(writable_dir, display):
    """FR-130 — the defect D-14 regression test."""
    write_settings(writable_dir, json.dumps(
        {"volume": 0.25, "muted": True, "teacher_pin_hash": None}))

    from typecraft.core.app_context import AppContext

    ctx = AppContext()
    try:
        assert ctx.audio.volume == pytest.approx(0.25)
        assert ctx.audio.muted is True
    finally:
        ctx.db.close()


def test_the_settings_screen_shows_the_stored_values(app_ctx, display):
    """FR-131: the screen must reflect reality, not a hard-coded default."""
    app_ctx.config.set("volume", 0.4)
    app_ctx.config.set("muted", True)
    app_ctx.audio.set_volume(0.4)
    app_ctx.audio.set_muted(True)

    scene = SettingsScene(app_ctx)
    scene.on_enter()

    assert scene.volume_bar.value == pytest.approx(0.4)
    assert scene.muted is True
    assert scene.mute_button.label == "Unmute"


# --------------------------------------------------------------------- persistence

def test_changing_the_volume_persists_it(app_ctx, display, writable_dir):
    """FR-132."""
    scene = SettingsScene(app_ctx)
    scene.on_enter()
    start = scene.volume_bar.value

    scene._vol_down()

    assert scene.volume_bar.value == pytest.approx(start - 0.1)
    assert app_ctx.audio.volume == pytest.approx(start - 0.1)
    # Reload from disk, the way the next launch will.
    assert ConfigManager().get("volume") == pytest.approx(start - 0.1)


def test_toggling_mute_persists_it(app_ctx, display, writable_dir):
    scene = SettingsScene(app_ctx)
    scene.on_enter()

    scene._toggle_mute()

    assert app_ctx.audio.muted is True
    assert ConfigManager().get("muted") is True

    scene._toggle_mute()
    assert ConfigManager().get("muted") is False


def test_volume_is_clamped_at_both_ends(app_ctx, display):
    scene = SettingsScene(app_ctx)
    scene.on_enter()

    for _ in range(20):
        scene._vol_down()
    assert scene.volume_bar.value == pytest.approx(0.0)
    assert ConfigManager().get("volume") == pytest.approx(0.0)

    for _ in range(20):
        scene._vol_up()
    assert scene.volume_bar.value == pytest.approx(1.0)
    assert ConfigManager().get("volume") == pytest.approx(1.0)


def test_a_muted_classroom_stays_muted_across_a_restart(writable_dir, display):
    """The scenario in one test: mute a machine, restart, still muted."""
    from typecraft.core.app_context import AppContext

    first = AppContext()
    try:
        scene = SettingsScene(first)
        scene.on_enter()
        scene._toggle_mute()
        scene._vol_down()
    finally:
        first.db.close()

    second = AppContext()
    try:
        assert second.audio.muted is True
        assert second.audio.volume == pytest.approx(0.6)
    finally:
        second.db.close()


# --------------------------------------------------------------------- corrupt files

@pytest.mark.parametrize("content,label", [
    ("{ not json", "syntax error"),
    ("[1, 2, 3]", "JSON array instead of an object"),
    ("", "empty file"),
    ("null", "JSON null"),
])
def test_a_corrupt_settings_file_falls_back_and_warns(writable_dir, caplog, content, label):
    """FR-134: never crash, always explain."""
    write_settings(writable_dir, content)

    with caplog.at_level(logging.WARNING, logger="typecraft"):
        config = ConfigManager()

    assert config.get("volume") == pytest.approx(0.7), label
    assert config.get("muted") is False
    assert config.warnings, f"no warning recorded for {label}"
    assert "settings.json" in " ".join(r.getMessage() for r in caplog.records)


def test_a_corrupt_settings_file_is_left_alone_for_the_teacher_to_inspect(writable_dir):
    """Same reasoning as a broken lessons.json: overwriting it hides the mistake."""
    write_settings(writable_dir, "{ oops")
    ConfigManager()
    assert settings_file(writable_dir).read_text(encoding="utf-8") == "{ oops"


def test_a_partially_edited_file_keeps_what_is_valid(writable_dir):
    """Deleting one line must not blank out the others."""
    write_settings(writable_dir, json.dumps({"volume": 0.2}))

    config = ConfigManager()

    assert config.get("volume") == pytest.approx(0.2)
    assert config.get("muted") is False
    assert config.has_pin() is False


@pytest.mark.parametrize("bad_volume,expected", [
    (11, 1.0), (-5, 0.0), ("loud", 0.7), (None, 0.7),
])
def test_an_out_of_range_volume_is_coerced(writable_dir, bad_volume, expected):
    """A hand-edited "volume": 11 must not reach pygame.mixer."""
    write_settings(writable_dir, json.dumps(
        {"volume": bad_volume, "muted": False, "teacher_pin_hash": None}))

    assert ConfigManager().get("volume") == pytest.approx(expected)


@pytest.mark.parametrize("bad_muted", ["no", 1, [], "false"])
def test_a_non_boolean_mute_is_coerced(writable_dir, bad_muted):
    """"muted": "no" must not read as true just because it is a non-empty string."""
    write_settings(writable_dir, json.dumps(
        {"volume": 0.5, "muted": bad_muted, "teacher_pin_hash": None}))

    config = ConfigManager()
    assert config.get("muted") is False
    assert config.warnings


def test_a_corrupt_file_is_healed_by_the_next_change(writable_dir):
    """The teacher's fix path: open Settings, change anything, file is valid again."""
    write_settings(writable_dir, "{ oops")
    config = ConfigManager()
    config.set("volume", 0.5)

    reloaded = ConfigManager()
    assert reloaded.warnings == []
    assert reloaded.get("volume") == pytest.approx(0.5)


def test_the_warning_reaches_the_app_context_and_the_settings_screen(writable_dir, display):
    """FR-134 wants it *visible*, not only logged."""
    write_settings(writable_dir, "{ oops")

    from typecraft.core.app_context import AppContext

    ctx = AppContext()
    try:
        from typecraft.core.game import build_state_manager

        build_state_manager(ctx)
        assert ctx.notices, "the warning did not reach AppContext"

        scene = SettingsScene(ctx)
        scene.on_enter()
        scene.render(display)   # must render the notice without crashing
    finally:
        ctx.db.close()


def test_a_missing_settings_file_is_recreated_without_a_warning(writable_dir):
    """First launch is normal operation, not a fault."""
    assert not settings_file(writable_dir).exists()

    config = ConfigManager()

    assert settings_file(writable_dir).exists()
    assert config.warnings == []
