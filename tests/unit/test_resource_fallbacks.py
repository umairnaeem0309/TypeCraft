"""tests/unit/test_resource_fallbacks.py — missing assets degrade, not crash."""

from unittest.mock import patch

import pygame
import pytest

from typecraft.ui.resource_manager import ResourceManager


@pytest.fixture(autouse=True)
def _init_pygame():
    # Pygame font/mixer operations need an initialized sub-system, but no
    # display is required for off-screen surface work.
    pygame.init()


@pytest.fixture
def resources(tmp_path):
    return ResourceManager()


def test_missing_image_returns_placeholder(resources):
    surf = resources.image("does_not_exist.png")
    assert isinstance(surf, pygame.Surface)
    assert surf.get_width() > 0 and surf.get_height() > 0


def test_missing_image_is_logged_once(resources):
    with patch.object(resources._log, "warning") as mock_warn:
        resources.image("missing.png")
        resources.image("missing.png")  # cached; should not log again
    mock_warn.assert_called_once()
    # logging.warning receives the format string plus its arguments.
    assert "image" in mock_warn.call_args[0]
    assert "missing.png" in mock_warn.call_args[0]


def test_missing_sound_returns_silent_stub(resources):
    stub = resources.sound("does_not_exist.wav")
    # Must satisfy the contract AudioManager.play() expects.
    stub.set_volume(0.5)
    stub.play()


def test_missing_sound_is_logged_once(resources):
    with patch.object(resources._log, "warning") as mock_warn:
        resources.sound("missing.wav")
        resources.sound("missing.wav")
    mock_warn.assert_called_once()
    assert "sound" in mock_warn.call_args[0]
    assert "missing.wav" in mock_warn.call_args[0]


def test_missing_custom_font_falls_back_to_default(resources):
    font = resources.font("no_such_font.ttf", 24)
    assert isinstance(font, pygame.font.Font)
