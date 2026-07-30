"""The root launcher's guidance when the wrong interpreter is used.

Reported 2026-07-31: `python main.py` failed with a bare
`ModuleNotFoundError: No module named 'pygame'`. The cause was environmental — a
machine-wide `python` (MiniConda) rather than the project's `.venv` — but the
traceback said nothing about that, so the message is now the fix.

`missing_dependency_message()` is a pure function, so the wording is tested without
having to uninstall pygame.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_launcher():
    """Import the root `main.py` under its own name.

    It cannot be imported as `main` because that shadows nothing useful and would
    collide with `typecraft.main`; loading it by path keeps the test honest about
    which file it is checking.
    """
    spec = importlib.util.spec_from_file_location("typecraft_launcher",
                                                 REPO_ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def launcher():
    return load_launcher()


def test_the_launcher_still_exposes_main(launcher):
    """The guard must not break the ordinary path."""
    assert callable(launcher.main)


def test_the_venv_path_is_platform_correct(launcher):
    expected = "Scripts" if sys.platform == "win32" else "bin"
    assert expected in launcher.VENV_PYTHON.parts


def test_the_message_names_the_interpreter_actually_used(launcher):
    """The whole point: the reader needs to see that they ran the wrong python."""
    message = launcher.missing_dependency_message(
        "pygame", r"C:\MiniConda\python.exe", launcher.VENV_PYTHON)

    assert "pygame" in message
    assert r"C:\MiniConda\python.exe" in message


def test_an_existing_venv_is_offered_as_the_fix(launcher, tmp_path):
    """When the environment is already there, the fix is one command, so give it
    rather than a setup lecture."""
    venv = tmp_path / ".venv" / "Scripts" / "python.exe"
    venv.parent.mkdir(parents=True)
    venv.write_text("")

    message = launcher.missing_dependency_message("pygame", "/usr/bin/python", venv)

    assert "(exists)" in message
    assert "main.py" in message
    assert "Activate.ps1" in message
    assert "python -m venv" not in message, "no need to create what already exists"


def test_a_missing_venv_gets_setup_instructions(launcher, tmp_path):
    """A fresh checkout has no environment yet, so the fix is to make one."""
    message = launcher.missing_dependency_message(
        "pygame", "/usr/bin/python", tmp_path / ".venv" / "bin" / "python")

    assert "(not found)" in message
    assert "python -m venv .venv" in message
    assert "requirements.txt" in message


def test_the_message_is_short_enough_to_read(launcher):
    """Guidance nobody reads is not guidance."""
    message = launcher.missing_dependency_message(
        "pygame", sys.executable, launcher.VENV_PYTHON)
    assert len(message.splitlines()) <= 20


def test_only_third_party_imports_are_intercepted():
    """A typo inside the package is a real bug and must keep its traceback rather
    than being reported as an environment problem."""
    source = (REPO_ROOT / "main.py").read_text(encoding="utf-8")
    assert 'in ("pygame",)' in source, (
        "the guard should whitelist third-party packages, not swallow every "
        "ModuleNotFoundError"
    )
