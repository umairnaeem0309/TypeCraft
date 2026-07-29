# TypeCraft — Task Backlog

**Legend.** Status: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE` / `DEFERRED`.
Priority: `P0` release-blocking data-integrity or "nothing works without it";
`P1` release-blocking feature/quality; `P2` important, not blocking; `P3` nice to have.

**Rules.** One task `IN_PROGRESS` at a time. Never mark `DONE` without verification
evidence recorded in `PROJECT_STATE.md`. Tests change in the same task as the behaviour they
cover.

**Summary:** 27 tasks — 6 DONE, 0 IN_PROGRESS, 21 TODO. Open P0: 6. Open P1: 11.
**Phase 1 complete.** Test suite: 281 tests — 271 passing, 10 strict-xfail defect
reproductions awaiting TC-006, 0 unexpected failures.

| ID | Title | Phase | Status | Pri |
|---|---|---|---|---|
| TC-000 | Control files and read-only audit | 0 | DONE | P0 |
| TC-001 | Baseline inventory, `.gitignore`, dev DB hygiene | 0 | DONE | P0 |
| TC-002 | Normalise the package and entry point | 1 | DONE | P0 |
| TC-003 | Runtime and dev dependency manifests | 1 | DONE | P0 |
| TC-004 | pytest infrastructure with isolated data paths | 1 | DONE | P0 |
| TC-005 | Baseline tests for metrics and the three modes | 2 | DONE | P0 |
| TC-006 | Fix keystroke accounting (LockOnError + Backspace + D-29/D-30) | 2 | TODO | P0 |
| TC-007 | Progression, unlock, streak, badge service tests | 3 | TODO | P0 |
| TC-008 | Real transaction support in `Database` | 3 | TODO | P0 |
| TC-008b | Schema migration: keystroke columns + `schema_meta` | 3 | TODO | P0 |
| TC-009 | Active-attempt checkpoint and crash recovery | 3 | TODO | P0 |
| TC-010 | Esc and window-close persist incomplete attempts | 3 | TODO | P0 |
| TC-011 | Settings load, apply, and persist | 5 | TODO | P1 |
| TC-011b | PIN hardening and atomic settings writes | 5 | TODO | P1 |
| TC-012 | Leaderboard completed-attempt filtering | 4 | TODO | P1 |
| TC-013 | Teacher dashboard statistics + confirmed atomic reset | 5 | TODO | P1 |
| TC-013b | Badge XP applied before level recompute | 3 | TODO | P1 |
| TC-014 | Classroom-scale scrolling for profiles, lessons, dashboard | 4 | TODO | P1 |
| TC-015 | Keyboard: Space, Shift, punctuation, next-key, finger guidance | 4 | TODO | P1 |
| TC-016 | Word-wrapped target text and unambiguous cursor | 4 | TODO | P1 |
| TC-017 | Assets, logging, and graceful fallbacks | 4 | TODO | P2 |
| TC-018 | Measured dirty-rect rendering and bounded caches | 6 | TODO | P1 |
| TC-019 | Full application smoke tests | 6 | TODO | P1 |
| TC-020 | PyInstaller spec and release build | 7 | TODO | P1 |
| TC-021 | User, teacher, editing, deployment, troubleshooting docs | 7 | TODO | P1 |
| TC-022 | Release acceptance on a clean Windows target | 7 | TODO | P1 |
| TC-023 | Lesson JSON fallback warning surfaced to the teacher | 4 | TODO | P2 |

---

## TC-000 — Control files and read-only audit
- **Phase** 0 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** all (documentation baseline)
- **Depends on** —
- **Goal.** Inspect the whole repository without modifying production code and produce the
  five control files so every later task has a stable frame of reference.
- **Scope.** Read every module, JSON file, the blueprint, and the SQLite schema; run
  `compileall` and import probes; write `REQUIREMENTS.md`, `ARCHITECTURE.md`,
  `PROJECT_PLAN.md`, `TASKS.md`, `PROJECT_STATE.md`.
- **Files.** The five control files only.
- **Checks.** `python -m compileall` clean. Every task references a real requirement id;
  every requirement id appears in at least one task.
- **Acceptance.** Five files exist and are internally consistent; zero production files
  modified (`git status` shows only the new documents).
- **Notes.** Import probes must be run from the repo's parent directory — see TC-002.

## TC-001 — Baseline inventory, `.gitignore`, dev DB hygiene
- **Phase** 0 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** NFR-011, AS-07, DR-011
- **Depends on** TC-000
- **Goal.** A clean, committable baseline: nothing generated or student-data-shaped can be
  committed, and the current state is recorded before any change.
- **Scope.** Add `.gitignore` (`__pycache__/`, `*.pyc`, `_dev_data/`, `*.db`, `build/`,
  `dist/`, `.venv/`, `*.spec.bak`, `.pytest_cache/`). Record per-file line counts and a module
  inventory in `PROJECT_STATE.md`. Commit the inherited implementation untouched, then the
  audit documents plus `.gitignore`. Do **not** delete `_dev_data/typecraft.db` (verified
  empty, but it is the only existing DB artefact and the TC-008b migration fixture).
- **Files.** `.gitignore` (new); `PROJECT_STATE.md`; `TASKS.md`.
- **Checks.** `git status --short` shows no `__pycache__` or `_dev_data` entries;
  `git check-ignore -v _dev_data/typecraft.db` confirms the rule; working tree clean after
  the commits.
- **Acceptance.** ✅ Met. Two commits on branch `repair/typecraft-v1`: the inherited source as
  an untouched baseline, then `.gitignore` + the five control documents. `_dev_data/` and
  `__pycache__/` proven ignored. Working tree clean.
- **Scope deviation (recorded).** Planned as a single documents-only commit. Split into two
  because every source file was untracked: TC-002's `git mv` needs the source tracked first,
  and a separate "inherited, untouched" commit gives every later task a diffable origin.
  Work happens on branch `repair/typecraft-v1` rather than directly on `main`.

## TC-002 — Normalise the package and entry point
- **Phase** 1 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** NFR-001, NFR-011, PK-009, ADR-001, ADR-002
- **Depends on** TC-001
- **Goal.** Make the repository importable, testable, and runnable from its own root.
- **Scope.** `git mv` `core/ engine/ managers/ models/ scenes/ ui/ data/ __init__.py` into a
  new `typecraft/` package; create `typecraft/assets/{images,fonts,sounds}/` with
  `.gitkeep`; add root `main.py` shim and `typecraft/__main__.py`; mechanically rewrite every
  `TypeCraft.` import to `typecraft.`; update `core/paths.py::_project_root()` so
  `resource_path` anchors on the package directory and `writable_data_dir()` (dev mode)
  anchors on the repo root's `_dev_data`. Add `.gitattributes` (`* text=auto eol=lf`,
  `*.pdf binary`) **first, as the opening step**, so the D-28 line-ending flip cannot corrupt
  the diff of the move. **No logic changes of any other kind in this task.**
- **Files.** every `.py`; `main.py` (new); `typecraft/__main__.py` (new); `core/paths.py`;
  `.gitattributes` (new); `ARCHITECTURE.md` §1.2.
- **Checks.** `python -m compileall .` clean; `python main.py` reaches the Main Menu (manual,
  or headless with SDL dummy); `python -c "import typecraft.core.game"` from the repo root;
  a grep proves zero remaining `TypeCraft.` imports; `resource_path("data/lessons.json")`
  and `writable_data_dir()` both resolve to existing paths.
- **Acceptance.** ✅ Met, with one deferral. `compileall` clean over `typecraft/` + `main.py`;
  grep confirms **0** remaining `TypeCraft.` imports (the 4 surviving bare mentions are the
  window caption, the menu title, and two prose lines); 88 import statements rewritten across
  27 files; all 45 files recorded by git as pure renames; `resource_path()` resolves all four
  `data/*.json` plus `assets/images`; `writable_data_dir()` resolves to the pre-existing
  `<repo>/_dev_data` with `typecraft.db` intact, so the dev DB was **not** orphaned; both
  `python main.py` and `python -m typecraft` resolve the full internal import graph and fail
  only at `import pygame`. No `sys.path` manipulation exists anywhere.
- **DEFERRED to TC-003.** "Reaches the Main Menu" cannot be checked: pygame is not installed
  in this environment (defect D-02). The import chain is proven correct up to the pygame
  boundary; TC-003 must complete this check and record the result.
- **Notes.** The single widest change in the project — committed alone. Closes risk R1 and
  defects D-01 and D-28.

## TC-003 — Runtime and dev dependency manifests
- **Phase** 1 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** NFR-001, NFR-002, NFR-003, PK-009
- **Depends on** TC-002
- **Goal.** Reproducible environments for running, testing, and building.
- **Scope.** `requirements.txt` (`pygame>=2.5,<3`); `requirements-dev.txt` (`pytest`,
  `pytest-cov`, `pyinstaller>=6,<7`, optionally `hypothesis`); `pyproject.toml` with
  `[tool.pytest.ini_options]` (`testpaths=tests`, `addopts=-q`) and project metadata pinning
  `requires-python = ">=3.10"`; document the venv setup in `README.md`.
- **Files.** `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `README.md`.
- **Checks.** From a fresh venv: `pip install -r requirements.txt -r requirements-dev.txt`
  succeeds; `python -c "import pygame; print(pygame.version.ver)"` prints a 2.x version;
  `pytest --version` and `pyinstaller --version` both work. **Plus the check deferred from
  TC-002:** `python main.py` reaches the Main Menu (headless with `SDL_VIDEODRIVER=dummy` is
  acceptable evidence), and `python -m typecraft` behaves identically.
- **Acceptance.** ✅ Met. Fresh `.venv` installed from the new manifests: pygame 2.6.1,
  pytest 8.4.2, pytest-cov 7.1.0, hypothesis 6.163.0, PyInstaller 6.21.0 on Python 3.12.9.
  `pytest` runs and collects nothing (no tests until TC-004). **The deferred TC-002 check is
  closed: the application starts.** Headless probe reached `MainMenuScene`, rendered 3 frames,
  entered and rendered all 5 profile-independent scenes, loaded 20 lessons across 5 tiers,
  seeded all 5 writable files on first run, and exited `run()` cleanly on QUIT. Both
  `python main.py` and `python -m typecraft` sustained the loop for 6 s with no error.
- **Notes.** The environment audited on 2026-07-29 (MiniConda Python 3.12.9) had **no**
  pygame, pytest, or PyInstaller — a venv was required before anything could run.
  PyInstaller emits a benign "not an Anaconda environment" warning because the venv's base
  interpreter is MiniConda; re-check at TC-020 that it does not affect the build.

## TC-004 — pytest infrastructure with isolated data paths
- **Phase** 1 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** NFR-011, NFR-013, DR-011, AC-02
- **Depends on** TC-003
- **Goal.** A test suite that can never touch the developer's or a school's real data, plus
  the logging facility later error-handling requirements depend on.
- **Scope.** `tests/conftest.py` with fixtures: `writable_dir` (monkeypatches
  `core.paths.writable_data_dir` to `tmp_path`), `db` (a `Database` on a temp file),
  `sdl_dummy` (sets `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`), `fake_ctx` (an
  `AppContext` built entirely on temp paths). Add `tests/unit/test_imports.py` importing
  every module. Add `core/logging_setup.py` (rotating file handler at `log_path()`), and
  `log_path()` to `core/paths.py`. Add an import-direction test asserting the §2 layering
  rules (e.g. no `pygame` import inside `engine/` or `managers/`).
- **Files.** `tests/conftest.py`, `tests/unit/test_imports.py`,
  `tests/unit/test_layering.py`, `typecraft/core/logging_setup.py`,
  `typecraft/core/paths.py`.
- **Checks.** `pytest -q` passes; after a full run `_dev_data/` modification time is
  unchanged and no new file appeared there; the layering test fails if a `pygame` import is
  added to `engine/`.
- **Acceptance.** ✅ Met. **154 tests pass** in 2.9 s. Isolation proven, not assumed: after a
  full suite run every `_dev_data/` file still had its original 02:04:35 mtime and no
  `typecraft.log` existed there — the log appeared only when the app itself was run.
  `test_data_isolation.py` additionally walks every imported `typecraft.*` module and asserts
  no `writable_data_dir` binding escaped the redirect, and that `resource_path()` was *not*
  redirected (or first-run seeding would have nothing to copy from). Fixtures delivered:
  `writable_dir`, `seeded_dir`, `db`, `display`, `app_ctx`, `profile` — each used by at least
  one test. Coverage tooling verified: baseline **34 %** overall, **29 %** for
  `engine/` + `managers/` (AC-02 needs ≥ 85 % there; Phases 2–3 close it).
- **Extra beyond the planned scope, recorded.** `tests/unit/test_logging_setup.py` (5 tests)
  and `tests/unit/test_data_isolation.py` (8 tests) were not named in the original scope but
  are the evidence for the two acceptance claims above, so they belong here rather than in a
  later task. `typecraft/main.py` gained a 2-line `configure_logging()` call so the new
  facility is wired rather than dead code.

## TC-005 — Baseline tests for metrics and the three modes
- **Phase** 2 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** FR-030…FR-036, FR-040…FR-048, FR-050…FR-057
- **Depends on** TC-004
- **Goal.** Pin the correct behaviour in tests *before* changing the engine, and make the
  existing accounting defects visible as failures rather than opinions.
- **Scope.** `tests/unit/test_metrics.py`: accuracy, gross/net WPM, stars at the 85/92/97
  boundaries, XP against the blueprint's three worked examples, `level_for` across the full
  10-level table, `daily_streak_bonus`, and the zero/negative guards. `test_input_modes.py`: each mode's
  advance/error/backspace-permission behaviour. `test_typing_engine.py`: clean run, repeated
  errors at one position, backspace + correction, completion, empty input, stray input after
  completion. `test_invariants.py`: ≥1 000 seeded randomised keystroke sequences per mode
  asserting FR-043/044/045. Add a `clock` injection parameter to `TypingEngine` so WPM is
  deterministic (the only production change permitted in this task).
- **Files.** four new test modules; `typecraft/engine/typing_engine.py` (clock injection only).
- **Checks.** `pytest tests/unit -q`. Expect **failures** in `test_invariants.py` and the
  repeated-error and backspace cases — that is the deliverable.
- **Acceptance.** ✅ Met. **281 tests: 271 pass, 10 strict-xfail, 0 unexpected failures.**
  Defect reproductions are marked `xfail(strict=True)` with the defect id in the reason, so
  the suite stays green *and* goes red the moment TC-006 fixes them — the marker cannot be
  left behind. The 10 test ids are listed in `PROJECT_STATE.md` §7 as TC-006's acceptance
  list. Coverage: `metrics.py` 100 %, `typing_engine.py` 99 %, `input_modes.py` 94 %.
- **Findings.** `engine/metrics.py` and all three `InputMode` strategies are **correct as
  inherited** — all three blueprint XP worked examples and the whole 10-level table pass. Every
  defect is in `feed_key()`/`_apply_backspace()`. Two **new** defects found: **D-30**
  (Backspace at cursor 0 scores as a correct keystroke — 20 presses give 100 % accuracy and
  3 stars with nothing typed) and **D-29** (input after completion raises `IndexError`; the
  guard is unreachable). Also established that FR-043's equation is necessary but not
  sufficient: only D-08 unbalances it.
- **Notes.** Nothing was fixed here. One production change only: a `clock=` parameter on
  `TypingEngine` for deterministic WPM, with no behavioural effect.

## TC-006 — Fix keystroke accounting (LockOnError + Backspace + D-29/D-30)
- **Phase** 2 · **Status** TODO · **Priority** P0
- **Requirements** FR-040…FR-048, FR-050, ADR-005, OQ-001
- **Depends on** TC-005. **OQ-001 is RESOLVED** (blueprint-literal ledger) — unblocked.
- **Goal.** Make the counters a consistent ledger so accuracy, WPM, stars, XP, badges, and
  the leaderboard are all trustworthy. Fixes D-07, D-08, D-29, D-30.
- **Scope.** Per the OQ-001 resolution, Backspace touches the cursor and character status
  **only** — it never edits any counter, so no entry is ever reversed and no keystroke can be
  invented:
  1. Delete `_error_counted` so a repeated wrong key in `LockOnErrorMode` posts a full entry
     each time (`total += 1`, `errors += 1`). *(D-08)*
  2. Rewrite `_apply_backspace()` to move the cursor and reset `char_status` only, and to
     increment a new non-scoring `corrections_made` counter. *(D-07)*
  3. Make `BackspaceMode.resolve()` return `is_backspace=True` even when the cursor is at 0
     (a no-op backspace is still a backspace), so `feed_key()` can never score it on the
     normal path. *(D-30 — the highest-impact fix in the task)*
  4. Move the `cursor >= len(target)` guard **before** the `mode.resolve()` call so it is
     reachable and stray input is ignored per FR-047. *(D-29)*
  5. Expose `corrections_made`, `total_keystrokes` and `correct_keystrokes` in `metrics()`
     and `AttemptResult` for the HUD and the attempt row.
- **Files.** `typecraft/engine/typing_engine.py`, `typecraft/engine/input_modes.py`,
  `typecraft/models/attempt.py`, the Phase 2 tests, `REQUIREMENTS.md` (OQ-001 resolution),
  `ARCHITECTURE.md` §6.
- **Checks.** All **10 strict-xfail tests** listed in `PROJECT_STATE.md` §7 must pass and
  **their `xfail` markers must be removed** — `strict=True` makes the suite red otherwise, so
  a leftover marker cannot be missed. Then the full suite green, and coverage of
  `typing_engine.py` held at ≥ 99 %.
- **Acceptance.** FR-043/044/045 hold for every input sequence tested; no counter is ever
  negative; no sequence of Backspace presses can move any counter; input after completion is
  ignored rather than raising; a corrected error still costs accuracy per the OQ-001
  resolution, with `corrections_made` reported separately.
- **Notes.** Verifying with the FR-043 invariant alone is **not sufficient** — TC-005 proved
  D-07 and D-30 keep the equation balanced while corrupting the values. The exact expected
  counter assertions in `test_typing_engine.py` are the real gate.

## TC-007 — Progression, unlock, streak, badge service tests
- **Phase** 3 · **Status** TODO · **Priority** P0
- **Requirements** FR-010…FR-016, FR-060…FR-066, FR-080…FR-087, DR-002…DR-008
- **Depends on** TC-006
- **Goal.** Characterise the persistence services against a real temp database before
  restructuring their transactions.
- **Scope.** `tests/db/`: schema bootstrap idempotency; profile create seeds exactly one
  unlocked lesson; complete vs incomplete persistence; orphan `in_progress` reclassification;
  progress-cache best-value updates; unlock at 84.99/85.0/85.01 and at the final lesson;
  streak same-day/next-day/gap/rollback via injected dates; badge award idempotency across
  repeated `evaluate()`; XP and level updates including the badge bonus; leaderboard
  exclusion of zero-completion profiles; first-run JSON seeding without overwrite; malformed
  JSON fallback. `tests/unit/test_streaks.py` and `test_pin.py` for the pure parts.
- **Files.** `tests/db/test_*.py`, `tests/unit/test_streaks.py`, `tests/unit/test_pin.py`.
- **Checks.** `pytest tests/db tests/unit -q`. Expected failures document TC-008/TC-012/
  TC-013b defects (non-atomic reset, leaderboard including zero-completion profiles, badge XP
  not raising the level).
- **Acceptance.** Every requirement listed has a test; each expected failure is named in
  `PROJECT_STATE.md` and mapped to its fixing task.

## TC-008 — Real transaction support in `Database`
- **Phase** 3 · **Status** TODO · **Priority** P0
- **Requirements** DR-010, FR-126, NFR-012, NFR-013, ADR-003
- **Depends on** TC-007
- **Goal.** Make multi-statement mutations genuinely atomic. Today `execute()` commits after
  every statement, so `begin()`/`rollback()` are inert and a failed reset leaves a
  half-wiped student.
- **Scope.** Open the connection with `isolation_level=None`; add
  `transaction()` as a context manager issuing `BEGIN IMMEDIATE`, committing on clean exit,
  rolling back and re-raising on exception, and refusing to nest; make `execute()` skip its
  commit while `_in_txn`; remove `begin`/`commit`/`rollback` from the public surface (or keep
  them raising a clear error); wrap `ProgressionService.score()` and the dashboard reset in
  one transaction each; add `PRAGMA journal_mode=WAL` and `synchronous=FULL`.
- **Files.** `typecraft/managers/database.py`, `typecraft/managers/progression.py`,
  `typecraft/scenes/teacher_dashboard.py`, `tests/db/test_transactions.py`,
  `ARCHITECTURE.md` §13.
- **Checks.** A test injects a failing statement mid-transaction and asserts every table is
  byte-for-byte unchanged; a nested-transaction attempt raises; `score()` failure leaves no
  attempt row; full `pytest`.
- **Acceptance.** DR-010 and FR-126 pass; no student-data write occurs outside a transaction.
- **Notes.** Risk R2 — must land before TC-009.

## TC-008b — Schema migration: keystroke columns + `schema_meta`
- **Phase** 3 · **Status** TODO · **Priority** P0
- **Requirements** DR-003, DR-009, FR-050
- **Depends on** TC-008
- **Goal.** Store the keystroke counts FR-050 requires and give the schema a version so
  future changes are safe on a school machine that already holds data.
- **Scope.** Add `schema_meta(key, value)`; add `lesson_attempts.total_keystrokes`,
  `correct_keystrokes`, `corrections_made` via additive idempotent `ALTER TABLE`; write them
  in `ProgressionService.score()`; run migrations in `_bootstrap()` inside one transaction
  before the orphan reclassification.
- **Files.** `typecraft/managers/database.py`, `typecraft/managers/progression.py`,
  `tests/db/test_migrations.py`.
- **Checks.** Migrating a v1 database twice is a no-op the second time; existing rows keep
  their values and get the column defaults; a fresh database lands at the current version; a
  round-trip test asserts the stored counts equal the engine's counters.
- **Acceptance.** `AttemptResult` and the `lesson_attempts` columns match exactly;
  `_dev_data/typecraft.db` (v1) upgrades in place with no data loss.

## TC-009 — Active-attempt checkpoint and crash recovery
- **Phase** 3 · **Status** TODO · **Priority** P0
- **Requirements** FR-073, FR-074, FR-075, DR-010, ADR-004
- **Depends on** TC-008, TC-008b
- **Goal.** A power cut mid-lesson must leave a recoverable, correctly-classified record and
  never a duplicate row.
- **Scope.** Reserve one attempt row with status `in_progress` on the first keystroke; add
  `ProgressionService.checkpoint(engine, profile)` that UPSERTs that row on a ~10 s timer
  driven from `LessonScene.update(dt)` (never from `feed_key`); change the final
  complete/incomplete write to promote the same row rather than insert a new one; confirm
  startup reclassification runs before any aggregate read.
- **Files.** `typecraft/managers/progression.py`, `typecraft/scenes/lesson.py`,
  `typecraft/managers/database.py`, `tests/db/test_recovery.py`, `ARCHITECTURE.md` §12.
- **Checks.** A test writes a checkpoint, discards the service without finishing, constructs
  a new `Database`, and asserts exactly one row now `incomplete`; a completed attempt after
  checkpoints yields exactly one `complete` row; no database write occurs on the keystroke
  path (assert by counting `execute` calls across 100 keystrokes).
- **Acceptance.** FR-073/074/075 pass; a simulated kill loses at most the last 10 s of
  progress and never corrupts aggregates.

## TC-010 — Esc and window-close persist incomplete attempts
- **Phase** 3 · **Status** TODO · **Priority** P0
- **Requirements** FR-070, FR-071, FR-072, FR-076
- **Depends on** TC-009
- **Goal.** Closing the window mid-lesson must save the attempt. Today `pygame.QUIT` just
  stops the loop and the attempt is lost.
- **Scope.** Add `Scene.on_quit_requested()` (default no-op); `Game._process_events()` calls
  it on `QUIT` before setting `running = False`; `LessonScene.on_quit_requested()` persists an
  `incomplete` attempt when keystrokes > 0 and the lesson is unfinished; keep the existing Esc
  path and route both through one helper so they cannot diverge.
- **Files.** `typecraft/core/scene.py`, `typecraft/core/game.py`,
  `typecraft/scenes/lesson.py`, `tests/scenes/test_quit_paths.py`,
  `ARCHITECTURE.md` §3/§12/§17.
- **Checks.** Under the SDL dummy driver: feed keystrokes, post `pygame.QUIT`, run one loop
  iteration, assert exactly one `incomplete` row; same for Esc; assert **zero** rows when Esc
  is pressed before any keystroke.
- **Acceptance.** FR-070/071/072/076 pass; aggregates unchanged by either path.

## TC-011 — Settings load, apply, and persist
- **Phase** 5 · **Status** TODO · **Priority** P1
- **Requirements** FR-130, FR-131, FR-132, FR-134
- **Depends on** TC-004
- **Goal.** Volume and mute must come from `settings.json` and go back to it. Today the
  Settings screen hard-codes 0.7/unmuted and never writes either value.
- **Scope.** `AppContext` reads `volume`/`muted` from `ConfigManager` and applies them to
  `AudioManager` at startup; `SettingsScene.on_enter()` initialises its widgets from the
  config; volume and mute changes call `ConfigManager.set()`; malformed config falls back to
  defaults, records a notice, and logs.
- **Files.** `typecraft/core/app_context.py`, `typecraft/scenes/settings.py`,
  `typecraft/managers/config_manager.py`, `typecraft/ui/audio_manager.py`,
  `tests/db/test_settings.py`, `tests/scenes/test_settings_scene.py`.
- **Checks.** Set volume → new `ConfigManager` → value preserved; corrupt the file → app
  constructs, notice present, log line written; mute state round-trips.
- **Acceptance.** FR-130/131/132/134 pass.

## TC-011b — PIN hardening and atomic settings writes
- **Phase** 5 · **Status** TODO · **Priority** P1
- **Requirements** SR-001, SR-002, SR-003, FR-133, FR-135, ADR-006
- **Depends on** TC-011
- **Goal.** A 4-digit PIN behind bare SHA-256 has 10 000 preimages — trivially reversed from
  `settings.json`. And a power cut during a settings write can truncate the file.
- **Scope.** Replace the hash with `hashlib.pbkdf2_hmac('sha256', pin, salt, 100_000)` with a
  per-install random salt stored alongside; verify with `hmac.compare_digest`; accept a
  legacy unsalted hash once and transparently re-hash on the next successful entry; write
  `settings.json` atomically (temp file + `os.replace`).
- **Files.** `typecraft/managers/config_manager.py`, `tests/unit/test_pin.py`,
  `tests/db/test_settings.py`, `docs/troubleshooting.md` (lost-PIN recovery).
- **Checks.** Correct/incorrect PIN; legacy-hash upgrade path; the plaintext PIN appears in
  no file after setting it (grep the writable dir); an interrupted write leaves the previous
  valid file intact.
- **Acceptance.** SR-001/002/003, FR-133, FR-135 pass.

## TC-012 — Leaderboard completed-attempt filtering
- **Phase** 4 · **Status** TODO · **Priority** P1
- **Requirements** FR-112, FR-113, FR-114, SR-006, ADR-011
- **Depends on** TC-007
- **Goal.** Every profile currently appears on the leaderboard with score 0, because profile
  creation inserts a zero-valued `lesson_progress` row and the query has no completion filter.
- **Scope.** Add `WHERE lp.times_completed > 0` (and `HAVING MAX(score) > 0`); implement the
  documented tie-break (score desc, `created_at` asc, `id` asc); replace the f-string column
  with an explicit allow-list mapping; keep the empty-state message.
- **Files.** `typecraft/scenes/leaderboard.py`, `tests/db/test_leaderboard.py`,
  `docs/student-guide.md` (tie rule).
- **Checks.** A profile with only incomplete attempts is absent; a fresh profile is absent; a
  profile with one completed attempt appears with the right score; ties order deterministically
  across repeated runs.
- **Acceptance.** FR-112/113/114 pass.

## TC-013 — Teacher dashboard statistics + confirmed atomic reset
- **Phase** 5 · **Status** TODO · **Priority** P1
- **Requirements** FR-120…FR-127
- **Depends on** TC-008, TC-014
- **Goal.** The dashboard shows only level and streak today, and reset fires immediately with
  no confirmation and no working rollback.
- **Scope.** Add a `ProgressionService.student_summary(profile_id)` query returning average
  net WPM, average accuracy, distinct lessons completed, level, XP, badge count, current and
  longest streak, all filtered to `status='complete'`, with an explicit placeholder when
  there are no completed attempts; render those columns; add a modal confirmation before
  reset; run reset inside `db.transaction()`.
- **Files.** `typecraft/scenes/teacher_dashboard.py`, `typecraft/managers/progression.py`,
  `typecraft/ui/` (confirm dialog), `tests/db/test_dashboard_stats.py`,
  `tests/scenes/test_dashboard.py`.
- **Checks.** Statistics verified against hand-computed fixtures including a zero-completion
  profile and a mixed complete/incomplete profile; reset without confirming changes nothing;
  reset with a forced failure rolls back completely; after a successful reset the profile row
  survives and lesson 1 is unlocked.
- **Acceptance.** FR-120…FR-127 pass.

## TC-013b — Badge XP applied before level recompute
- **Phase** 3 · **Status** TODO · **Priority** P1
- **Requirements** FR-083, FR-081
- **Depends on** TC-008
- **Goal.** `BadgeManager.award()` adds `xp_bonus` after `_award_xp()` already computed the
  level, so badge XP does not raise the level until the next attempt — and the
  `rising_star` / `keyboard_master` predicates then evaluate a stale level.
- **Scope.** Recompute the level after badge XP inside the same transaction; re-evaluate the
  level-dependent predicates once after the recompute (bounded to one extra pass, no loop).
- **Files.** `typecraft/managers/progression.py`, `typecraft/managers/badge_manager.py`,
  `tests/db/test_badges.py`.
- **Checks.** A profile brought to 49 XP that then earns a 25 XP badge ends at level 2 in the
  same attempt; `rising_star` is awarded in the attempt that crosses level 5 via badge XP;
  no infinite award loop.
- **Acceptance.** FR-081/083 pass.

## TC-014 — Classroom-scale scrolling for profiles, lessons, dashboard
- **Phase** 4 · **Status** TODO · **Priority** P1
- **Requirements** FR-014, FR-026, FR-124, PR-004
- **Depends on** TC-004
- **Goal.** Profile Select overflows the window past 8 profiles, Lesson Select clips its
  fourth row of 20 cards (y ≈ 570…720), and the dashboard list has no bound at all.
- **Scope.** Add `ui/scroll_panel.py` (mouse wheel, drag, PgUp/PgDn, clamped, renders only
  visible children); adopt it in Profile Select, Lesson Select, and the dashboard; keep layout
  construction on scene entry only.
- **Files.** `typecraft/ui/scroll_panel.py` (new), `typecraft/scenes/profile_select.py`,
  `typecraft/scenes/lesson_select.py`, `typecraft/scenes/teacher_dashboard.py`,
  `tests/scenes/test_layout_bounds.py`.
- **Checks.** With 40 profiles and 20 lessons, every visible child rect lies inside
  1280×720 and no two overlap; scrolling reaches the last item; clicks map to the correct item
  after scrolling; no per-frame database query.
- **Acceptance.** FR-014/026/124 pass.

## TC-015 — Keyboard: Space, Shift, punctuation, next-key, finger guidance
- **Phase** 4 · **Status** TODO · **Priority** P1
- **Requirements** FR-090…FR-096
- **Depends on** TC-004
- **Goal.** The keyboard has 40 keys, no Space, no Shift, no `?` or `'`, highlights the key
  just *typed* instead of the *next expected* one, and never names a finger.
- **Scope.** Extend `ROWS` with a Space bar, both Shift keys, and the missing punctuation;
  add `CHAR_TO_KEY` mapping every character in `lessons.json` (including shifted pairs) to a
  base key plus a required Shift side; change the API to
  `highlight_expected(char)` driving a next-key highlight; highlight the correct Shift key
  together with the base key; add a finger caption strip naming the finger for the expected
  key; keep the single pre-rendered base layer.
- **Files.** `typecraft/ui/keyboard_renderer.py`, `typecraft/scenes/lesson.py`,
  `typecraft/ui/theme.py`, `tests/unit/test_keyboard_map.py`.
- **Checks.** A test iterates every character of every bundled lesson and asserts a key rect
  and a finger name exist; capitals highlight the opposite-hand Shift; Space is highlighted
  for a space; `prerender()` is called once per lesson entry.
- **Acceptance.** FR-090…FR-096 pass.

## TC-016 — Word-wrapped target text and unambiguous cursor
- **Phase** 4 · **Status** TODO · **Priority** P1
- **Requirements** FR-100…FR-104, NFR-007
- **Depends on** TC-004
- **Goal.** Target text currently wraps mid-word by pixel width, uses `x > max_width + 60`
  (so the last glyph on a line overhangs), and draws the cursor after advancing `x`.
- **Scope.** Pre-compute a word-wrapped layout of `(char, x, y)` once on lesson entry using
  cached glyph widths; wrap at word boundaries within the text area; draw a caret at the
  exact current character's left edge; render the space marker inside the layout.
- **Files.** `typecraft/scenes/lesson.py` (or a new `typecraft/ui/target_text.py`),
  `tests/unit/test_target_layout.py`.
- **Checks.** For the longest bundled lesson, every glyph rect lies inside the text area; no
  word is split; the caret index matches the engine cursor for a scripted sequence; layout is
  computed once (assert the layout function is not called during `render`).
- **Acceptance.** FR-100…FR-104 pass.

## TC-017 — Assets, logging, and graceful fallbacks
- **Phase** 4 · **Status** TODO · **Priority** P2
- **Requirements** FR-024, FR-134, NFR-013, AS-03, AS-06, OQ-003
- **Depends on** TC-004, TC-015
- **Goal.** `assets/` does not exist, so any `ResourceManager.image()`/`sound()` call would
  crash, and nothing degrades gracefully because there is no logging or notice channel.
- **Scope.** Create `assets/{images,fonts,sounds}`; add four generated placeholder avatars and
  a small set of permissively-licensed or synthesised short cues (key click, success, error) —
  pending OQ-003; make `image()`/`sound()` return a placeholder surface / silent stub and log
  once on a miss instead of raising; wire `AudioManager.play()` into keystroke, completion,
  and badge events; add `ui/notice.py` and render notices in every scene.
- **Files.** `typecraft/assets/**`, `typecraft/ui/resource_manager.py`,
  `typecraft/ui/audio_manager.py`, `typecraft/ui/notice.py` (new),
  `typecraft/core/app_context.py`, `tests/unit/test_resource_fallbacks.py`.
- **Checks.** With `assets/` deliberately emptied, every scene still renders and one log line
  per missing asset is written; with no audio device, `play()` is a silent no-op; a licence
  note exists for every bundled asset.
- **Acceptance.** No missing asset can crash the app; FR-024/FR-134 have a visible channel.

## TC-018 — Measured dirty-rect rendering and bounded caches
- **Phase** 6 · **Status** TODO · **Priority** P1
- **Requirements** PR-001…PR-006, NFR-006…NFR-008, NFR-014, ADR-007
- **Depends on** TC-016, TC-019
- **Goal.** `Game._render()` does a full `fill()` + `flip()` every frame and the Lesson scene
  blits ~150 glyphs per frame; the text cache is never cleared.
- **Scope.** Add a `--profile` flag logging per-phase frame timings and blit counts to CSV;
  capture a 60 s Lesson-scene baseline; introduce per-scene dirty-rect accumulation and
  `pygame.display.update(rects)` with a full-repaint debug flag; pre-composite the target
  text into per-line surfaces and re-composite only changed lines; mark the HUD dirty at most
  1 Hz for the timer field; cap the text cache and clear it on scene exit.
- **Files.** `typecraft/core/game.py`, `typecraft/core/scene.py`, all scenes,
  `typecraft/ui/resource_manager.py`, `typecraft/ui/hud.py`,
  `tests/scenes/test_render_budget.py`, `PROJECT_STATE.md` (before/after numbers).
- **Checks.** Recorded 95th-percentile frame time ≤ 33.3 ms before and after; a test
  monkeypatches `pygame.font.Font.render` and fails if called during `render()`; a test
  asserts the text cache size stays bounded over 5 000 distinct strings; manual visual pass on
  every scene.
- **Acceptance.** PR-001…PR-006 evidenced by measurement, not assertion; no visual regression.
- **Notes.** Risk R6 — land only after TC-019 exists.

## TC-019 — Full application smoke tests
- **Phase** 6 · **Status** TODO · **Priority** P1
- **Requirements** FR-001…FR-006, AC-02
- **Depends on** TC-013, TC-014, TC-015, TC-016
- **Goal.** A regression net covering the whole app before the render refactor.
- **Scope.** Under the SDL dummy driver: construct `Game`; enter and render every registered
  scene once; drive Main Menu → Profile Select → Lesson Select → Mode Select → Lesson →
  Results by synthetic events; complete a lesson and assert the Results transition; cover the
  Esc and QUIT paths; settings persistence; dashboard auth and reset confirmation.
- **Files.** `tests/scenes/test_app_smoke.py`, `tests/scenes/test_flow.py`.
- **Checks.** `pytest tests/scenes -q` green; the suite runs headless in CI-like conditions
  with no display.
- **Acceptance.** Every registered scene has an enter+render test; the main flow is covered
  end to end.

## TC-020 — PyInstaller spec and release build
- **Phase** 7 · **Status** TODO · **Priority** P1
- **Requirements** PK-001…PK-008, DR-012, DR-013
- **Depends on** TC-018, TC-019
- **Goal.** A `dist/TypeCraft/` folder that runs on a school PC with no Python and never
  writes student data inside the bundle.
- **Scope.** Author `TypeCraft.spec` (onedir, windowed, `--name TypeCraft`, icon,
  `datas` for `typecraft/assets` and `typecraft/data`); build; verify the writable-path split;
  add an automated packaging smoke test that builds, launches with a self-exit flag, asserts
  the writable files sit beside the exe and not under `_internal/`, relaunches, and asserts
  persistence.
- **Files.** `TypeCraft.spec`, `tests/packaging/test_build.py`, `docs/deployment-and-backup.md`.
- **Checks.** Build succeeds; `dist/TypeCraft/TypeCraft.exe` launches; `typecraft.db` and the
  four JSON files appear beside the exe; nothing writable appears under `_internal/`; second
  launch preserves the profile; folder relocation preserves data; replacing exe + `_internal/`
  preserves data.
- **Acceptance.** PK-001…PK-008 pass.

## TC-021 — User, teacher, editing, deployment, troubleshooting docs
- **Phase** 7 · **Status** TODO · **Priority** P1
- **Requirements** DOC-001…DOC-008
- **Depends on** TC-020
- **Goal.** The school can install, use, teach with, back up, and repair TypeCraft without
  the original developers.
- **Scope.** Rewrite `README.md` (DOC-001) and write `docs/teacher-quickstart.md`,
  `docs/student-guide.md`, `docs/deployment-and-backup.md`, `docs/editing-lessons.md`,
  `docs/troubleshooting.md`, `docs/testing-and-release-checklist.md`.
- **Files.** `README.md`, `docs/*.md`.
- **Checks.** Every command in every document executed verbatim on a clean machine; every
  screenshot/field name matches the shipped build; the lesson-editing guide's worked example
  actually loads.
- **Acceptance.** DOC-001…DOC-008 pass.

## TC-022 — Release acceptance on a clean Windows target
- **Phase** 7 · **Status** TODO · **Priority** P1
- **Requirements** AC-01…AC-19, PK-005…PK-008, NFR-006
- **Depends on** TC-021
- **Goal.** Prove the whole definition of done with recorded evidence.
- **Scope.** Execute `docs/testing-and-release-checklist.md` on a clean Windows 10 and
  Windows 11 machine (4th-gen-Intel-class if available): install nothing, run from the copied
  folder, create profiles, complete lessons in all three modes, verify unlocks, badges,
  streaks across a simulated date change, leaderboard, dashboard, reset, settings, a forced
  power-loss simulation, relocation, and a backup/restore cycle; measure frame time; record
  everything in `PROJECT_STATE.md`.
- **Files.** `PROJECT_STATE.md`, `docs/testing-and-release-checklist.md`.
- **Checks.** Every AC line marked pass with its evidence.
- **Acceptance.** AC-01…AC-19 all pass; no open P0/P1 task remains.

## TC-023 — Lesson JSON fallback warning surfaced to the teacher
- **Phase** 4 · **Status** TODO · **Priority** P2
- **Requirements** FR-023, FR-024
- **Depends on** TC-017
- **Goal.** A malformed `lessons.json` currently falls back to the bundled default in total
  silence, so a teacher's broken edit looks like their edit simply had no effect.
- **Scope.** `LessonManager.load_file()` records the specific parse/validation failure,
  appends a notice to `AppContext.notices`, and logs the file path, line, and reason; the
  notice bar shows a teacher-facing message on the Main Menu and Lesson Select.
- **Files.** `typecraft/managers/lesson_manager.py`, `typecraft/core/app_context.py`,
  `typecraft/ui/notice.py`, `tests/db/test_lesson_fallback.py`.
- **Checks.** Write a syntactically invalid `lessons.json` into the temp writable dir: the app
  starts, 20 default lessons load, a notice exists with the filename and reason, and a log
  line is written; a `schema_version` mismatch produces a distinct message.
- **Acceptance.** FR-023/024 pass.

---

## Deferred / not scheduled

| ID | Item | Why deferred |
|---|---|---|
| TC-D01 | In-app lesson editor | Out of scope (§11 of REQUIREMENTS.md) |
| TC-D02 | Cross-machine leaderboard | Out of scope — offline only |
| TC-D03 | Resizable window / fullscreen | Out of scope; fixed 1280×720 per FR-005 |
| TC-D04 | Progress export/print for teachers | OQ-005 unresolved; backup = copy the DB |
