"""core/scene.py — abstract base every screen inherits from."""

from abc import ABC, abstractmethod


class Scene(ABC):
    def __init__(self, ctx):
        self.ctx = ctx

    def on_enter(self, **kwargs) -> None:
        """Called once when the scene becomes active. Build widgets, load data here."""
        pass

    def on_exit(self) -> None:
        """Called once when the scene stops being active. Free heavy surfaces, stop sounds."""
        pass

    @abstractmethod
    def handle_event(self, event) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, dt: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def render(self, surface) -> None:
        raise NotImplementedError
