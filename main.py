"""main.py — tiny entry point: build the Game, start the loop."""

from TypeCraft.core.game import Game


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
