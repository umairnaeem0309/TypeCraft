"""
scripts/build_release.py — reproducible PyInstaller build for TypeCraft.

Run from the repository root:

    .venv/Scripts/python scripts/build_release.py

This script is intentionally tiny: the real recipe lives in TypeCraft.spec.
The script just ensures the build is clean and prints the path to the
produced distribution folder.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = REPO_ROOT / "TypeCraft.spec"
DIST_DIR = REPO_ROOT / "dist"
BUILD_DIR = REPO_ROOT / "build"

#: Plain-language README copied in beside the exe. Written for the teacher or IT
#: volunteer who opens the folder, not for a developer — dist/ is generated, so the
#: file has to be sourced from the repo or it would vanish on the next build.
RELEASE_README_SOURCE = REPO_ROOT / "docs" / "release-readme.md"
RELEASE_README_NAME = "README.md"


def run_build(*, clean_dist: bool = True, clean_build: bool = True) -> Path:
    if clean_dist and DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if clean_build and BUILD_DIR.exists():
        # Keep only the top-level build/TypeCraft folder PyInstaller creates.
        shutil.rmtree(BUILD_DIR)

    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm", "--clean"],
        check=True,
        cwd=REPO_ROOT,
    )

    dist = DIST_DIR / "TypeCraft"
    if not dist.exists():
        raise RuntimeError(f"Expected distribution folder not found: {dist}")

    copy_release_readme(dist)
    return dist


def copy_release_readme(dist: Path) -> Path:
    """Place the end-user README beside the executable.

    Whoever copies this folder onto a school PC opens it before they open anything
    else, so it must explain starting up, backing up typecraft.db, and updating
    without losing progress.
    """
    if not RELEASE_README_SOURCE.exists():
        raise RuntimeError(f"Missing release README source: {RELEASE_README_SOURCE}")
    target = dist / RELEASE_README_NAME
    shutil.copy2(RELEASE_README_SOURCE, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the TypeCraft release folder.")
    parser.add_argument(
        "--no-clean", action="store_true",
        help="Reuse existing build/ and dist/ folders instead of removing them."
    )
    args = parser.parse_args()

    try:
        dist = run_build(clean_dist=not args.no_clean, clean_build=not args.no_clean)
    except subprocess.CalledProcessError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return exc.returncode

    exe = dist / "TypeCraft.exe"
    print(f"Build complete: {dist}")
    print(f"Executable:   {exe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
