# TypeCraft

An offline typing tutor game for developing keyboard literacy in The Bridge School students.

Fully offline, child-friendly, and built to run on low-end Windows 10/11 machines — 4th-gen
Intel with integrated graphics and 4 GB RAM. No internet, no accounts, no installer: the
release is one folder you copy.

> **Project status: under active repair — not releasable.**
> The application starts and all 20 lessons load, but there is no automated test coverage yet
> and several confirmed defects can still lose or mis-record student progress. See
> [`PROJECT_STATE.md`](PROJECT_STATE.md) for the current defect list and
> [`TASKS.md`](TASKS.md) for what is being fixed next. Do not deploy to a classroom yet.

---

## Requirements

- **Python 3.10 or later** (developed and verified on 3.12.9)
- **Windows 10 or 11** for the release build. The source also runs on other platforms but
  they are neither supported nor tested.
- One third-party runtime dependency: **pygame 2.x**. Everything else is standard library.

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

## Run

```bash
python main.py          # or:  python -m typecraft
```

Both are equivalent. A 1280×720 window opens on the Main Menu.

While running from source, all writable data — `typecraft.db`, the editable JSON, and the log
— lives in `_dev_data/` beside the package. It is git-ignored, so development never touches
a real classroom database.

## Test

```bash
pytest                  # whole suite
pytest tests/unit -q    # fast, no pygame or database
```

The test suite is being built in TC-004/TC-005; until then `pytest` collects nothing. Test
architecture is documented in [`ARCHITECTURE.md`](ARCHITECTURE.md) §15.

## Build a release

```bash
pyinstaller TypeCraft.spec
```

Produces `dist/TypeCraft/`, a self-contained folder that runs on Windows with no Python
installed — copy the whole folder to the target machine or a USB stick. Student data and
teacher-edited JSON are created *beside* `TypeCraft.exe`, so replacing the application files
during an update preserves everything.

The spec file is authored in TC-020; this command does not work yet.

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
├─ assets/             Read-only images/fonts/sounds, bundled into the build (empty — TC-017)
└─ data/               Default lessons/badges/messages/settings, teacher-editable once copied
tests/                 Test suite (TC-004)
_dev_data/             Writable dev data — git-ignored, never committed
```

Two rules that matter more than they look:

1. **Every filesystem path comes from `typecraft/core/paths.py`.** `resource_path()` for
   read-only bundled files, `writable_data_dir()` for anything written. A plain relative
   `open("data/lessons.json")` works from source and silently breaks once packaged — and
   writing the database into the bundle wipes student progress on every launch.
2. **Only `managers/database.py` imports `sqlite3`**, and all SQL is parameterised.

## Project documents

| File | What it is |
|---|---|
| [`REQUIREMENTS.md`](REQUIREMENTS.md) | Numbered, testable requirements and acceptance criteria |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Current vs target architecture, decisions, risks |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Phases, dependencies, test gates |
| [`TASKS.md`](TASKS.md) | Atomic task backlog with traceability |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | **Start here.** Current state, defects, resume point |
| `TypeCraft_Master_Blueprint.md` | Original design blueprint (requirement source) |
| `TypeCraft Khidmat Proposal.pdf` | Original proposal (requirement source) |

Teacher, student, deployment, lesson-editing, and troubleshooting guides are produced in
TC-021.
