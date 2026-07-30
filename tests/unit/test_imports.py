"""Every module must import cleanly from the repository root.

This is the regression test for defect D-01 (the package was not importable from
its own root) and the cheapest possible guard against a typo'd import surviving a
refactor: `compileall` catches syntax errors, but only an actual import catches a
wrong module path, a circular import, or a missing name.
"""

import importlib
import pkgutil
from pathlib import Path

import pytest

import typecraft

PACKAGE_ROOT = Path(typecraft.__path__[0])
EXPECTED_SUBPACKAGES = {"core", "engine", "managers", "models", "scenes", "ui"}


def _all_modules():
    """Every module inside the typecraft package, recursively."""
    return sorted(
        info.name for info in pkgutil.walk_packages(typecraft.__path__, prefix="typecraft.")
    )


def test_package_layout_is_as_documented():
    """ARCHITECTURE.md 1.2: six subpackages inside typecraft/."""
    names = {n.split(".")[1] for n in _all_modules() if n.count(".") >= 2}
    missing = EXPECTED_SUBPACKAGES - names
    assert not missing, f"expected subpackages missing: {sorted(missing)}"


@pytest.mark.parametrize("module_name", _all_modules())
def test_module_imports(module_name):
    """Importing must not raise, and must not need sys.path help."""
    importlib.import_module(module_name)


def test_no_module_uses_the_legacy_import_prefix():
    """Defect D-01: the old `TypeCraft.` prefix must never come back."""
    offenders = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith(("from TypeCraft.", "import TypeCraft.")):
                offenders.append(f"{path.name}:{lineno}: {stripped}")
    assert not offenders, "legacy TypeCraft.* imports found:\n" + "\n".join(offenders)


def test_entry_point_is_reachable():
    """`python main.py` and `python -m typecraft` both call this function."""
    from typecraft.main import main

    assert callable(main)
