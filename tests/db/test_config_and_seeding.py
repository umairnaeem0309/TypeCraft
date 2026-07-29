"""First-run seeding, malformed-JSON fallback, and the teacher PIN
(DR-012, FR-023, FR-024, FR-130..FR-135, SR-001..SR-003).

The seeding rule is the one that protects a teacher's work: a launch must copy a
default into place only when the file is *absent*. Overwriting an edited
lessons.json — or a settings.json holding the only copy of the PIN hash — would
silently destroy work with no way back.
"""

import json
import logging

import pytest

from typecraft.core.paths import ensure_seeded, resource_path
from typecraft.managers.config_manager import ConfigManager
from typecraft.managers.lesson_manager import LessonManager

SEED_FILES = ["lessons.json", "badges.json", "messages.json", "settings.json"]


# --------------------------------------------------------------------- first-run seeding

def test_first_launch_seeds_every_editable_file(writable_dir):
    """DR-012, and the reason a freshly-copied folder just works on a school PC."""
    assert list(writable_dir.iterdir()) == []

    ensure_seeded(SEED_FILES)

    assert {p.name for p in writable_dir.iterdir()} == set(SEED_FILES)


def test_settings_json_is_seeded_from_the_default_variant(writable_dir):
    """There is no bundled settings.json — it seeds from settings.default.json,
    so a shipped build cannot accidentally carry a developer's PIN hash."""
    ensure_seeded(SEED_FILES)

    seeded = json.loads((writable_dir / "settings.json").read_text(encoding="utf-8"))
    default = json.loads(resource_path("data/settings.default.json").read_text(encoding="utf-8"))
    assert seeded == default
    assert seeded["teacher_pin_hash"] is None


def test_seeding_never_overwrites_an_edited_file(writable_dir):
    """DR-012/AC-16. The teacher's edits must survive every subsequent launch."""
    edited = writable_dir / "lessons.json"
    edited.write_text('{"teacher": "my own lessons"}', encoding="utf-8")

    for _ in range(3):                       # three more launches
        ensure_seeded(SEED_FILES)

    assert edited.read_text(encoding="utf-8") == '{"teacher": "my own lessons"}'


def test_seeding_fills_only_the_gaps(writable_dir):
    """A partially-populated folder — e.g. after a teacher restored one backup
    file — must be topped up, not flattened."""
    (writable_dir / "lessons.json").write_text("KEEP ME", encoding="utf-8")

    ensure_seeded(SEED_FILES)

    assert (writable_dir / "lessons.json").read_text(encoding="utf-8") == "KEEP ME"
    assert (writable_dir / "badges.json").exists()


# --------------------------------------------------------------------- lessons.json fallback

def test_a_valid_edited_lessons_file_is_used_in_preference_to_the_default(seeded_dir, db):
    """The whole point of the writable copy: the teacher's file wins."""
    live = seeded_dir / "lessons.json"
    data = json.loads(live.read_text(encoding="utf-8"))
    data["tiers"][0]["lessons"][0]["title"] = "Ms Fatima's Home Row"
    live.write_text(json.dumps(data), encoding="utf-8")

    lessons = LessonManager(db)
    lessons.load_file()

    assert lessons.get("t1l1").title == "Ms Fatima's Home Row"


@pytest.mark.parametrize("bad_content,label", [
    ("{ this is not json", "syntax error"),
    ('{"schema_version": 99, "tiers": []}', "schema_version mismatch"),
    ('{"schema_version": 1}', "missing tiers key"),
    ("", "empty file"),
])
def test_a_broken_lessons_file_falls_back_to_the_bundled_default(seeded_dir, db,
                                                                bad_content, label):
    """FR-023: a teacher's mistake must never stop the class from typing."""
    (seeded_dir / "lessons.json").write_text(bad_content, encoding="utf-8")

    lessons = LessonManager(db)
    lessons.load_file()

    assert len(lessons._ordered) >= 20, f"fallback failed for {label}"
    assert len(lessons.tiers()) == 5


