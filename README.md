# TypeCraft

An offline typing tutor game for developing keyboard literacy in The Bridge School students.

Fully offline, child-friendly, and built to run on low-end Windows 10/11 machines — 4th-gen
Intel with integrated graphics and 4 GB RAM. No internet, no accounts, no installer: the
release is one folder you copy.

- **Students** type lessons, earn stars, badges, XP, and streaks.
- **Teachers** view a dashboard, reset progress, and protect settings with a PIN.
- **School IT** deploys a single folder and backs up one file (`typecraft.db`).

📚 See the [docs](docs/) folder for detailed guides.

---

## Quick start (school)

1. Copy the release `TypeCraft/` folder to the computer.
2. Double-click `TypeCraft.exe`.
3. Create a profile for each student and start typing.

Student progress is saved in `typecraft.db` beside the executable. Back up that file regularly.

For deployment, backup, and update instructions, see [docs/deployment-and-backup.md](docs/deployment-and-backup.md).

---

## Requirements

- **Windows 10 or 11** for the release build.
- **Python 3.10 or later** for development (tested on 3.12.9).
- One runtime dependency: **pygame 2.x**.

---

## Developer setup

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1             # PowerShell
# .venv\Scripts\activate.bat           # cmd
# source .venv/Scripts/activate        # Git Bash

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

`requirements.txt` is the runtime dependency (pygame). `requirements-dev.txt` adds pytest,
coverage, hypothesis, and PyInstaller — needed to develop or cut a release, never needed on
a school machine.

## Run from source

**Activate the virtualenv first** — this is the one step people skip:

```bash
.venv\Scripts\Activate.ps1             # PowerShell
python main.py                          # or:  python -m typecraft
```

Or skip activation and name the interpreter directly, which always works:

```bash
.venv\Scripts\python.exe main.py
```

> A bare `python main.py` uses whatever `python` is on your PATH. If that is a
> machine-wide install (Anaconda, the Microsoft Store build, `C:\PythonXX`) it will not
> have pygame, and TypeCraft will tell you so and print the command to use instead.

A window opens on the Main Menu, sized to suit your screen. **F11** or **Alt+Enter**
toggles fullscreen; `--fullscreen` starts that way.

While running from source, all writable data lives in `_dev_data/` beside the package. It is
git-ignored, so development never touches a real classroom database.

## Test

```bash
pytest                  # whole suite
pytest tests/unit -q    # fast unit tests only
```

The full suite runs under the SDL dummy driver, so no window appears.

## Build a release

```bash
.venv\Scripts\python scripts/build_release.py
```

Produces `dist/TypeCraft/`, a self-contained folder that runs on Windows with no Python
installed — copy the whole folder to the target machine or a USB stick. Student data and
teacher-edited JSON are created *beside* `TypeCraft.exe`, so replacing the application files
during an update preserves everything.

You can also run PyInstaller directly:

```bash
.venv\Scripts\pyinstaller TypeCraft.spec --noconfirm --clean
```

## Repository map

```
main.py                Launcher — python main.py
typecraft/             The application package
├─ core/               Window, 30 FPS loop, scene state machine, path resolution
├─ engine/             Typing engine, the three input-mode strategies, pure metric formulas
├─ managers/           SQLite wrapper, profiles, lessons, progression, badges, streaks, config
├─ models/             Plain data holders: Profile, Lesson, AttemptResult
├─ scenes/             One module per screen
├─ ui/                 Reusable widgets, on-screen keyboard, HUD, theme, resource cache
├─ assets/             Read-only images/fonts/sounds, bundled into the build
└─ data/               Default lessons/badges/messages/settings, teacher-editable once copied
docs/                  User, teacher, deployment, and release guides
tests/                 Test suite
_dev_data/             Writable dev data — git-ignored, never committed
```

Two rules that matter more than they look:

1. **Every filesystem path comes from `typecraft/core/paths.py`.** `resource_path()` for
   read-only bundled files, `writable_data_dir()` for anything written. A plain relative
   `open("data/lessons.json")` works from source and silently breaks once packaged — and
   writing the database into the bundle wipes student progress on every launch.
2. **Only `managers/database.py` imports `sqlite3`**, and all SQL is parameterised.

## Project documents

| File | Who it is for |
|---|---|
| [`docs/teacher-quickstart.md`](docs/teacher-quickstart.md) | Teachers — first launch, profiles, PIN, dashboard |
| [`docs/student-guide.md`](docs/student-guide.md) | Students — how to play |
| [`docs/deployment-and-backup.md`](docs/deployment-and-backup.md) | School IT — install, back up, update |
| [`docs/editing-lessons.md`](docs/editing-lessons.md) | Teachers — editing `lessons.json` safely |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Anyone — when something misbehaves |
| [`docs/requirements.md`](docs/requirements.md) | Developers — numbered, testable requirements (`FR-`/`NFR-` ids cited throughout the code) |
| [`docs/architecture.md`](docs/architecture.md) | Developers — structure, decisions (ADRs), risks |
| [`docs/testing-and-release-checklist.md`](docs/testing-and-release-checklist.md) | Developers — pre-release gate |

Project tracking (task backlog, phase plan, running state) and the original requirement sources
(the master blueprint and the Khidmat proposal) lived in the repo during the rebuild and have
been retired — **`docs/requirements.md` and the git history are the record**. Each commit names
the requirement ids it satisfies and the defects it closed, so `git log --grep=FR-073` still
answers "how was this implemented, and why".
