"""Enforce the dependency direction rules from docs/architecture.md 2.

These are the rules that keep the project testable. The two that earn their keep:

  - `engine/` and `managers/` must not import pygame. That is what lets every
    metric, mode, and persistence rule be tested with no display and no window
    (docs/architecture.md 15), and it is the first thing a well-meaning "just render
    it here" change breaks.
  - Only `managers/database.py` may import sqlite3, and only `core/paths.py` may
    compute a filesystem location (NFR-011). Both rules exist because a stray
    `open("data/lessons.json")` works from source and silently breaks the moment
    the app is frozen.

Checks are on module-level imports only, parsed with `ast`. Function-local
imports are deliberately out of scope: `core/game.py` imports the scenes inside
`_register_scenes()` specifically to break a circular import, and that is
correct.
"""

import ast
from pathlib import Path

import pytest

import typecraft

PACKAGE_ROOT = Path(typecraft.__path__[0])

# subpackage -> the typecraft subpackages its modules may import at module level.
ALLOWED = {
    "core": {"core", "managers", "models", "ui", "engine"},
    "engine": {"engine", "models"},
    "managers": {"managers", "models", "core", "engine"},
    "models": set(),
    "scenes": {"core", "engine", "managers", "models", "ui"},
    "ui": {"ui", "models", "core"},
}

# subpackages whose modules must never import pygame at module level.
PYGAME_FREE = {"engine", "managers", "models"}


def _modules():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        rel = path.relative_to(PACKAGE_ROOT)
        subpackage = rel.parts[0] if len(rel.parts) > 1 else ""
        if not subpackage:
            continue  # __init__.py / __main__.py / main.py at the package root
        yield subpackage, rel.as_posix(), path


def _module_level_imports(path):
    """Yield imported dotted names from module-level import statements only."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:  # module level only, not nested in a def/class
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import
                continue
            if node.module:
                yield node.module


ALL = list(_modules())


@pytest.mark.parametrize("subpackage,rel,path", ALL, ids=[m[1] for m in ALL])
def test_dependency_direction(subpackage, rel, path):
    """A module may only import the subpackages docs/architecture.md 2 allows it."""
    allowed = ALLOWED[subpackage]
    violations = []
    for name in _module_level_imports(path):
        if not name.startswith("typecraft."):
            continue
        parts = name.split(".")
        if len(parts) < 2:
            continue
        target = parts[1]
        if target == subpackage and subpackage in allowed:
            continue
        if target not in allowed:
            violations.append(f"{rel} imports {name} (may only reach {sorted(allowed) or 'stdlib'})")
    assert not violations, "\n".join(violations)


@pytest.mark.parametrize("subpackage,rel,path", ALL, ids=[m[1] for m in ALL])
def test_no_pygame_in_logic_layers(subpackage, rel, path):
    """engine/, managers/ and models/ stay renderable-free so they are testable
    with no display (docs/architecture.md 15)."""
    if subpackage not in PYGAME_FREE:
        return
    offenders = [n for n in _module_level_imports(path) if n == "pygame" or n.startswith("pygame.")]
    assert not offenders, f"{rel} imports {offenders}; {subpackage}/ must stay pygame-free"


def test_only_database_module_imports_sqlite3():
    """One gateway to the database (docs/architecture.md 5)."""
    offenders = [
        rel
        for _, rel, path in ALL
        if any(n == "sqlite3" for n in _module_level_imports(path))
        and rel != "managers/database.py"
    ]
    assert not offenders, f"sqlite3 imported outside managers/database.py: {offenders}"


def test_no_scene_imports_another_scene():
    """Scenes transition by name through GameStateManager, never by importing
    each other (docs/architecture.md 2 rule 6)."""
    offenders = []
    for subpackage, rel, path in ALL:
        if subpackage != "scenes":
            continue
        for name in _module_level_imports(path):
            if name.startswith("typecraft.scenes."):
                offenders.append(f"{rel} imports {name}")
    assert not offenders, "\n".join(offenders)


def test_only_paths_module_derives_locations_from_dunder_file():
    """NFR-011: filesystem layout is core/paths.py's job alone. Anything else
    building a path from __file__ is constructing an ad hoc data path."""
    offenders = []
    for _, rel, path in ALL:
        if rel == "core/paths.py":
            continue
        if "__file__" in path.read_text(encoding="utf-8"):
            offenders.append(rel)
    assert not offenders, f"__file__ used outside core/paths.py: {offenders}"


def test_metrics_is_pure():
    """engine/metrics.py holds the scoring formulas and must import nothing from
    the project and nothing that touches the outside world, so the numbers can be
    tested in isolation (FR-052)."""
    path = PACKAGE_ROOT / "engine" / "metrics.py"
    forbidden = {"typecraft", "pygame", "sqlite3", "json", "time", "os", "sys", "pathlib", "random"}
    offenders = [
        name for name in _module_level_imports(path) if name.split(".")[0] in forbidden
    ]
    assert not offenders, f"engine/metrics.py must stay pure; found {offenders}"
