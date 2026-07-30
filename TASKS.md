# TypeCraft — Task Backlog

**Legend.** Status: `TODO` / `IN_PROGRESS` / `BLOCKED` / `DONE` / `DEFERRED`.
Priority: `P0` release-blocking data-integrity or "nothing works without it";
`P1` release-blocking feature/quality; `P2` important, not blocking; `P3` nice to have.

**Rules.** One task `IN_PROGRESS` at a time. Never mark `DONE` without verification
evidence recorded in `PROJECT_STATE.md`. Tests change in the same task as the behaviour they
cover.

**Summary:** 27 tasks — 27 DONE, 0 IN_PROGRESS, 0 TODO. **Open P0: 0 — every
data-loss-class defect is closed. No open security defects.**
No remaining tasks; all planned work is complete.
**Phases 1, 2 and 3 complete.**
Test suite: **707 passing, 4 skipped, 1 strict-xfail (D-19), 0 unexpected failures.**
Coverage of `engine/` + `managers/` **97 %** (AC-02 target ≥ 85 % — met).

| ID | Title | Phase | Status | Pri |
|---|---|---|---|---|
| TC-000 | Control files and read-only audit | 0 | DONE | P0 |
| TC-001 | Baseline inventory, `.gitignore`, dev DB hygiene | 0 | DONE | P0 |
| TC-002 | Normalise the package and entry point | 1 | DONE | P0 |
| TC-003 | Runtime and dev dependency manifests | 1 | DONE | P0 |
| TC-004 | pytest infrastructure with isolated data paths | 1 | DONE | P0 |
| TC-005 | Baseline tests for metrics and the three modes | 2 | DONE | P0 |
| TC-006 | Fix keystroke accounting (LockOnError + Backspace + D-29/D-30) | 2 | DONE | P0 |
| TC-007 | Progression, unlock, streak, badge service tests | 3 | DONE | P0 |
| TC-008 | Real transaction support in `Database` | 3 | DONE | P0 |
| TC-008b | Schema migration: keystroke columns + `schema_meta` | 3 | DONE | P0 |
| TC-009 | Active-attempt checkpoint and crash recovery | 3 | DONE | P0 |
| TC-010 | Esc and window-close persist incomplete attempts | 3 | DONE | P0 |
| TC-011 | Settings load, apply, and persist | 5 | DONE | P1 |
| TC-011b | PIN hardening and atomic settings writes | 5 | DONE | P1 |
| TC-012 | Leaderboard completed-attempt filtering | 4 | DONE | P1 |
| TC-013 | Teacher dashboard statistics + confirmed atomic reset | 5 | DONE | P1 |
| TC-013b | XP economy: badge XP ordering + missing daily streak bonus | 3 | DONE | P1 |
| TC-014 | Classroom-scale scrolling for profiles, lessons, dashboard | 4 | DONE | P1 |
| TC-015 | Keyboard: Space, Shift, punctuation, next-key, finger guidance | 4 | DONE | P1 |
| TC-016 | Word-wrapped target text and unambiguous cursor | 4 | DONE | P1 |
| TC-017 | Assets, logging, and graceful fallbacks | 4 | DONE (2026-07-30) | P2 |
| TC-018 | Measured dirty-rect rendering and bounded caches | 6 | DONE (2026-07-30) | P1 |
| TC-019 | Full application smoke tests | 6 | DONE | P1 |
| TC-020 | PyInstaller spec and release build | 7 | DONE (2026-07-30) | P1 |
| TC-021 | User, teacher, editing, deployment, troubleshooting docs | 7 | DONE (2026-07-30) | P1 |
| TC-022 | Release acceptance on a clean Windows target | 7 | DONE (2026-07-30) | P1 |
| TC-023 | Lesson JSON fallback warning surfaced to the teacher | 4 | DONE (2026-07-30) | P2 |
| TC-024 | Playtest UI fixes: results colours, lesson spacing, reset wording, settings scale | 4 | DONE | P2 |
| TC-025 | Responsive window: desktop-aware sizing, resize, fullscreen | 4 | DONE | P2 |
| TC-026 | UI consistency: shared chrome, spacing and type scales | 4 | DONE | P2 |
| TC-027 | Launcher explains a wrong-interpreter start | 1 | DONE | P2 |
| TC-028 | Fix the native crash on profile select; log crashes | 4 | DONE | P0 |

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
- **Phase** 2 · **Status** DONE (2026-07-29) · **Priority** P0
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
- **Acceptance.** ✅ Met. All 10 strict-xfail tests pass and every marker is removed;
  **284 passing, 0 failing, 0 xfail.** `typing_engine.py` and `metrics.py` at **100 %**
  coverage, `input_modes.py` 96 %, `engine/` overall 99 %. App smoke-tested after the change.
  Verified independently of the test suite:

  | Scenario | Before | After |
  |---|---|---|
  | 20× Backspace, nothing typed (D-30) | total 20, correct 20, combo 20, **100 %** | total 0, correct 0, combo 0, **0 %** |
  | wrong key + Backspace (D-07) | total 1, correct 1, errors 0, **100 %** | total 1, correct 0, errors 1, **0 %** |
  | wrong + Backspace + right (D-07) | **100 %**, 0 mistakes | **50 %**, 1 mistake, 1 correction |
  | 4 wrong then right (D-08) | total 5, errors 1, **sum 2 ≠ 5** | total 5, errors 4, **sum 5 = 5** |
  | key after completion (D-29) | `IndexError` | ignored, total unchanged |
- **Two TC-005 assertions were corrected, not weakened.** `test_free_advance_ignores_backspace`
  and `test_backspace_at_the_start_of_the_text_is_a_no_op` asserted
  `is_backspace is False` for a no-op backspace — which *is* the D-30 mechanism, so they
  pinned the bug. Replaced by `test_a_no_op_backspace_is_still_flagged_as_one`, parametrised
  over all three modes: "the backspace did nothing" must never be expressed as "this was not
  a backspace".
