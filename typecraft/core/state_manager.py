"""core/state_manager.py — holds exactly one active Scene and handles transitions."""


class GameStateManager:
    def __init__(self, ctx):
        self.ctx = ctx
        self.current = None
        self.registry = {}

    def register(self, name: str, scene_cls) -> None:
        self.registry[name] = scene_cls

    def change(self, name: str, **kwargs) -> None:
        if name not in self.registry:
            raise ValueError(f"No scene registered under {name!r}")

        if self.current is not None:
            self.current.on_exit()

        scene_cls = self.registry[name]
        self.current = scene_cls(self.ctx)
        self.current.on_enter(**kwargs)

    def handle_event(self, event) -> None:
        if self.current:
            self.current.handle_event(event)

    def notify_quit(self) -> None:
        if self.current:
            self.current.on_quit_requested()

    def update(self, dt: float) -> None:
        if self.current:
            self.current.update(dt)

    def render(self, surface) -> None:
        if self.current:
            self.current.render(surface)
