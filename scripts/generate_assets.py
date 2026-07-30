#!/usr/bin/env python3
"""Generate placeholder avatars and short sound cues for TypeCraft.

Run from the repo root with the project virtual environment:

    .venv/Scripts/python scripts/generate_assets.py

This script is intentionally self-contained and only depends on pygame.
All generated assets are original, so there is no licensing concern (OQ-003).
"""

import math
import os
import struct
import wave

import pygame

# Off-screen rendering only; no display is required.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame.init()

BASE_DIR = os.path.join("typecraft", "assets")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
SOUNDS_DIR = os.path.join(BASE_DIR, "sounds")

SAMPLE_RATE = 22050


def ensure_dirs() -> None:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(SOUNDS_DIR, exist_ok=True)


def _save_surface(surface: pygame.Surface, name: str) -> None:
    path = os.path.join(IMAGES_DIR, name)
    pygame.image.save(surface, path)


def generate_avatar(name: str, color: tuple, symbol: str) -> None:
    """A simple coloured circle with a big letter/symbol in the centre."""
    size = 128
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    # Soft outer ring
    pygame.draw.circle(surface, color, (size // 2, size // 2), size // 2 - 4)
    pygame.draw.circle(surface, (255, 255, 255), (size // 2, size // 2), size // 2 - 8)

    # Symbol
    font = pygame.font.Font(None, 80)
    text = font.render(symbol, True, color)
    rect = text.get_rect(center=(size // 2, size // 2))
    surface.blit(text, rect)

    _save_surface(surface, f"{name}.png")


def _sine_wave(freq: float, duration: float, volume: float = 0.5) -> bytes:
    """Generate a mono 16-bit PCM sine wave."""
    frames = int(SAMPLE_RATE * duration)
    data = []
    for i in range(frames):
        value = int(volume * 32767 * math.sin(2 * math.pi * freq * i / SAMPLE_RATE))
        data.append(value)
    # Fade in/out to avoid clicking.
    fade = int(SAMPLE_RATE * 0.005)
    for i in range(min(fade, len(data))):
        data[i] = int(data[i] * (i / fade))
        data[-(i + 1)] = int(data[-(i + 1)] * (i / fade))
    return struct.pack("<" + "h" * len(data), *data)


def _write_wav(name: str, *tones: tuple) -> None:
    """Write a WAV file made of consecutive (freq_hz, duration_s, volume) tones."""
    path = os.path.join(SOUNDS_DIR, f"{name}.wav")
    chunks = b"".join(_sine_wave(freq, duration, volume) for freq, duration, volume in tones)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(chunks)


def generate_sounds() -> None:
    # Short, gentle click.
    _write_wav("key_click", (880, 0.05, 0.3))
    # Lower, slightly longer error buzz.
    _write_wav("error", (220, 0.15, 0.4))
    # Pleasant success: two rising tones.
    _write_wav("success", (523, 0.12, 0.4), (784, 0.25, 0.4))
    # Badge fanfare: quick rising arpeggio.
    _write_wav("badge", (523, 0.08, 0.35), (659, 0.08, 0.35), (784, 0.2, 0.35))


def main() -> None:
    ensure_dirs()

    avatars = [
        ("avatar_fox", (244, 67, 54), "F"),
        ("avatar_owl", (156, 39, 176), "O"),
        ("avatar_cat", (33, 150, 243), "C"),
        ("avatar_bear", (121, 85, 72), "B"),
    ]
    for name, color, symbol in avatars:
        generate_avatar(name, color, symbol)

    generate_sounds()

    print(f"Generated {len(avatars)} avatars in {IMAGES_DIR}")
    print(f"Generated sounds in {SOUNDS_DIR}")


if __name__ == "__main__":
    main()