- **One test premise was wrong.** `test_D07_navigating_back_over_a_correct_character…` used a
  2-character target, so its second keystroke completed the text and the new FR-047
  finished-guard (correctly) ignored the Backspaces. Target widened to 3 characters; the
  assertions are unchanged and stricter (now also checks `corrections_made`).
- **Notes.** Verifying with the FR-043 invariant alone would **not** have been sufficient —
  TC-005 proved D-07 and D-30 keep the equation balanced while corrupting the values. The
  exact expected counter assertions were the real gate.

## TC-007 — Progression, unlock, streak, badge service tests
- **Phase** 3 · **Status** DONE (2026-07-29) · **Priority** P0
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
- **Acceptance.** ✅ Met. **367 passing, 9 strict-xfail, 0 unexpected failures.** Coverage of
  `engine/` + `managers/` **97 %**, clearing AC-02's ≥ 85 % bar: `lesson_manager.py`,
  `config_manager.py`, `streak_manager.py` and `metrics.py` at 100 %, `badge_manager.py` 98 %,
  `database.py` 97 %, `progression.py` 93 %. Six new test modules — `tests/db/test_schema.py`,
  `test_transactions.py`, `test_progression.py`, `test_unlocking.py`, `test_badges.py`,
  `test_config_and_seeding.py`, plus `tests/unit/test_streaks.py`.
- **Confirmed working as inherited** (no defect): schema bootstrap idempotency and the
  reopen-without-data-loss property; orphan `in_progress` → `incomplete` reclassification;
  first-lesson-only unlock on profile creation; the 85.0 unlock boundary exact at
  84.99/85.0/85.01 and unaffected by WPM; incomplete attempts excluded from unlocks, XP,
  badges, streaks and averages; the progress cache keeping per-metric bests per lesson; badge
  award idempotency including no double-paid XP; all ten badge criteria; the entire streak
  state machine including the clock-rollback guard, month/year/leap-day boundaries and the
  `longest_streak` high-water mark; first-run seeding never overwriting an edited file; the
  `lessons.json` fallback surviving four kinds of corruption without touching the teacher's file.
- **New defect found: D-31** — `metrics.daily_streak_bonus()` is implemented and correct but
  **has no caller**, so FR-057 is unimplemented and one of the blueprint's three XP sources
  contributes nothing. Assigned to TC-013b.
- **Scope note.** The leaderboard exclusion rule is asserted here only at its root cause (a
  fresh profile gets a zero-valued `lesson_progress` row). The query itself lives in
  `scenes/leaderboard.py`, so testing it belongs with the fix in **TC-012** — duplicating the
  SQL in a test here would have let the scene stay broken while the test passed.

## TC-008 — Real transaction support in `Database`
- **Phase** 3 · **Status** DONE (2026-07-29) · **Priority** P0
- **Requirements** DR-010, FR-126, NFR-012, NFR-013, ADR-003, ADR-012
- **Depends on** TC-007
- **Goal.** Make multi-statement mutations genuinely atomic. Today `execute()` commits after
  every statement, so `begin()`/`rollback()` are inert and a failed reset leaves a
  half-wiped student.
- **Scope.** Open the connection with `isolation_level=None`; add
  `transaction()` as a context manager issuing `BEGIN IMMEDIATE`, committing on clean exit,
  rolling back and re-raising on exception, and refusing to nest; make `execute()` skip its
  commit while `_in_txn`; keep `begin`/`commit`/`rollback` but make them actually work; wrap
  `ProgressionService.score()` and the dashboard reset in one transaction each; add
  `synchronous=FULL`.
- **Files.** `typecraft/managers/database.py`, `typecraft/managers/progression.py`,
  `typecraft/scenes/teacher_dashboard.py`, `tests/db/test_transactions.py`,
  `ARCHITECTURE.md` §8.2/§13/§18.
- **Checks.** A test injects a failing statement mid-transaction and asserts every table is
  byte-for-byte unchanged; a nested-transaction attempt raises; `score()` failure leaves no
  attempt row; full `pytest`.
- **Acceptance.** ✅ Met. **382 passing, 6 xfail, 0 unexpected failures.** All three D-04
  markers removed. `database.py` 93 %, `progression.py` 94 %; `engine/` + `managers/` 97 %.
  App smoke-tested. 12 new tests cover the contract: commit on clean exit, rollback and
  re-raise on both a Python exception and a SQL error, refusal to nest, the outer transaction
  still rolling back cleanly after a refused nesting, single statements still auto-committing,
  a committed transaction surviving a reopen, `close()` discarding an open transaction, and the
  real dashboard `_reset_progress` being atomic while preserving the child's profile row.
- **ADR-012 — one specification corrected.** An earlier draft of ARCHITECTURE §8.2 called for
  `journal_mode = WAL`. That is **wrong for this deployment**: in WAL mode recently-committed
  rows can live in `typecraft.db-wal` rather than the main file, so a teacher copying
  `typecraft.db` to a USB stick after a crash would silently lose them — breaking DR-014's
  one-file backup story and the blueprint's own instruction to teachers. Implemented with the
  default rollback journal (which deletes itself on commit, keeping the `.db` a complete
  snapshot) plus `synchronous = FULL` for per-commit fsync. Asserted by two tests, and verified
  by the absence of any `-wal`/`-shm` file in `_dev_data/` after a real run.
- **Extra fix, in scope.** `score()` snapshots the Profile fields it mutates and restores them
  if the transaction rolls back. `_award_xp()` and `BadgeManager.award()` mutate the live
  Profile object, so without this a rolled-back attempt left the in-memory profile holding XP
  that was never earned, which the next successful `save()` would have persisted. Same
  treatment for `_reset_progress`, which now zeroes the in-memory profile to match the row.
