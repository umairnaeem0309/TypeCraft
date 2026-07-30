"""
tests/integration/test_packaging.py — verify the PyInstaller build starts.

This test is marked `slow` because it runs the packaged executable. It is
excluded from the default pytest run via pyproject.toml.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DIST_DIR = REPO_ROOT / "dist" / "TypeCraft"
EXE = DIST_DIR / "TypeCraft.exe"


@pytest.mark.slow
def test_built_executable_starts_and_logs_startup(tmp_path):
    """
    Run the onedir executable under the SDL dummy driver and confirm it reaches
    the main loop (log file is created and contains the startup line).

    This also implicitly verifies that ``writable_data_dir()`` points beside the
    executable in frozen mode, because the log file is written there rather than
    in the repository root.
    """
    if sys.platform != "win32":
        pytest.skip("Windows-only packaging test")
    if not EXE.exists():
        pytest.skip(f"Built executable not found; run PyInstaller first: {EXE}")

    env = os.environ.copy()
    env["SDL_VIDEODRIVER"] = "dummy"
    env["SDL_AUDIODRIVER"] = "dummy"

    proc = subprocess.Popen(
        [str(EXE)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    finally:
        proc.kill()
        proc.wait()

    log_file = DIST_DIR / "typecraft.log"
    assert log_file.exists(), (
        "typecraft.log was not created beside the executable; "
        f"writable_data_dir() may not be pointing to the right place.\n"
        f"stderr: {proc.stderr.read().decode('utf-8', 'replace')[:500] if proc.stderr else ''}"
    )
    content = log_file.read_text(encoding="utf-8")
    assert "TypeCraft starting" in content, "Startup log line missing"
