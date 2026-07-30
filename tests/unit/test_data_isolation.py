"""Prove the test fixtures cannot reach real data.

This file guards the guard. If `writable_dir` ever stops redirecting — because a
new module binds `writable_data_dir` in a way conftest does not patch, or because
someone adds a module-level `Database()` — then the whole suite would silently
start reading and writing the developer's `_dev_data/typecraft.db`, and on a
school machine a stray run would touch real student records. That failure is
invisible unless something asserts against it, so this does.
"""

from pathlib import Path

import typecraft
from typecraft.core import paths

REPO_ROOT = Path(typecraft.__path__[0]).parent
REAL_DEV_DATA = REPO_ROOT / "_dev_data"


def test_unpatched_writable_dir_is_the_real_dev_folder():
    """Sanity check on the thing being protected: without a fixture, the writable
    directory really is `<repo>/_dev_data`, i.e. redirection is load-bearing."""
    assert paths.writable_data_dir() == REAL_DEV_DATA


def test_writable_dir_fixture_redirects_paths_module(writable_dir):
    assert paths.writable_data_dir() == writable_dir
    assert writable_dir != REAL_DEV_DATA
    assert REAL_DEV_DATA not in writable_dir.parents


def test_writable_dir_fixture_redirects_every_importing_module(writable_dir):
    """Modules that did `from ... import writable_data_dir` hold their own
    binding; all of them must have been patched."""
    import sys

    unpatched = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("typecraft"):
            continue
        func = getattr(module, "writable_data_dir", None)
        if func is None:
            continue
        if func() != writable_dir:
            unpatched.append(name)
    assert not unpatched, f"still pointing at real data: {unpatched}"


def test_log_path_is_inside_the_isolated_dir(writable_dir):
    assert paths.log_path().parent == writable_dir


def test_database_fixture_creates_its_file_in_the_isolated_dir(db, writable_dir):
    created = {p.name for p in writable_dir.iterdir()}
    assert "typecraft.db" in created
    # The schema really was bootstrapped, so `db` is usable, not just a file.
    tables = {r["name"] for r in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"profiles", "lesson_attempts", "lesson_progress", "badges", "profile_badges"} <= tables


def test_seeded_dir_seeds_the_four_editable_json_files(seeded_dir):
    names = {p.name for p in seeded_dir.iterdir()}
    assert {"lessons.json", "badges.json", "messages.json", "settings.json"} <= names


def test_writable_dir_fixture_starts_empty(writable_dir):
    """First-run behaviour (DR-012) is only testable if the fixture does not
    pre-seed. Deliberately separate from `seeded_dir`."""
    assert list(writable_dir.iterdir()) == []


def test_resource_path_still_points_inside_the_package(writable_dir):
    """The redirect must move only the WRITABLE side. Read-only resources stay
    anchored in the package, or first-run seeding would have nothing to copy."""
    lessons = paths.resource_path("data/lessons.json")
    assert lessons.exists()
    assert Path(typecraft.__path__[0]) in lessons.parents
