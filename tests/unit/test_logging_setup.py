"""The diagnostic log channel that FR-024, FR-134 and NFR-013 depend on.

Nothing in the inherited code logged anything (defect D-22), so a teacher-edited
JSON file being silently rejected was undiagnosable in the field. These tests fix
the contract: a log file appears in the writable directory, repeated setup does
not stack handlers, and setup never raises even when the log cannot be written.
"""

import logging

from typecraft.core import paths
from typecraft.core.logging_setup import (
    LOGGER_NAME,
    configure_logging,
    get_logger,
    reset_logging,
)


def test_configure_logging_writes_into_the_writable_dir(writable_dir):
    configure_logging()
    get_logger("test").warning("lessons.json rejected: %s", "schema_version mismatch")
    logging.getLogger(LOGGER_NAME).handlers[0].flush()

    log_file = paths.log_path()
    assert log_file.exists(), "no log file was created"
    text = log_file.read_text(encoding="utf-8")
    assert "schema_version mismatch" in text
    assert "WARNING" in text


def test_repeated_configuration_does_not_stack_handlers(writable_dir):
    """AppContext is built many times in one test session, and a --windowed exe
    must not accumulate handlers either."""
    configure_logging()
    first = len(logging.getLogger(LOGGER_NAME).handlers)
    for _ in range(5):
        configure_logging()
    assert len(logging.getLogger(LOGGER_NAME).handlers) == first


def test_child_loggers_sit_under_the_typecraft_root(writable_dir):
    configure_logging()
    assert get_logger("typecraft.managers.lesson_manager").name == (
        "typecraft.managers.lesson_manager"
    )
    assert get_logger("managers.lesson_manager").name == "typecraft.managers.lesson_manager"
    assert get_logger(None).name == LOGGER_NAME


def test_configure_logging_survives_an_unwritable_location(writable_dir, monkeypatch):
    """Tier 3 of the error strategy (docs/architecture.md 11): losing the log must
    never stop the app from starting."""
    reset_logging()
    monkeypatch.setattr(paths, "log_path", lambda: writable_dir / "no" / "such" / "dir" / "x.log")
    import typecraft.core.logging_setup as ls

    monkeypatch.setattr(ls, "log_path", lambda: writable_dir / "no" / "such" / "dir" / "x.log")

    logger = configure_logging()  # must not raise
    assert logger.handlers, "expected a fallback handler"
    logger.info("still alive")


def test_frozen_build_gets_no_console_handler(writable_dir, monkeypatch):
    """A --windowed exe has no console to write to."""
    reset_logging()
    monkeypatch.setattr("sys.frozen", True, raising=False)
    logger = configure_logging()
    kinds = {getattr(h, "_typecraft_kind", None) for h in logger.handlers}
    assert "console" not in kinds
