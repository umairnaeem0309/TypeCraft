"""
main.py — repository-root launcher.

Exists so `python main.py` works from a plain checkout with no installation
and no sys.path manipulation: the repository root is already sys.path[0], and
the `typecraft` package sits directly inside it.

Equivalent entry points, all reaching the same function:

    python main.py
    python -m typecraft
    TypeCraft.exe            (PyInstaller; this file is the spec's script)

The import is guarded because the commonest way to fail to start TypeCraft is to
run it with the wrong interpreter — a machine-wide `python` that has no pygame,
rather than the project's `.venv`. That produced a bare `ModuleNotFoundError`
traceback, which tells a new developer nothing about what to do next.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

#: Where the project's virtual environment lives, per README.md.
VENV_PYTHON = REPO_ROOT / ".venv" / (
    "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
)


def missing_dependency_message(missing: str, executable: str, venv_python: Path) -> str:
    """Explain how to start TypeCraft with the right interpreter.

    Split out from the import guard so the wording is testable without having to
    uninstall pygame.
    """
    lines = [
        f"TypeCraft could not start: '{missing}' is not installed for this interpreter.",
        "",
        f"  Interpreter in use:  {executable}",
    ]

    if venv_python.exists():
        relative = venv_python.relative_to(REPO_ROOT) if venv_python.is_relative_to(REPO_ROOT) \
            else venv_python
        lines += [
            f"  Project virtualenv:  {venv_python}  (exists)",
            "",
            "TypeCraft's dependencies live in the project virtualenv, not in the",
            "interpreter you used. Run it with that one instead:",
            "",
            f"    {relative} main.py",
            "",
            "or activate the environment first, then `python main.py`:",
            "",
            "    .venv\\Scripts\\Activate.ps1     # PowerShell",
            "    .venv\\Scripts\\activate.bat     # cmd",
            "    source .venv/bin/activate       # Git Bash / macOS / Linux",
        ]
    else:
        lines += [
            f"  Project virtualenv:  {venv_python}  (not found)",
            "",
            "Create it and install the dependencies (see README.md):",
            "",
            "    python -m venv .venv",
            "    .venv\\Scripts\\Activate.ps1",
            "    python -m pip install -r requirements.txt -r requirements-dev.txt",
        ]

    return "\n".join(lines)


try:
    from typecraft.main import main
except ModuleNotFoundError as exc:                       # pragma: no cover - see tests
    # Only intercept a missing third-party dependency. A typo inside the package
    # is a real bug and must keep its traceback.
    root_package = (exc.name or "").split(".")[0]
    if root_package in ("pygame",):
        print(missing_dependency_message(root_package, sys.executable, VENV_PYTHON),
              file=sys.stderr)
        raise SystemExit(1) from None
    raise


if __name__ == "__main__":
    raise SystemExit(main())