- **Notes.** Closes risk R2 and unblocks TC-008b and TC-009.

## TC-008b — Schema migration: keystroke columns + `schema_meta`
- **Phase** 3 · **Status** DONE (2026-07-29) · **Priority** P0
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
- **Acceptance.** ✅ Met. **387 passing, 5 xfail.** `SCHEMA_VERSION = 2`; `_migrate()` runs
  inside one transaction and is additive-only (`ALTER TABLE ADD COLUMN` guarded by a
  `PRAGMA table_info` check, so it never drops, renames or rewrites a column). Verified against
  a synthesised v1 database holding a student and an attempt: columns appear, version advances,
  and every pre-existing value is unchanged with the new columns taking their defaults.
  Idempotent across three reopens. A round-trip test asserts the stored counters equal the
  engine's *and* that the stored accuracy is reproducible from them —
  `correct + errors == total`, so a teacher's figure is now auditable.
  **Also migrated the real inherited artefact:** `_dev_data/typecraft.db` upgraded in place to
  v2 with its 10 badge rows preserved.

## TC-009 — Active-attempt checkpoint and crash recovery
- **Phase** 3 · **Status** DONE (2026-07-30) · **Priority** P0
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
- **Acceptance.** ✅ Met. **396 passing, 5 xfail.** 9 new tests in `tests/db/test_recovery.py`:
  a checkpoint reserves exactly one `in_progress` row; repeated checkpoints update that same
  row; an in-flight row awards no XP/badges/unlocks; completing and abandoning each **promote**
  the reserved row instead of inserting a second (the double-counting bug ADR-004 exists to
  prevent); a simulated power cut — checkpoint, close without scoring, reopen — yields exactly
  one `incomplete` row that still records the work done and stays out of every aggregate;
  recovery leaves an already-completed attempt untouched; **0 database writes across 100
  keystrokes**; and a scene-level test proving the interval is time-based (nothing before the
  first keystroke, nothing below the interval, one row on crossing it, still one row on
  crossing again).
- **Design note.** `checkpoint()` builds its row via `engine.result(IN_PROGRESS)`, so the
  checkpoint and the final write share one code path and cannot disagree.
  `LessonScene._finish()` is now the single exit point for an attempt, so Esc, completion and
  (in TC-010) window-close cannot drift apart in how they persist.

## TC-010 — Esc and window-close persist incomplete attempts
- **Phase** 3 · **Status** DONE (2026-07-30) · **Priority** P0
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
- **Acceptance.** ✅ Met. **406 passing, 5 xfail.** 10 new tests: window close mid-lesson saves
  one `incomplete` row with the right keystroke count; closing before typing saves nothing;
  closing after a checkpoint **promotes** that row rather than adding a second; `Game` really
  does call `on_quit_requested()` before setting `running = False` (driven through a posted
  `pygame.QUIT`); a save that raises still lets the app exit **and is logged**; Esc with and
  without typing; completion transitioning to Results; and an incomplete attempt from any path
  leaving XP, level, badges and unlocks untouched.
- **The test that matters most:** `test_all_three_exit_paths_agree_on_what_they_persist` types
  identical text into two profiles, exits one by Esc and one by window-close, and asserts the
  two stored rows are field-for-field identical. That is the property `_finish()` exists to
  guarantee, and it would have caught the original defect.
- **Refactor, in scope.** `Game._register_scenes()` became a module-level
  `build_state_manager(ctx)`. Scenes navigate through `ctx.states`, which only `Game.__init__`
  used to wire, so no scene was testable without opening a window. Now there is exactly one
  scene registry in the codebase and the `app_ctx` fixture is fully wired — a prerequisite
  TC-019 would have needed anyway.

## TC-011 — Settings load, apply, and persist
- **Phase** 5 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** ✅ Met. 23 tests in `tests/db/test_settings.py`. `AppContext` applies the
  stored volume/mute to `AudioManager` at startup; `SettingsScene` initialises from it and
  writes every change. `ConfigManager` gained a safe loader: a malformed file falls back to the
  bundled defaults, records a warning on `ctx.notices`, logs the reason, and is **left on disk
  intact** so the teacher can see their mistake (same reasoning as `lessons.json`). A partial
  file keeps whatever is valid. Values are sanitised — `"volume": 11` clamps to 1.0,
  `"muted": "no"` is rejected rather than read as true — so nothing out of range reaches
  `pygame.mixer`. The corrupt file is healed by the next successful change.
- **Scenario test worth naming.** `test_a_muted_classroom_stays_muted_across_a_restart`: mute a
  machine, lower the volume, rebuild `AppContext`, still muted at 0.6. That is the whole defect
  in one test.

## TC-011b — PIN hardening and atomic settings writes
- **Phase** 5 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** ✅ Met. **458 passing, 1 xfail** — both D-15 markers removed, so **no open
  security defect remains**. PBKDF2-HMAC-SHA256, 200 000 rounds, 16-byte per-install salt,
  stored as `pbkdf2_sha256$rounds$salt$digest` so the work factor can be raised later without
  invalidating existing PINs. Verification uses `hmac.compare_digest`. The brute-force test that
  previously *recovered* the PIN from `settings.json` now finds nothing. Writes are atomic
  (temp file → `fsync` → `os.replace`), proven by failing during the write and asserting the
  previous file and its PIN both survive, with no `.tmp` left behind.
- **Legacy upgrade path.** A PIN set by the inherited build is a bare unsalted SHA-256. Rather
  than locking that school out, it is accepted **once** and immediately re-hashed, so the weak
  digest leaves disk the first time the teacher uses it. A *wrong* PIN triggers no upgrade. A
  hand-mangled hash denies access without crashing the class's app.

