"""ui/audio_manager.py — thin pygame.mixer wrapper. Sounds are tiny
(<50KB) and loaded/convert-ed once via ResourceManager (§5.7)."""

import pygame


class AudioManager:
    def __init__(self, resource_manager):
        self.resources = resource_manager
        self._volume = 0.7
        self._muted = False
        try:
            pygame.mixer.init(buffer=512)
        except pygame.error:
            pass  # no audio device available; play() becomes a silent no-op

    def play(self, name: str) -> None:
        if self._muted:
            return
        try:
            snd = self.resources.sound(name)
            snd.set_volume(self._volume)
            snd.play()
        except (pygame.error, FileNotFoundError):
            pass

    def set_volume(self, v: float) -> None:
        self._volume = max(0.0, min(1.0, v))

    def set_muted(self, flag: bool) -> None:
        self._muted = flag
