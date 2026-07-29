"""
ui/resource_manager.py

Every image/font/sound load in the codebase goes through here, and
nobody calls font.render() directly anywhere else. Two perf rules baked
in from blueprint §5: convert() every image once at load (§5.4), and
cache rendered text surfaces keyed by (text, font_id, colour) so re-typed
text isn't re-rasterised every frame (§5.2).
"""

import pygame

from typecraft.core.paths import resource_path


class ResourceManager:
    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._sounds = {}
        self._text_cache = {}

    def resource_path(self, rel: str):
        return resource_path(rel)

    def image(self, name: str) -> pygame.Surface:
        if name not in self._images:
            path = resource_path(f"assets/images/{name}")
            surf = pygame.image.load(str(path))
            surf = surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()
            self._images[name] = surf
        return self._images[name]

    def font(self, name: str, size: int) -> pygame.font.Font:
        key = (name, size)
        if key not in self._fonts:
            if name == "default":
                self._fonts[key] = pygame.font.Font(None, size)
            else:
                path = resource_path(f"assets/fonts/{name}")
                self._fonts[key] = pygame.font.Font(str(path), size)
        return self._fonts[key]

    def sound(self, name: str) -> pygame.mixer.Sound:
        if name not in self._sounds:
            path = resource_path(f"assets/sounds/{name}")
            snd = pygame.mixer.Sound(str(path))
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
