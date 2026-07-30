"""
ui/resource_manager.py

Every image/font/sound load in the codebase goes through here, and
nobody calls font.render() directly anywhere else. Two perf rules baked
in from blueprint §5: convert() every image once at load (§5.4), and
cache rendered text surfaces keyed by (text, font_id, colour) so re-typed
text isn't re-rasterised every frame (§5.2).
"""

from typing import Union

import pygame

from typecraft.core.logging_setup import get_logger
from typecraft.core.paths import resource_path


class _SilentSound:
    """Stub returned when a sound file is missing so gameplay stays silent
    instead of raising (defect D-21)."""

    def play(self, loops=0, maxtime=0, fade_ms=0):
        pass

    def set_volume(self, value):
        pass


class ResourceManager:
    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._sounds = {}
        self._text_cache = {}
        # Tracks missing assets so the warning is logged once per process rather
        # than once per frame.
        self._missing = set()
        self._log = get_logger(__name__)

    def _warn_once(self, kind: str, name: str, exc=None) -> None:
        key = (kind, name)
        if key in self._missing:
            return
        self._missing.add(key)
        if exc is not None:
            self._log.warning("asset missing: %s/%s (%s)", kind, name, exc)
        else:
            self._log.warning("asset missing: %s/%s", kind, name)

    def resource_path(self, rel: str):
        return resource_path(rel)

    def image(self, name: str) -> pygame.Surface:
        if name not in self._images:
            path = resource_path(f"assets/images/{name}")
            if path.exists():
                surf = pygame.image.load(str(path))
                surf = surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
            else:
                self._warn_once("image", name)
                surf = self._placeholder_image()
            self._images[name] = surf
        return self._images[name]

    @staticmethod
    def _placeholder_image() -> pygame.Surface:
        """A neutral grey box with a darker border — never crashes the app."""
        surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        surf.fill((200, 200, 205))
        pygame.draw.rect(surf, (150, 150, 160), surf.get_rect(), width=2)
        return surf

    def font(self, name: str, size: int) -> pygame.font.Font:
        key = (name, size)
        if key not in self._fonts:
            if name == "default":
                self._fonts[key] = pygame.font.Font(None, size)
            else:
                path = resource_path(f"assets/fonts/{name}")
                try:
                    self._fonts[key] = pygame.font.Font(str(path), size)
                except Exception as exc:
                    self._warn_once("font", name, exc)
                    self._fonts[key] = pygame.font.Font(None, size)
        return self._fonts[key]

    def sound(self, name: str) -> Union[pygame.mixer.Sound, _SilentSound]:
        if name not in self._sounds:
            path = resource_path(f"assets/sounds/{name}")
            if path.exists():
                snd = pygame.mixer.Sound(str(path))
            else:
                self._warn_once("sound", name)
                snd = _SilentSound()
            self._sounds[name] = snd
        return self._sounds[name]

    def text_surface(self, text: str, font: pygame.font.Font, color) -> pygame.Surface:
        key = (text, id(font), tuple(color))
        if key not in self._text_cache:
            self._text_cache[key] = font.render(text, True, color).convert_alpha()
        return self._text_cache[key]

    def clear_text_cache(self) -> None:
        """Call on scene exit if a scene generated a huge number of one-off
        strings, to keep the cache from growing unbounded over a session."""
        self._text_cache.clear()