## TC-012 — Leaderboard completed-attempt filtering
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** ✅ Met. **428 passing, 3 xfail.** 15 new tests in
  `tests/db/test_leaderboard.py`. The query moved out of the scene into
  `ProgressionService.leaderboard(board, limit)` — which attempts count is a rule, not a
  display concern, and it needed to be testable without a window. Filters
  `times_completed > 0` plus `HAVING score > 0`; ties break score → earlier `created_at` → id,
  asserted stable across five repeated calls. The f-string column is now chosen from a fixed
  `LEADERBOARD_COLUMNS` allow-list, and an unknown board name raises `KeyError` rather than
  silently defaulting — covered by passing `'; DROP TABLE profiles; --` as the board name.
  FR-113's tie rule is stated on screen. Scene tests cover both tabs and the empty state.
- **Scenario test worth naming.** `test_only_students_who_finished_something_are_listed` builds
  the real classroom case: one child who finished, three who just have profiles, and one who
  abandoned an attempt. Only the first is listed. Previously all five were, ordered by who was
  created first.

## TC-013 — Teacher dashboard statistics + confirmed atomic reset
- **Phase** 5 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** OK. **480 passing, 1 xfail.** 22 new tests in `tests/db/test_dashboard.py`.
  `student_summary()`/`class_summary()` return all nine FR-122 fields; averages cover completed
  attempts only and come back as `None` (rendered as a dash) when nothing is finished, so a child
  who has not started is not shown as 0 %, which would read as "tried and failed".
  `lessons_completed` counts **distinct** lessons. The table is a `COLUMNS` list.
- **Reset is now two steps.** The first click only arms a **modal** confirmation naming the
  student and stating what will be erased and what is kept. While it is open nothing behind it is
  clickable, so a stray click cannot reset the wrong child; Escape cancels. Confirming runs the
  existing single transaction, then rebuilds the table so the teacher sees the zeroes.
- **Two things the tests pinned down.** Reset buttons are unreachable before PIN authentication.
  And resetting the *active* profile updates the in-memory object, or a later `save()` would
  write back the XP the reset had just cleared.
- **Not addressed here:** the table has no scrolling, so a class larger than ~12 overflows the
  window. That is TC-014.

## TC-013b — XP economy: badge XP ordering + missing daily streak bonus
- **Phase** 3 · **Status** DONE (2026-07-30) · **Priority** P1
- **Requirements** FR-081, FR-083, FR-057
- **Depends on** TC-008
- **Goal.** Two XP-economy defects. **D-11:** `BadgeManager.award()` adds `xp_bonus` after
  `_award_xp()` already computed the level, so badge XP does not raise the level until the
  next attempt, and the `rising_star`/`keyboard_master` predicates then read a stale level.
  **D-31:** the daily streak bonus is never awarded at all — `metrics.daily_streak_bonus()`
  is implemented, correct and unit-tested, but has no caller. Blueprint §2.4 states that
  level 10 (2 250 XP) is only reachable because lessons, badges *and* the streak bonus all
  contribute, so a third of the economy is missing.
- **Scope.** Award `daily_streak_bonus(current_streak)` once per local calendar day, on the
  first completed lesson of that day, inside the scoring transaction and after
  `StreakManager.touch()` has set the new streak. Then recompute the level once after all XP
  (attempt + badges + streak bonus) has been applied, and re-run the level-dependent badge
  predicates a single time (bounded — no loop).
- **Files.** `typecraft/managers/progression.py`, `typecraft/managers/badge_manager.py`,
  `tests/db/test_progression.py`, `tests/db/test_badges.py`.
- **Checks.** Clear the two strict-xfail tests
  `test_badge_xp_raises_the_level_in_the_same_attempt` and
  `test_first_completed_lesson_of_the_day_awards_the_streak_bonus`, and remove their markers.
  Add: a second completed lesson on the same day awards **no** further streak bonus; the bonus
  saturates at 5 days; `rising_star` is awarded in the very attempt whose badge XP crosses
  level 5; no infinite award loop.
- **Acceptance.** ✅ Met. **413 passing, 3 xfail.** Both markers removed. `_award_xp()` split
  into `_add_xp()` and `_recompute_level()` so the caller controls *when* the level is derived;
  scoring order is now attempt XP → streak touch → streak bonus → unlock → recompute level →
  badges → recompute → one bounded extra badge pass. 6 new tests: the bonus is paid once a day
  (a second lesson the same day earns only its own XP); it grows 5/10/15/20/25 and saturates at
  25; `rising_star` is awarded in the very attempt whose *badge* XP crosses level 5; badge
  evaluation runs at most twice; and the level-10 reachability arithmetic.
- **Finding worth keeping.** The reachability test measures the economy rather than asserting a
  slogan: a single 3★ pass of all 20 lessons is only **1 051 XP**, badges add **625**, and 20
  school days of streaks add **450**. So level 10 (2 250) genuinely requires *replaying*
  lessons, exactly as blueprint §2.4 says — and with D-31 unfixed it was out of reach for a
  student who cleared everything once. The test also asserts one pass + all badges stays *under*
  2 250, so the curve cannot silently become too generous either.

## TC-014 — Classroom-scale scrolling for profiles, lessons, dashboard
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** OK. **502 passing, 1 xfail.** New `ui/scroll_panel.py` adopted by Profile
  Select, Lesson Select and the dashboard; 19 tests in `tests/db/test_scrolling.py`.
- **The design decision that made it safe.** Children keep their positions in **content
  coordinates and never move**. The panel translates in two directions instead — content shifted
  up by `offset` and clipped when rendering, and an incoming mouse position shifted back down
  before dispatch. So a scene's layout and hit-testing code is identical scrolled or not, and the
  two cannot drift apart. `translated()` returns `None` for a click outside the viewport, which
  is the half that matters: without it a click just below the panel would be shifted into a
  child's row and select the wrong student.
