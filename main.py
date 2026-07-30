"""
main.py — repository-root launcher.

Exists so `python main.py` works from a plain checkout with no installation
and no sys.path manipulation: the repository root is already sys.path[0], and
the `typecraft` package sits directly inside it.

Equivalent entry points, all reaching the same function:

    python main.py
    python -m typecraft
    TypeCraft.exe            (PyInstaller; this file is the spec's script)
"""

from typecraft.main import main

if __name__ == "__main__":
    main()