def test_fallback_does_not_overwrite_the_teachers_broken_file(seeded_dir, db):
    """The teacher needs their file left alone so they can find their mistake."""
    broken = "{ oops"
    (seeded_dir / "lessons.json").write_text(broken, encoding="utf-8")

    LessonManager(db).load_file()

    assert (seeded_dir / "lessons.json").read_text(encoding="utf-8") == broken


@pytest.mark.xfail(strict=True, reason="defect D-19: the fallback is silent - no log record "
                                      "and no teacher-visible notice")
def test_a_broken_lessons_file_is_reported(seeded_dir, db, caplog):
    """FR-024. Without this, a teacher's broken edit looks exactly like an edit
    that had no effect: the class sees the default lessons and nobody knows why.
    TC-023 adds the log record and the on-screen notice."""
    (seeded_dir / "lessons.json").write_text("{ broken", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="typecraft"):
        LessonManager(db).load_file()

    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "lessons.json" in messages
    assert caplog.records, "nothing was logged about the rejected file"


# --------------------------------------------------------------------- settings & PIN

def test_config_seeds_itself_when_settings_json_is_absent(writable_dir):
    config = ConfigManager()
    assert (writable_dir / "settings.json").exists()
    assert config.get("volume") == pytest.approx(0.7)
    assert config.get("muted") is False


def test_a_set_value_survives_a_restart(writable_dir):
    """FR-132."""
    ConfigManager().set("volume", 0.3)
    assert ConfigManager().get("volume") == pytest.approx(0.3)


def test_no_pin_is_configured_on_a_fresh_install(writable_dir):
    """FR-120: with no PIN the dashboard opens so the teacher can set one."""
    config = ConfigManager()
    assert config.has_pin() is False
    assert config.verify_pin("0000") is False


def test_a_pin_can_be_set_and_verified(writable_dir):
    """FR-133."""
    config = ConfigManager()
    config.set_pin("2468")

    assert config.has_pin() is True
    assert config.verify_pin("2468") is True
    assert config.verify_pin("1357") is False


def test_the_pin_survives_a_restart(writable_dir):
    ConfigManager().set_pin("2468")
    assert ConfigManager().verify_pin("2468") is True


def test_the_plaintext_pin_is_never_written_to_disk(writable_dir):
    """SR-001. settings.json is a plain text file a curious student can open."""
    ConfigManager().set_pin("2468")

    for path in writable_dir.iterdir():
        assert "2468" not in path.read_text(encoding="utf-8", errors="ignore"), path.name


@pytest.mark.xfail(strict=True, reason="defect D-15: the PIN is an unsalted SHA-256 of four "
                                      "digits - only 10 000 possible hashes")
def test_the_pin_hash_is_salted(writable_dir, tmp_path, monkeypatch):
    """SR-002. A bare SHA-256 of a 4-digit PIN is reversed by trying all 10 000
    inputs, so the stored hash is equivalent to storing the PIN. Two installs
    choosing the same PIN must not produce the same hash. TC-011b moves this to
    PBKDF2 with a per-install salt."""
    ConfigManager().set_pin("2468")
    first = json.loads((writable_dir / "settings.json").read_text(encoding="utf-8"))

    (writable_dir / "settings.json").unlink()
    ConfigManager().set_pin("2468")
    second = json.loads((writable_dir / "settings.json").read_text(encoding="utf-8"))

    assert first["teacher_pin_hash"] != second["teacher_pin_hash"]


@pytest.mark.xfail(strict=True, reason="defect D-15: a 4-digit unsalted SHA-256 is brute "
                                      "forced instantly")
def test_the_pin_cannot_be_recovered_by_brute_force(writable_dir):
    """SR-002, demonstrated rather than asserted in the abstract: this loop
    recovers the PIN from settings.json in milliseconds."""
    import hashlib

    ConfigManager().set_pin("2468")
    stored = json.loads((writable_dir / "settings.json").read_text(encoding="utf-8"))

    recovered = next(
        (f"{n:04d}" for n in range(10_000)
         if hashlib.sha256(f"{n:04d}".encode()).hexdigest() == stored["teacher_pin_hash"]),
        None,
    )
    assert recovered is None, f"recovered the teacher PIN from disk: {recovered}"