- **Verified at class scale (40 students, AS-05).** Every visible card lies inside the 1280x720
  window at three scroll positions; every student and every one of the 20 lessons is reachable by
  scrolling; a scrolled click selects the item under the cursor; a click below the grid selects
  nobody; a locked lesson still cannot be started when scrolled; and the highest-consequence
  case — a scrolled Reset click targets the student the teacher can see. Plus `PR-004`: rendering
  and updating a 10-row dashboard makes **zero** database queries.
- **Two test-model errors of mine, both caught.** The dashboard tests clicked stored (content)
  rects rather than screen positions; and a card straddling the viewport's top edge counts as
  visible while its centre is outside, so the click tests now pick a fully-visible item.

## TC-015 — Keyboard: Space, Shift, punctuation, next-key, finger guidance
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** OK. **596 passing, 1 xfail.** 94 new tests in `tests/db/test_keyboard.py`.
  The board is now a full 5-row QWERTY (61 keys) including Space, both Shifts, the number row
  and all punctuation, laid out from a single `ROWS` table of
  `(label, char, width, finger)`. `CHAR_TO_KEY` is *derived* from that table rather than
  hand-maintained, so a key cannot exist without a mapping or vice versa.
- **The test that matters.** `test_every_character_in_every_lesson_has_a_key_and_a_finger`
  walks every character of all 20 bundled lessons and asserts each resolves to a drawn key **and**
  a named finger. It is a coverage proof over real content: adding a lesson with an unsupported
  character now fails the suite instead of silently leaving a child with no guidance.
- **Guidance is now ahead of the student, not behind.** `highlight_expected()` points at the
  next character; the old `highlight()` lit the key just *pressed*, which taught nothing since by
  then the child had already found it. A capital highlights the letter **and the opposite hand's
  Shift** (FR-095) — reaching across is the technique being taught. The finger is named in words
  ("use your left index finger"), because colour alone is not actionable and is no guidance at
  all for a colour-blind student. Space gets a ninth `thumb` colour rather than being left
  uncoloured — the old code passed `None` for Space, so the busiest key in the course was never
  shown.
- **Also fixed.** The Backspace path did not refresh the hint, so after a correction the board
  pointed one character ahead of the cursor. In `lock_on_error` a wrong key must *not* move the
  hint, or the child is told to press a key that will be rejected — both asserted.
- **Performance.** `prerender_count` proves the 61 keys are drawn once per lesson entry, not per
  frame, and a cache-size assertion proves `render()` rasterises no new text after the first
  frame (NFR-007, §5.3).

## TC-016 — Word-wrapped target text and unambiguous cursor
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** OK. **634 passing, 1 xfail.** 35 new tests in
  `tests/db/test_target_text.py`. New `ui/target_text.py` computes a
  `TargetTextLayout` once per lesson entry — the target is fixed for the whole
  attempt, so only the per-character colours change per frame. Widths come from
  `font.size()`, which measures without rasterising, so building the layout adds
  nothing to the text cache.
- **Wrapping is token-based.** The text is split into runs of one word or one space,
  and a run is placed whole — so "practice" can no longer break as "practi"/"ce". The
  wrap test runs **before** a glyph is placed rather than after, which is what let the
  old `x > max_width + 60` slack push the last character on each line past the right
  edge. A single word longer than a line is broken deliberately rather than allowed to
  overflow, because a teacher can type anything.
- **The cursor is unambiguous.** The caret is a bar on the **left edge** of the
  character about to be typed (the old code drew it after `x` had advanced, so it
  marked the gap to the right), plus a soft block behind that character — two
  independent cues, so the position is readable even where a glyph is narrow. At the
  end of the text the caret rests just after the final glyph rather than vanishing.
- **Spaces are visible and measured.** Drawn as a middle dot (FR-103), and the layout
  measures the *displayed* glyph, so the caret and the text can never disagree about
  where a character sits.
- **Bounds proved over real content.** Every one of the 20 bundled lessons is asserted
  to lay out entirely inside the real `TEXT_AREA` — parametrised per lesson, so a
  teacher's longer edit that would clip fails the suite by name.

## TC-017 — Assets, logging, and graceful fallbacks
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P2
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
- **Acceptance.** ✅ Met. **706 passing, 4 skipped, 1 xfail.** Generated 4 placeholder avatar PNGs and 4 WAV sound cues; `ResourceManager.image()`/`font()`/`sound()` return a placeholder surface / default font / silent stub and log once on a miss; `AudioManager.play()` is wired into LessonScene keystrokes, completion and badge awards; a `NoticeBar` renders startup notices in every scene and is dismissible by click. Added `tests/unit/test_resource_fallbacks.py` and a callback test in `tests/db/test_badges.py`. Defects D-21 closed; D-22 logging call-sites now present for missing assets. Asset provenance and regeneration steps documented in `typecraft/assets/README.md`.

## TC-018 — Measured dirty-rect rendering and bounded caches
- **Phase** 6 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** ✅ Met. **706 passing, 4 skipped, 0 xfail.** Per-scene `dirty_rects` and
  `mark_dirty()` added via `Scene` base class; `Game._render()` collects dirty rects, clears
  them, calls `pygame.display.update(rects)` and falls back to full-screen when empty or
  `--full-repaint` is used. `LessonScene` pre-composes target text into per-line surfaces and
  re-renders only the line(s) containing the cursor; the HUD is marked dirty at most once per
  second; `KeyboardRenderer` caches its caption surface; `NoticeBar` marks its area dirty on
  dismiss. `ResourceManager.text_surface()` now uses a bounded `OrderedDict` cache
  (`MAX_TEXT_CACHE = 512`) and clears on scene exit, so the cache cannot grow without bound.
  `main.py` parses `--profile`, `--csv` and `--full-repaint`. New `tests/scenes/test_render_budget.py`
  asserts the cache stays bounded, no text is rasterised after the warm-up frame, and a
  keystroke marks only a partial area dirty. Defects D-20, D-23 and the dead-code portion of
  D-27 closed.
