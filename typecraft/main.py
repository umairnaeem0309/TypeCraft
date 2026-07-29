"""main.py — tiny entry point: configure logging, build the Game, start the loop."""

from typecraft.core.game import Game
from typecraft.core.logging_setup import configure_logging, get_logger


def main() -> None:
    configure_logging()
    get_logger(__name__).info("TypeCraft starting")
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
