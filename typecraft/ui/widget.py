"""ui/widget.py — abstract base for every UI element."""

from abc import ABC, abstractmethod


class Widget(ABC):
    def __init__(self, rect):
        self.rect = rect
        self.visible = True

    @abstractmethod
    def handle_event(self, event) -> bool:
        """Return True if this widget consumed the event."""
        raise NotImplementedError

    @abstractmethod
    def render(self, surface) -> None:
        raise NotImplementedError
