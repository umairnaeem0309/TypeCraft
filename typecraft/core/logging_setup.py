"""
core/logging_setup.py

The one place logging is configured. Exists because several requirements need a
diagnostic channel that survives the app closing and can be read by whoever is
standing in front of a broken school PC:

  - FR-024   a malformed teacher-edited lessons.json must log why it was rejected
  - FR-134   a corrupt settings.json must log its fallback
  - NFR-013  a broad `except` is only acceptable if the reason is recorded
  - tier 3/4 error handling in ARCHITECTURE.md §11

Deliberately boring: stdlib logging, one rotating file in the writable data
directory (never inside the read-only bundle), no third-party dependency, no
network handler. Console output is added only when running from source, so the
packaged --windowed build never tries to write to a console that does not exist.

Usage:
    from typecraft.core.logging_setup import configure_logging, get_logger

    configure_logging()                  # once, at startup
    log = get_logger(__name__)           # anywhere
    log.warning("lessons.json rejected: %s", reason)
"""

import logging
import logging.handlers
import sys

from typecraft.core.paths import log_path

LOGGER_NAME = "typecraft"
MAX_BYTES = 512 * 1024  # half a MB is plenty for a diagnostic trail
BACKUP_COUNT = 2
_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(level: int = logging.INFO, to_console: bool | None = None) -> logging.Logger:
    """
    Configure the 'typecraft' logger. Safe to call more than once — repeated
    calls do not stack duplicate handlers, which matters because tests build an
    AppContext many times in one process.

    Args:
        level: threshold for the root TypeCraft logger.
        to_console: add a stderr handler. Defaults to True when running from
            source and False when frozen (a --windowed exe has no console).

    Returns:
        The configured logger. Never raises: if the log file cannot be opened
        (read-only folder, locked file, full disk) the application must still
        start, so the failure degrades to console-only or to no handler at all.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if to_console is None:
        to_console = not getattr(sys, "frozen", False)

    # Idempotency: identify our own handlers by an attribute rather than by type,
    # so a caller's extra handler is never removed.
    existing = {getattr(h, "_typecraft_kind", None) for h in logger.handlers}

    if "file" not in existing:
        try:
            handler = logging.handlers.RotatingFileHandler(
                str(log_path()), maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT,
                encoding="utf-8", delay=True,
            )
            handler.setFormatter(logging.Formatter(_FORMAT))
            handler._typecraft_kind = "file"
            logger.addHandler(handler)
        except OSError:
            # No log file available. Not fatal — see the docstring.
            pass

    if to_console and "console" not in existing:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        handler._typecraft_kind = "console"
        logger.addHandler(handler)

    if not logger.handlers:
        # Nothing could be attached; silence "no handler" warnings.
        logger.addHandler(logging.NullHandler())

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Child logger under the 'typecraft' root. Pass __name__ from the caller."""
    if not name or name == LOGGER_NAME:
        return logging.getLogger(LOGGER_NAME)
    short = name[len(LOGGER_NAME) + 1:] if name.startswith(LOGGER_NAME + ".") else name
    return logging.getLogger(f"{LOGGER_NAME}.{short}")


def reset_logging() -> None:
    """Detach and close TypeCraft's own handlers. For test teardown, so a
    temporary log file is not held open across tmp_path cleanup on Windows."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in [h for h in logger.handlers if hasattr(h, "_typecraft_kind")]:
        logger.removeHandler(handler)
        handler.close()
