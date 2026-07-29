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

    def on_quit_requested(self) -> None:
        """Called when the window's close button is pressed, before the loop stops.

        The last chance to persist anything the student would otherwise lose
        (FR-071). Default is to do nothing, which is right for every scene that
        holds no unsaved state. Must not raise and must not block: the process is
        on its way out, and a crash here would turn a clean exit into data loss.
        """
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