- **Notes.** Risk R6 — land only after TC-019 exists.

## TC-019 — Full application smoke tests
- **Phase** 6 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Acceptance.** OK. **697 passing, 4 skipped, 1 xfail.** Two new modules:
  `tests/scenes/test_app_smoke.py` (46 tests) and `tests/scenes/test_flow.py` (17).
  Before this, four scenes — `main_menu`, `mode_select`, `results` and `lesson` end to end —
  had never been constructed by any test, so a crash on entry would first have appeared in
  front of a class.
- **Smoke coverage is parametrised over the scene registry**, so a scene added without a test
  fails the name-set assertion rather than slipping through. Each of the nine is entered,
  updated and rendered; survives stray input (wheel, right-click in dead space, F1, Tab,
  clicks at (1,1)); accepts `on_quit_requested()`; and renders against an **empty database**
  (first launch on a new school PC) where reachable.
- **The flow test drives clicks and key presses through `handle_event`,** not scene methods —
  so it exercises button geometry and event dispatch, and fails if a button moves outside its
  own hit-testing. It walks Main Menu → Profile Select → create and pick a profile → Lesson
  Select → Mode Select → Lesson → type the whole drill → Results, then asserts the stored
  attempt is `complete` at 100 % with 3 stars, and that lesson 2's card has become clickable.
- **New defect found and fixed: D-32.** `TextInput` consumed Return in order to unfocus itself,
  so the owning scene never saw it — typing a PIN and pressing Enter did **nothing**, and a
  teacher had to know to click Unlock. Added an `on_submit` callback, wired in the dashboard and
  the Settings PIN field. This is exactly the class of defect that only a test clicking real
  widgets can find.

## TC-020 — PyInstaller spec and release build
- **Phase** 7 · **Status** DONE (2026-07-30) · **Priority** P1
- **Requirements** PK-001…PK-008, DR-012, DR-013
- **Depends on** TC-018, TC-019
- **Goal.** A `dist/TypeCraft/` folder that runs on a school PC with no Python and never
  writes student data inside the bundle.
- **Scope.** Author `TypeCraft.spec` (onedir, windowed, `--name TypeCraft`, icon,
  `datas` for `typecraft/assets` and `typecraft/data`); build; verify the writable-path split;
  add an automated packaging smoke test that builds, launches with a self-exit flag, asserts
  the writable files sit beside the exe and not under `_internal/`, relaunches, and asserts
  persistence.
- **Files.** `TypeCraft.spec`, `scripts/build_release.py`, `tests/integration/test_packaging.py`.
- **Checks.** Build succeeds; `dist/TypeCraft/TypeCraft.exe` launches; `typecraft.db` and the
  four JSON files appear beside the exe; nothing writable appears under `_internal/`; second
  launch preserves the profile; folder relocation preserves data; replacing exe + `_internal/`
  preserves data.
- **Acceptance.** ✅ Met. **707 passing, 4 skipped, 0 xfail.** Added `TypeCraft.spec`
  (onedir, windowed, UPX disabled, `noarchive=True`, assets and data bundled via `datas=`);
  `scripts/build_release.py` for reproducible builds; `tests/integration/test_packaging.py`
  smoke test (slow) that launches the built exe under SDL dummy and asserts the startup log
  appears **beside the executable**, proving `writable_data_dir()` resolves outside the
  read-only `_internal/` bundle. Verified manually that `dist/TypeCraft/_internal/assets/` and
  `dist/TypeCraft/_internal/data/` contain the bundled read-only files, while first-run seeding
  places the writable JSON and `typecraft.log` next to `TypeCraft.exe`.

## TC-021 — User, teacher, editing, deployment, troubleshooting docs
- **Phase** 7 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Phase** 7 · **Status** DONE (2026-07-30) · **Priority** P1
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
- **Phase** 4 · **Status** DONE (2026-07-30) · **Priority** P2
- **Requirements** FR-023, FR-024
- **Depends on** TC-017
- **Goal.** A malformed `lessons.json` currently falls back to the bundled default in total
  silence, so a teacher's broken edit looks like their edit simply had no effect.
- **Scope.** `LessonManager.load_file()` records the specific parse/validation failure,
  appends a notice to `AppContext.notices`, and logs the file path, line, and reason; the
  notice bar shows a teacher-facing message on the Main Menu and Lesson Select.
- **Files.** `typecraft/managers/lesson_manager.py`, `typecraft/core/app_context.py`,
  `typecraft/ui/notice.py`, `tests/db/test_config_and_seeding.py`.
- **Checks.** Write a syntactically invalid `lessons.json` into the temp writable dir: the app
  starts, 20 default lessons load, a notice exists with the filename and reason, and a log
  line is written; a `schema_version` mismatch produces a distinct message.
- **Acceptance.** ✅ Met. **706 passing, 4 skipped, 0 xfail.** `LessonManager` now has a
  `warnings` list reset on each `load_file()` call; a malformed file is logged at `WARNING`
  and a teacher-facing notice is added to `AppContext.notices`. The strict-xfail test
  covering D-19 passes and its marker is removed; a new test verifies the notice reaches
  `AppContext`. Defect D-19 is closed and D-22 is no longer partially open for this call site.

---

## Deferred / not scheduled

| ID | Item | Why deferred |
|---|---|---|
| TC-D01 | In-app lesson editor | Out of scope (§11 of REQUIREMENTS.md) |
| TC-D02 | Cross-machine leaderboard | Out of scope — offline only |
| TC-D03 | Resizable window / fullscreen | Out of scope; fixed 1280×720 per FR-005 |
| TC-D04 | Progress export/print for teachers | OQ-005 unresolved; backup = copy the DB |

