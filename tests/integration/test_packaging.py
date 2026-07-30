"""
tests/integration/test_packaging.py — verify the PyInstaller build starts.

This test is marked `slow` because it runs the packaged executable. It is
excluded from the default pytest run via pyproject.toml.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "dist" / "TypeCraft"
EXE = DIST_DIR / "TypeCraft.exe"


def _wait_for_log(log_file: Path, *, timeout: float = 20.0) -> None:
    """Poll until ``log_file`` exists or the timeout is reached."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if log_file.exists():
            return
        time.sleep(0.5)


def _start_executable(exe: Path, log_file: Path, env: dict) -> subprocess.Popen:
    """Launch the executable and poll for its log file, returning the Popen handle."""
    proc = subprocess.Popen(
        [str(exe)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_log(log_file)
    except Exception:
        proc.kill()
        proc.wait()
        raise
    return proc


def _remove_stale_log(log_file: Path) -> None:
    """Delete a stale log file, tolerating a locked file from a previous run."""
    try:
        log_file.unlink()
    except FileNotFoundError:
        pass
    except PermissionError as exc:
        pytest.fail(f"Cannot remove locked {log_file}; kill any lingering TypeCraft.exe first: {exc}")


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only packaging test")
def test_built_executable_starts_and_logs_startup():
    """
    Run the onedir executable under the SDL dummy driver and confirm it reaches
    the main loop (log file is created and contains the startup line).

    This also implicitly verifies that ``writable_data_dir()`` points beside the
    executable in frozen mode, because the log file is written there rather than
    in the repository root.
    """
    if not EXE.exists():
        pytest.skip(f"Built executable not found; run PyInstaller first: {EXE}")

    log_file = DIST_DIR / "typecraft.log"
    _remove_stale_log(log_file)

    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"

    proc = _start_executable(EXE, log_file, env)
    proc.kill()
    proc.wait()

    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    assert log_file.exists(), (
        "typecraft.log was not created beside the executable; "
        f"writable_data_dir() may not be pointing to the right place.\n"
        f"stderr: {stderr[:500]}"
    )
    content = log_file.read_text(encoding="utf-8")
    assert "TypeCraft starting" in content, "Startup log line missing"


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only packaging test")
def test_no_writable_files_appear_under_internal():
    """
    The read-only bundle must not contain a live database, editable settings,
    or log. Those all belong beside the executable. Bundled default data files
    (lessons.json, badges.json, messages.json) are intentionally read-only and
    are allowed under _internal/data/.
    """
    internal = DIST_DIR / "_internal"
    if not internal.exists():
        pytest.skip("_internal/ not present; build first")

    forbidden = {"typecraft.db", "settings.json", "typecraft.log"}
    found = [str(path) for path in internal.rglob("*")
             if path.is_file() and path.name.lower() in forbidden]

    assert not found, (
        "Writable/persistent files were found inside _internal/: "
        + ", ".join(found)
    )


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only packaging test")
def test_relocated_executable_starts_and_logs_beside_itself(tmp_path: Path):
    """
    Copy the release folder to a new location and confirm it self-initialises
    there. This catches hard-coded paths that work only in the original build
    directory.
    """
    if not EXE.exists():
        pytest.skip(f"Built executable not found; run PyInstaller first: {EXE}")

    relocated = tmp_path / "RelocatedTypeCraft"
    shutil.copytree(DIST_DIR, relocated)
    relocated_exe = relocated / "TypeCraft.exe"
    relocated_log = relocated / "typecraft.log"

    # Remove the log copied from the original dist folder so we genuinely wait
    # for the relocated process to create it.
    _remove_stale_log(relocated_log)

    # Snapshot every file in the original dist folder to detect writes back.
    original_files = {p.relative_to(DIST_DIR) for p in DIST_DIR.rglob("*") if p.is_file()}

    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"

    proc = _start_executable(relocated_exe, relocated_log, env)
    proc.kill()
    proc.wait()

    assert relocated_log.exists(), (
        "typecraft.log was not created beside the relocated executable"
    )
    content = relocated_log.read_text(encoding="utf-8")
    assert "TypeCraft starting" in content, "Startup log line missing after relocation"

    new_files = {p.relative_to(DIST_DIR) for p in DIST_DIR.rglob("*") if p.is_file()} - original_files
    assert not new_files, (
        f"Relocated run wrote files back into the original dist folder: {new_files}"
    )
