# -*- mode: python ; coding: utf-8 -*-
"""
TypeCraft.spec — PyInstaller build recipe.

Builds a single-folder Windows distribution:

    .venv/Scripts/pyinstaller TypeCraft.spec --noconfirm --clean

The output is `dist/TypeCraft/` containing TypeCraft.exe, the _internal/
folder, and (after first run) the writable files beside the exe. This whole
folder is what a teacher copies to a USB drive (blueprint §3.3).
"""

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import os

# Repository root is the directory containing this spec file.
repo_root = os.path.dirname(os.path.abspath(SPECPATH))  # noqa: F821

# Data files to bundle as read-only resources. These map to sys._MEIPASS/assets
# and sys._MEIPASS/data at runtime, which resource_path() resolves.
datas = [
    ("typecraft/assets", "assets"),
    ("typecraft/data", "data"),
]

# Pygame pulls in some lazily-loaded submodules. Explicitly include the ones
# used at runtime so PyInstaller does not miss them.
hiddenimports = [
    "pygame.font",
    "pygame.mixer",
    "pygame.base",
]

a = Analysis(
    ["main.py"],
    pathex=[repo_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,   # keep modules as real files for readable tracebacks
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TypeCraft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX can corrupt SDL2/pygame DLLs on Windows
    console=False,    # windowed GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Uncomment once an icon file exists:
    # icon="typecraft/assets/images/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TypeCraft",
)