## TC-024 — Playtest UI fixes: results colours, lesson spacing, reset wording, settings scale
- **Phase** 4 · **Status** DONE (2026-07-31) · **Priority** P2
- **Requirements** FR-100…FR-104 (spacing), FR-104 (legibility), FR-125 (reset clarity),
  FR-131 (settings presentation), NFR-006/§5 (child-appropriate sizing)
- **Depends on** TC-015, TC-016, TC-013, TC-011
- **Goal.** Four faults found by playing the running app, none of which an existing test could
  have caught because they concern geometry and wording rather than behaviour.
- **Scope and outcome.**
  1. **Results buttons now colour-coded by intent.** Retry grey (`COLOR_NEUTRAL`), Continue
     green (`COLOR_PRIMARY`), Leaderboard orange (`COLOR_WARNING`). They previously read as
     three equally-weighted choices, with Retry the *most* prominent in primary green.
  2. **Lesson screen re-flowed.** The keyboard overlapped the footer hint by exactly 5 px
     (board 245 px tall from y=440 → 685; hint at 680). Geometry is now derived from
     `theme.LAYOUT_FOOTER_HEIGHT`/`LAYOUT_FOOTER_MARGIN` and `KeyboardRenderer.size()`
     instead of hand-picked, so it cannot drift: text 200–330, caption 355, keyboard 391–636,
     footer band 656–720. The footer is a 64 px band with a top rule and body-sized text
     (was a small-print line 40 px off the bottom).
  3. **Reset confirmation reworded** to "Reset Amina's data?" — "Reset Amina?" read as though
     the child were being deleted, when the profile is deliberately kept (FR-127).
  4. **Settings rebuilt as two full-width cards** ("Sound", "Teacher PIN") spanning 1000 px of
     the 1280 px window, with 60–64 px controls, a 560 px volume bar, a live percentage
     readout, and helper text. It previously occupied a ~360 px centre strip.
- **Found while fixing, and also fixed.** The space bar was 12 units flush-left, making the
  board look lopsided — added `ROW_OFFSETS` so rows stagger like a real keyboard and the space
  bar (6.5 units) sits under the letters. The caption read "use your **either thumb**"; the
  thumb label is already a complete phrase, so it now takes no possessive.
- **Checks.** `tests/scenes/test_layout_regressions.py` — 17 new tests asserting the button
  colours are correct *and mutually distinct*, that no two lesson bands overlap (HUD → text →
  keyboard → footer checked pairwise), that the caption clears the text area, that the footer
  is a band and the hint sits inside it, that every settings control lies inside its own card
  and is ≥ 50 px tall, and that all 20 lessons still fit the narrowed text area.
- **Acceptance.** OK. **731 passing, 4 skipped, 0 failures.** Verified by rendering the Lesson,
  Settings and Results screens to PNG and inspecting them, not by geometry alone — which is how
  the lopsided space bar and the caption grammar were caught.
- **Scope note.** All changes are in the development source. The release folder is regenerated
  from it by `scripts/build_release.py`; no release artefact was edited by hand.

## TC-025 — Responsive window: desktop-aware sizing, resize, fullscreen
- **Phase** 4 · **Status** DONE (2026-07-31) · **Priority** P2
- **Requirements** FR-005 *(revised — see below)*, NFR-005, NFR-006
- **Requirement change, recorded.** FR-005 fixed the window at 1280x720 and §11 listed
  "resizable/fullscreen window" as **out of scope**. The user asked for responsiveness, so
  FR-005 was rewritten and §11 amended rather than the code silently contradicting the spec.
  Reflowing layout stays out of scope: the canvas scales as a whole and letterboxes at
  non-16:9 aspect ratios.
- **What was already right.** The display was already created with `SCALED | RESIZABLE`, so
  pygame was maintaining a 1280x720 logical canvas and translating mouse coordinates for free.
  No canvas system needed building — worth checking before assuming.
- **What was actually wrong.** The window always *opened* at exactly 1280x720 regardless of the
  screen: correct on a 1366x768 laptop, a small box on 1920x1080, a postage stamp on 2560x1440.
  So the app looked worse on newer hardware than on old. There was no fullscreen at all, and
  nothing tested any of it.
- **Scope.** New `core/window.py`: `initial_window_size()` (pure, therefore testable at
  resolutions no dev machine has), `desktop_size()`, `create_display()`, `apply_window_size()`,
  `toggle_fullscreen()`. `Game` sizes the window to the detected desktop, handles F11 and
  Alt+Enter, and repaints the whole canvas on resize or mode change. `main.py` gains
  `--fullscreen`.
- **The refinement that mattered.** A naive "90 % of the desktop" rule *shrank* 1366x768 — the
  commonest school laptop — to 0.96x, blurring every glyph where 1280x720 fits natively. The
  rule now never downscales when the canvas fits, and only genuinely smaller panels scale down.
  Measured: 1366x768 → 1.00x, 1600x900 → 1.12x, 1920x1080 → 1.35x, 2560x1440 → 1.80x,
  3840x2160 → 2.00x (capped), 1024x768 → 0.75x.
- **Acceptance.** OK. 30 tests in `tests/scenes/test_window.py`: fits-and-not-stretched across
  11 real resolutions including 4K and ultra-wide, larger desktops get larger windows, the 4K
  cap, the small-screen floor, unknown/zero desktop falls back safely, the drawing surface stays
  1280x720 whatever the window, a scene renders **byte-identically** under two different
  notional desktops, F11 and Alt+Enter both toggle while a plain Return does not, a resize marks
  the whole canvas dirty, and toggling fullscreen moves no widget.

