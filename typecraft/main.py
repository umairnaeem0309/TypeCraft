"""main.py — tiny entry point: configure logging, build the Game, start the loop.

Two guards live here, both added after a crash that left no evidence at all: the
app closed on a profile click and `typecraft.log` contained nothing but "starting"
lines. A silent exit on a school PC is undiagnosable.

  - a top-level `except` that logs the traceback before exiting non-zero
  - `faulthandler` writing to the log, which captures *native* crashes (access
    violations, segfaults) that raise no Python exception and so cannot be caught
"""

import argparse
import faulthandler
import sys

from typecraft.core.game import Game
from typecraft.core.logging_setup import configure_logging, get_logger
from typecraft.core.paths import log_path


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


def crash_log_path():
    return log_path().with_name("typecraft-crash.log")


def _enable_native_crash_capture():
    """Send native crash stacks to a file beside the log.

    A pygame/SDL access violation kills the process without a Python exception, so
    nothing else here can record it. Returns the open handle, which must stay open
    for faulthandler to use it.
    """
    try:
        handle = open(crash_log_path(), "a", encoding="utf-8")
        faulthandler.enable(file=handle, all_threads=True)
        return handle
    except OSError:
        faulthandler.enable()        # stderr is better than nothing
        return None


def _discard_empty_crash_log(handle) -> None:
    """Remove the crash file on a clean exit if nothing was written to it.

    faulthandler needs the file open *before* a crash, so it is created on every
    launch. Left behind empty, a file called typecraft-crash.log sitting beside the
    exe would worry a teacher and make the documentation wrong — its presence is
    supposed to mean something went wrong.
    """
    if handle is None:
        return
    faulthandler.disable()
    try:
        empty = handle.tell() == 0
        handle.close()
        if empty:
            crash_log_path().unlink(missing_ok=True)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    log = get_logger(__name__)
    _crash_handle = _enable_native_crash_capture()
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
    except Exception:
        # Anything escaping the loop would otherwise close the window with no
        # explanation. Log it, then fail loudly rather than exiting 0.
        log.exception("TypeCraft stopped because of an unhandled error")
        return 1
    finally:
        log.info("TypeCraft exiting")
    _discard_empty_crash_log(_crash_handle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
