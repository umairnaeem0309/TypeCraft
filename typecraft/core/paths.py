"""
core/paths.py

The single place in the codebase allowed to reason about "where are we
running from" and "where is it safe to write files."

Two kinds of files, two functions. Every file open anywhere else in the
project must go through one of these two helpers. Never build a path with
open("data/lessons.json") or similar — it works when run from source and
breaks the moment the app is frozen by PyInstaller.

    resource_path(relative)   -> read-only bundled files (assets/, default json)
    writable_data_dir()       -> writable persistent files (db, live json, settings)

See blueprint §3.3 for the full reasoning: writing the database into the
PyInstaller temp/bundle location silently wipes student progress on every
launch. That is the bug this file exists to prevent.
"""

import shutil
import sys
from pathlib import Path


def _is_frozen() -> bool:
    """True when running as a packaged PyInstaller exe, False when running from source."""
    return bool(getattr(sys, "frozen", False))


def _package_root() -> Path:
    """
    The `typecraft` package directory — the anchor for READ-ONLY resources
    when running from source.

    This file lives at <package_root>/core/paths.py, so the package root is
    this file's parent's parent. assets/ and data/ live inside the package
    (ADR-002) so this one anchor works both from source and when frozen.
    """
    return Path(__file__).resolve().parent.parent


def _repo_root() -> Path:
    """
    The repository root when running from source — the directory that
    *contains* the `typecraft` package, alongside main.py and tests/.

    Used only to place the dev-mode writable folder, so `_dev_data/` sits
    beside the package rather than inside it (where it would be swept into
    a PyInstaller bundle).
    """
    return _package_root().parent


def resource_path(relative: str) -> Path:
    """
    Resolve the absolute path to a READ-ONLY bundled resource.

    Use this for everything under assets/ (images, fonts, sounds) and for
    reading the DEFAULT/fallback copies of lessons.json, badges.json,
    messages.json, settings.default.json.

    Never write to a path returned by this function — when frozen it may
    point inside a temporary extraction folder (sys._MEIPASS) that does
    not persist between runs.

    Args:
        relative: path relative to the package root, e.g. "assets/images/logo.png"
            or "data/lessons.json".

    Returns:
        Path: absolute path to the resource.

    Note: TypeCraft.spec maps typecraft/assets -> assets and typecraft/data ->
    data inside the bundle, so the same `relative` string resolves correctly
    under sys._MEIPASS as it does under the package root.
    """
    if _is_frozen():
        # PyInstaller unpacks bundled data files here at runtime.
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = _package_root()

    return base / relative


def writable_data_dir() -> Path:
    """
    Resolve the absolute path to the WRITABLE, PERSISTENT data directory.

    Use this for typecraft.db, and the LIVE editable copies of
    lessons.json / badges.json / messages.json / settings.json.

    When frozen, this is the folder containing TypeCraft.exe (so the DB
    and edited JSON sit beside the executable and survive updates/reinstalls
    of the bundle itself, and can be copied to a USB stick as a backup).

    When running from source, this is the repository root's ./_dev_data
    folder — beside the package, never inside it — so dev runs never dirty
    the real project tree, never get swept into a build, and are ignored by
    git (.gitignore, defect D-24).

    The directory is created if it does not already exist.

    Returns:
        Path: absolute path to the writable data directory.
    """
    if _is_frozen():
        base = Path(sys.executable).parent
    else:
        base = _repo_root() / "_dev_data"

    base.mkdir(parents=True, exist_ok=True)
    return base


def ensure_seeded(filenames, defaults_subdir: str = "data") -> None:
    """
    First-run seeding (blueprint §3.3): for each filename in `filenames`,
    if it does not yet exist in writable_data_dir(), copy the bundled
    default (read via resource_path(defaults_subdir/filename)) into the
    writable dir.

    Call this once at startup, before anything else opens the db or json
    files, so a freshly-deployed folder self-initialises on first launch.

    Args:
        filenames: iterable of filenames to seed, e.g.
            ["lessons.json", "badges.json", "messages.json", "settings.json"]
        defaults_subdir: subfolder under the project root / bundle where
            the bundled default copies live (default: "data").

    Note: typecraft.db is intentionally NOT seeded this way — it has no
    bundled default. Database.py is responsible for bootstrapping the
    schema into a fresh, empty writable_data_dir()/typecraft.db on first run.
    """
    target_dir = writable_data_dir()

    for filename in filenames:
        target = target_dir / filename
        if target.exists():
            continue

        # settings.json has no direct default file; it seeds from
        # settings.default.json instead.
        default_name = "settings.default.json" if filename == "settings.json" else filename
        source = resource_path(f"{defaults_subdir}/{default_name}")

        if source.exists():
            shutil.copy2(source, target)
        # If the bundled default is itself missing, we deliberately do NOT
        # raise here — the caller (main.py / LessonManager / ConfigManager)
        # is responsible for validating the loaded content and falling
        # back / warning per §2.3. This function's job is only copying.