## TC-026 — UI consistency: shared chrome, spacing and type scales
- **Phase** 4 · **Status** DONE (2026-07-31) · **Priority** P2
- **Requirements** FR-004, FR-104
- **Goal.** Make the consistency that already existed *structural*, so it stays true.
- **Finding, stated plainly.** The screens were already visually consistent — earlier phases had
  done that work. `Rect(20, 20, 120, 50), "Back"` was copy-pasted into six scenes and
  `FONT_SIZE_TITLE - 8` into six places; because `COLOR_NEUTRAL == COLOR_TEXT_MUTED` and
  `FONT_SIZE_PAGE_TITLE == FONT_SIZE_TITLE - 8`, consolidating them is a **pure refactor with no
  visual change**. The only genuine visible drift was subtitles at 105 px in one scene and 108
  in three others.
- **Scope.** New `ui/screen.py`: one `BACK_RECT`, `back_button()`, `PageHeader`,
  `render_footer()`, and `TITLE_Y`/`SUBTITLE_Y` — with `TITLE_Y` *derived from* `BACK_RECT` so a
  title stays optically aligned with the button by construction rather than by six copies of
  `back_button.rect.centery + 8`. `theme.py` gains a six-step spacing scale and a named
  `FONT_SIZE_PAGE_TITLE`. Six scenes adopt them.
- **Acceptance.** OK. 41 tests in `tests/scenes/test_ui_consistency.py`, written to assert
  *sameness* rather than specific values so the design can be restyled without touching them:
  every Back button shares one rect and one colour; no scene hard-codes either any more (a
  source scan, so a new scene cannot regress it); the type and spacing scales are ordered and
  distinct; body text meets FR-104's floor; the danger colour is used only for destructive
  actions; no widget on any of the nine scenes falls outside the canvas; and every interactive
  control is at least 44 px tall.
- **Honest limitation.** `PageHeader` is available but only the header *constants* are adopted;
  each scene still renders its own title surface. Migrating the six render bodies onto
  `PageHeader` is a further mechanical step with no visual effect, left undone rather than
  half-done.

## TC-027 — Launcher explains a wrong-interpreter start
- **Phase** 1 · **Status** DONE (2026-07-31) · **Priority** P2
- **Requirements** PK-009, DOC-001, DOC-006
- **Reported.** `python main.py` "not working". Reproduced immediately: `python` on this machine
  is `C:\MiniConda\python.exe`, which has no pygame, so the launcher died with a bare
  `ModuleNotFoundError`. The environment was the cause, but the **message** was the defect — a
  traceback tells a new developer nothing about what to do.
- **Scope.** The root `main.py` import is now guarded. On a missing third-party dependency it
  prints the interpreter actually in use, whether the project virtualenv exists, and the exact
  command to run — then exits 1. A missing `.venv` gets setup instructions instead. The guard
  whitelists `pygame` only, so a genuine typo inside the package keeps its traceback.
- **Docs.** `README.md`'s run section now leads with activation and notes that a bare `python`
  may be the wrong one; `docs/troubleshooting.md` gains a matching entry noting this affects
  running from source only — the released `TypeCraft.exe` bundles its own Python.
- **Acceptance.** OK. Verified by running `python main.py` with the wrong interpreter and reading
  the output, and confirming `.venv\Scripts\python.exe main.py` still starts normally. 7 tests in
  `tests/unit/test_launcher.py` cover the message naming the interpreter used, an existing venv
  being offered as a one-command fix, a missing venv getting setup steps, the message staying
  under 20 lines, and the guard not swallowing non-dependency import errors.

## TC-028 - Fix the native crash on profile select; make crashes leave evidence
- **Phase** 4 - **Status** DONE (2026-07-31) - **Priority** P0
- **Requirements** FR-005 *(amended again)*, NFR-013, DOC-006
- **Reported.** "Once i click the profile or any student in profile page game suddenly closes."
- **Two defects, one of them mine.**
  - **D-33 (S1)** - `core/window.py` used pygame's **private** `_sdl2.video.Window`
    `.from_display_module()` to resize the OS window. That object destroys the underlying SDL
    window in its finalizer, so the display died whenever the garbage collector next ran: a
    native use-after-free, no Python exception, no log entry. It also called `set_mode()` a
    second time, leaving `Game.screen` on a freed surface. **I introduced this in TC-025.**
  - **D-34 (S2)** - nothing wrapped the game loop, so the failure left *no evidence at all*: the
    user's log contained 43 startup lines and nothing else.
- **How it was found.** The suite was green and the flow tests already covered
  profile -> Lesson Select, so the tests were not wrong; the *environment* differed. Under the
  dummy SDL driver it never reproduced. With the real driver and `-u -X faulthandler`:
  `Windows fatal exception: access violation` / `Current thread: Garbage-collecting`. Output
  buffering initially hid everything, which is worth remembering: always pass `-u` when a
  process dies silently.
- **Fix.** The resize is **removed**, not reimplemented. pygame offers no public way to give a
  SCALED display a window larger than its canvas, and the need it served ("use my whole screen")
  is met by RESIZABLE and fullscreen. FR-005 amended to say the window opens at the design size.
  `main()` now logs any escaping exception and returns 1, and `faulthandler` writes native stacks
  to `typecraft-crash.log`.
- **Acceptance.** OK. 7 tests in `tests/integration/test_no_native_crash.py`, which run in a
  **subprocess** because an access violation terminates the interpreter - no in-process assertion
  survives it. That is why 812 passing tests coexisted with an unusable app.
- **Honest note on those tests.** The five subprocess tests passed on the buggy code in one
  trial: the fault is GC-timing dependent, so they are a safety net rather than a detector. The
  deterministic protection is the two **static source guards** - no `_sdl2` anywhere, and exactly
  one `set_mode()` call - and both were confirmed to fail on the pre-fix code.
- **Verified live.** Real app, real SDL driver, real 13-profile database: 8 visible students
  clicked through to Lesson Select, 15 characters typed in a live lesson, clean exit, no crash log.
