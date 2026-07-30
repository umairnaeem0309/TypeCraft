"""main.py — tiny entry point: configure logging, build the Game, start the loop."""

import argparse
import sys

from typecraft.core.game import Game
from typecraft.core.logging_setup import configure_logging, get_logger


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="TypeCraft")
    parser.add_argument(
        "--profile", action="store_true",
        help="Log per-frame event/update/render timings to a CSV file."
    )
    parser.add_argument(
        "--csv", default="typecraft_profile.csv",
        help="Path for the profiling CSV (default: typecraft_profile.csv)."
    )
    parser.add_argument(
        "--fullscreen", action="store_true",
        help="Start fullscreen. F11 or Alt+Enter toggles it at any time."
    )
    parser.add_argument(
        "--full-repaint", action="store_true",
        help="Force a full-screen flip() every frame instead of dirty-rect updates."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    log = get_logger(__name__)
    log.info("TypeCraft starting")

    if argv is None:
        argv = sys.argv[1:]
    args = _build_parser().parse_args(argv)

    game = Game(
        full_repaint=args.full_repaint,
        profile=args.profile,
        profile_path=args.csv,
        fullscreen=args.fullscreen,
    )
    try:
        game.run()
    finally:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
