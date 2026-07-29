# TypeCraft — Project State

> **Read this file first, before doing anything else.** It is the resume point for every
> session. Update it at the start and end of every task, including failed ones.

---

**Last updated:** 2026-07-29
**Current phase:** Phase 0 — repository audit and reproducible baseline
**Current active task:** none — TC-001 closed, awaiting the go-ahead for TC-002
**Last completed task:** TC-001 — baseline inventory, `.gitignore`, dev DB hygiene (2026-07-29)
**Next recommended task:** **TC-002** — normalise the package and entry point (P0, unblocks
everything: no test can run and no build can be made until the repo imports from its own root)
**Working branch:** `repair/typecraft-v1` (created from `main` at `f158a91`)

---

## 1. Overall progress

| Phase | State |
|---|---|
| 0 — Audit & baseline | **COMPLETE** — control files written, baseline committed (TC-000, TC-001) |
| 1 — Structure, deps, tests | NOT STARTED |
| 2 — Engine & metric correctness | NOT STARTED |
| 3 — Persistence & recovery | NOT STARTED |
| 4 — Scenes & core UI | NOT STARTED |
| 5 — Teacher tools & settings | NOT STARTED |
| 6 — Performance | NOT STARTED |
| 7 — Packaging, docs, release | NOT STARTED |

Tasks: 27 defined — 2 DONE, 0 IN_PROGRESS, 25 TODO. Open P0: 10. Open P1: 11.
Requirements defined: 96 FR + 14 NFR + 14 DR + 7 SR + 6 PR + 9 PK + 8 DOC + 19 AC.

**Release status: NOT RELEASABLE.** No build has ever been produced, no test has ever run,
and two confirmed data-integrity defects (D-04, D-05) can lose or corrupt student records.

---

## 2. Repository facts (verified 2026-07-29)

- Container folder `D:\CS\Projects\Type-Craft` is **not** a git repository.
- Git repository root is `D:\CS\Projects\Type-Craft\TypeCraft` — one commit (`f158a91
  "Initial commit"`), branch `main`, remote `origin/main` configured. **Every source file is
  untracked**; only the README is committed.
- 45 `.py` files, **2 065 lines** of Python (largest: `core/paths.py` 99,
  `engine/typing_engine.py` 134, `managers/database.py` 101, `engine/input_modes.py` 101,
  `scenes/teacher_dashboard.py` 101).
- Content data: `data/lessons.json` (20 lessons in 5 tiers, `schema_version` 1),
  `badges.json` (10 badges), `messages.json` (4 bands × 3 messages),
  `settings.default.json` (`volume` 0.7, `muted` false, `teacher_pin_hash` null).
- `_dev_data/` holds copies of all four JSON files plus `typecraft.db` (45 056 bytes).
- `_dev_data/typecraft.db`: all five tables + `idx_attempts_lookup` present;
  **0 profiles, 0 lesson_attempts, 0 lesson_progress, 0 profile_badges, 10 badges.**
  No real student data (confirms AS-07).
- `lesson_attempts` columns: `id, profile_id, lesson_id, status, mode, wpm_net, wpm_gross,
  accuracy, errors, max_combo, duration_sec, stars, xp_awarded, started_at, completed_at`
  — **no `total_keystrokes`, no `correct_keystrokes`** (see D-09).
- Absent: `assets/`, `tests/`, `TypeCraft.spec`, `.gitignore`, `pyproject.toml`, any
  documentation beyond a 2-line README. `requirements.txt` is **0 bytes**.
- Environment: Python **3.12.9** (MiniConda, `C:\MiniConda\python.exe`). **pygame, pytest,
  and PyInstaller are all NOT installed.** No virtual environment exists.

---

## 3. Working features confirmed by tests

**None — there is no test suite.** Everything below is code-inspection-level confidence only
and must not be reported as working until Phase 1/2 tests exist:

- Every module byte-compiles (`compileall` clean).
- `core/paths.py` implements the read-only/writable split correctly, including
  `ensure_seeded()` which skips files that already exist (DR-012 looks satisfied).
- Schema bootstrap is idempotent (`CREATE TABLE IF NOT EXISTS`) and startup
  `in_progress → incomplete` reclassification exists.
- `engine/metrics.py` formulas match blueprint §2.4 by inspection (not yet numerically
  verified against the three worked examples).
- The 20-lesson / 5-tier content set is complete and well-formed.
- No network call, no `sqlite3` import outside `managers/database.py`, no ad hoc filesystem
  path outside `core/paths.py`, and all SQL uses parameter binding except one whitelisted
  column name in the leaderboard f-string.

---

## 4. Known defects

Severity: **S1** data loss or corruption · **S2** wrong stored data or a broken requirement ·
**S3** usability/quality · **S4** hygiene.

| ID | Sev | Defect | Evidence | Task |
|---|---|---|---|---|
| D-01 | S1 | Package/import layout is unrunnable from the repo root. Modules import `TypeCraft.*` but the repo root *is* the `TypeCraft` package, so imports resolve only with the repo's **parent** on `sys.path`. `python main.py` from the repo root fails; `pytest` cannot collect. | Probe: from parent dir the import proceeds (fails later only on the missing `pygame`); blueprint §3.1 expects bare imports instead | TC-002 |
| D-02 | S4 | `requirements.txt` is 0 bytes; no dev/test/build manifest; no venv; pygame/pytest/PyInstaller absent. | file size 0; `import pygame` → ModuleNotFoundError | TC-003 |
| D-03 | S2 | No automated tests and no test infrastructure at all. | no `tests/` directory | TC-004 |
| D-04 | S1 | `Database.execute()` commits after **every** statement, so `begin()`/`rollback()` are inert. The teacher's reset-progress is therefore **non-atomic** despite its `try/except: rollback(); raise` — a failure part-way leaves a student with deleted attempts but intact XP (or vice versa). `ProgressionService.score()` has the same exposure across six separate commits. | `managers/database.py:104-108`; `scenes/teacher_dashboard.py:47-69` | TC-008 |
| D-05 | S1 | No `in_progress` checkpoint is ever written. `AttemptStatus.IN_PROGRESS` exists and startup reclassification exists, but nothing produces such a row — so a power cut mid-lesson loses the entire attempt with no recovery record. | grep: no writer of `'in_progress'` | TC-009 |
| D-06 | S1 | Closing the window mid-lesson silently discards the attempt. `Game._process_events()` handles `pygame.QUIT` by setting `running = False` and returning; the active scene is never notified. | `core/game.py:64-68` | TC-010 |
| D-07 | S2 | `BackspaceMode` double-credits a correction: `_apply_backspace()` does `errors -= 1; correct_keystrokes += 1`, then the retype does `correct_keystrokes += 1` again, while `total_keystrokes` is never decremented. One physical keystroke is credited twice and a keystroke that never happened is invented. Net effect: any attempt whose errors are all corrected reports **100 % accuracy and 0 mistakes** with an inflated `total_keystrokes` (so gross WPM is inflated and net == gross). Backspacing over an already-*correct* character has the same double-credit on retype. | `engine/typing_engine.py:92-104` | TC-006 |
| D-08 | S2 | `LockOnErrorMode` + `_error_counted[]`: a second wrong key at the same position increments `total_keystrokes` but is suppressed from `errors`, so `correct + errors != total` (FR-043) and the displayed mistake count understates reality. Accuracy is *under*-reported. | `engine/typing_engine.py:72-76, 50` | TC-006 |
| D-09 | S2 | `lesson_attempts` has no `total_keystrokes` / `correct_keystrokes` columns, yet `AttemptResult` carries them and FR-050 requires storing them. `ProgressionService.score()` silently drops them. | `PRAGMA table_info` vs `models/attempt.py:41-43` | TC-008b |
| D-10 | S2 | Leaderboard includes every profile with score 0: `ProfileManager.create()` inserts a zero-valued `lesson_progress` row and the leaderboard query has no completion filter, so a brand-new student outranks nobody but still occupies a slot. Violates FR-112. | `scenes/leaderboard.py:35-44`; `managers/profile_manager.py:28-31` | TC-012 |
| D-11 | S2 | `BadgeManager.award()` adds `xp_bonus` to `profile.total_xp` **after** `ProgressionService._award_xp()` already recomputed the level, so badge XP does not raise the level until the next attempt — and the `rising_star` / `keyboard_master` predicates evaluate a stale level. Violates FR-083. | `managers/progression.py:40-45`; `managers/badge_manager.py:53-59` | TC-013b |
| D-12 | S2 | Teacher dashboard shows only name, level, and current streak. Average net WPM, average accuracy, lessons completed, XP, badge count, and longest streak are all missing (FR-122). | `scenes/teacher_dashboard.py:111-116` | TC-013 |
| D-13 | S2 | Reset progress fires immediately on click with no confirmation step (FR-125). | `scenes/teacher_dashboard.py:34-37` | TC-013 |
| D-14 | S2 | Settings UI neither loads nor persists: volume is hard-coded to 0.7 and mute to `False` on entry, and neither is ever written to `settings.json`. Startup never applies stored values to `AudioManager`. Only the PIN persists. | `scenes/settings.py:19-47` | TC-011 |
| D-15 | S2 | Teacher PIN is a **bare unsalted SHA-256** of a 4-digit code — only 10 000 preimages, reversible in milliseconds from `settings.json`. Verification uses `==`, not a constant-time compare. Violates SR-002/SR-003. | `managers/config_manager.py:32-39` | TC-011b |
| D-16 | S3 | Visual keyboard is 4 rows × 10 keys only: **no Space, no Shift, no `'`, `-`, `?`, `[`, `]`**. It highlights the key **just typed** rather than the next expected key (FR-092), never indicates a finger (FR-093), and `highlight(None)` for Space means Space is never shown. | `ui/keyboard_renderer.py:14-19, 65-66`; `scenes/lesson.py:74` | TC-015 |
| D-17 | S3 | Target text wraps mid-word by pixel width, the wrap test `x > max_width + 60` lets the last glyph overhang the text area, and the caret is drawn after `x` has already advanced. | `scenes/lesson.py:96-119` | TC-016 |
| D-18 | S3 | No pagination or scrolling. Profile Select lays out 4 per row starting at y=160 with 164 px pitch — the 9th profile onward renders off-screen. Lesson Select lays 20 cards 5-per-row at y=120 with 150 px pitch, so the 4th row spans y≈570–700 and the star widgets clip at the window edge. The dashboard list is unbounded. | `scenes/profile_select.py:29-39`; `scenes/lesson_select.py:21-43`; `scenes/teacher_dashboard.py:28-37` | TC-014 |
| D-19 | S3 | Malformed `lessons.json` falls back to the bundled default in **total silence** — no notice, no log. A teacher's broken edit looks like it simply had no effect. Violates FR-024. | `managers/lesson_manager.py:37-42` | TC-023 |
| D-20 | S3 | Full-screen redraw: `Game._render()` does `screen.fill()` + `pygame.display.flip()` every frame, contradicting the blueprint's §5.1 dirty-rect design. The Lesson scene additionally blits ~150 cached glyph surfaces per frame. Text surfaces *are* cached so no rasterisation happens per frame. | `core/game.py:73-76`; `scenes/lesson.py:102-119` | TC-018 |
| D-21 | S3 | `assets/` does not exist. Any `ResourceManager.image()` or `.sound()` call raises; `AudioManager.play()` is never called from anywhere, so the app is completely silent. | no `assets/` directory | TC-017 |
| D-22 | S3 | No logging facility anywhere in the codebase, so FR-024/FR-134 diagnostics and NFR-013 have no channel and a field failure at the school would be undiagnosable. | grep: no `logging` import | TC-004 / TC-017 |
| D-23 | S4 | `ResourceManager.clear_text_cache()` exists but is never called; the cache is unbounded across a classroom session (NFR-014). | `ui/resource_manager.py:57-60` | TC-018 |
| D-24 | S4 | `_dev_data/` (including `typecraft.db`) and `__pycache__/` are untracked **and un-ignored** — a future `git add -A` would commit a database and byte-code. No `.gitignore` exists. | `git status --short` | TC-001 |
| D-25 | S4 | `ResultsScene._pick_message()` re-opens and re-parses `messages.json` on every scene entry instead of loading it once through a manager. Not on the frame path, so low severity. | `scenes/results.py:40-57` | TC-017 |
| D-26 | S4 | Leaderboard interpolates a column name into SQL with an f-string. The value is currently drawn from a two-element internal whitelist so it is not injectable today, but it violates SR-006's "allow-list, never interpolate" rule. | `scenes/leaderboard.py:36-44` | TC-012 |
| D-28 | S4 | No `.gitattributes`, and `core.autocrlf` is enabled — git warned "LF will be replaced by CRLF" for all 51 committed text files. The next git operation that rewrites the working tree will flip every file's line endings and produce spurious whole-file diffs, which would make TC-002's import rewrite unreviewable. | `git add` output during TC-001 | TC-002 |
| D-27 | S4 | Dead code: `LessonSelectScene._unused_prevent_lint()`; `KeyboardRenderer.highlight()` accepts a `finger` argument it ignores; `StarRating._draw_star()` imports `math` inside the function on every call. | `scenes/lesson_select.py:83`; `ui/keyboard_renderer.py:65`; `ui/star_rating.py:21` | TC-015 / TC-018 |

### Audit hypotheses — verdicts

| Hypothesis (from the assignment) | Verdict |
|---|---|
| Imports are `TypeCraft.*` but the layout may not contain a proper package | **CONFIRMED (variant)** — the repo root *is* the package, so imports need the repo's parent on `sys.path` (D-01) |
| `requirements.txt` empty | CONFIRMED — 0 bytes (D-02) |
| No automated test suite | CONFIRMED (D-03) |
| No PyInstaller spec / release workflow | CONFIRMED — no `.spec`, no build ever run |
| Image/font/avatar/sound directories absent | CONFIRMED — no `assets/` at all (D-21) |
| Full-screen redraw + `flip()` conflicts with the dirty-rect design | CONFIRMED (D-20) |
| Window close during a lesson does not save an incomplete attempt | CONFIRMED (D-06) |
| Periodic `in_progress` checkpoints not implemented | CONFIRMED (D-05) |
| Backspace correction produces incorrect accounting | **CONFIRMED, worse than stated** — double-credit invents a keystroke (D-07); a second, independent defect exists in `LockOnErrorMode` (D-08). Accuracy cannot exceed 100 % today, but it is inflated to exactly 100 % whenever all errors are corrected, and mistakes then read 0 |
| DB wrapper auto-commits, making the teacher reset non-transactional | CONFIRMED (D-04) |
| Dashboard missing avg WPM / avg accuracy / lessons completed | CONFIRMED (D-12) |
| Settings UI does not load/persist `settings.json` | CONFIRMED (D-14) |
| Leaderboard includes profiles with no completed attempts | CONFIRMED — zero-valued progress rows are created at profile creation (D-10) |
| Keyboard lacks Space, Shift, shifted punctuation, next-key and finger guidance | CONFIRMED (D-16) |
| Profile/dashboard screens lack pagination for a classroom | CONFIRMED, and Lesson Select clips its 4th row too (D-18) |
| Lesson JSON fallback does not warn the teacher | CONFIRMED (D-19) |
| Packaging/deployment/teacher/student/lesson-editing docs missing | CONFIRMED — only a 2-line README |

**Additional defects found beyond the hypothesis list:** D-09 (schema missing keystroke
columns), D-11 (badge XP applied after the level recompute), D-13 (no reset confirmation),
D-15 (weak PIN hash), D-17 (mid-word wrap + caret offset), D-22 (no logging), D-23
(unbounded text cache), D-24 (no `.gitignore`), D-26 (SQL identifier interpolation).

---

## 5. Current blockers

- **B-01** No virtual environment and no pygame/pytest/PyInstaller installed — nothing can be
  executed beyond `compileall` until TC-003. Resolution: create a venv in TC-003 and install
  from the new manifests. *(Not a hard blocker for TC-001/TC-002, which are structural.)*
- **B-02 (decision needed from the user)** **OQ-001** — Backspace correction accounting.
  Blueprint §2.4 implies no retroactive edits; the code comment claims corrections do fix the
  books; the implementation does neither correctly. TC-006 will implement the recommended
  blueprint-literal ledger unless directed otherwise. Non-blocking until TC-006.
- **B-03 (decision, low urgency)** OQ-003 — whether permissively-licensed third-party assets
  may be bundled. Affects TC-017 only.

---

## 6. Files changed

### TC-001 (last task, DONE)

- `.gitignore` — **new.** Ignores `_dev_data/`, `*.db*`, `typecraft.log`, `__pycache__/`,
  `*.py[cod]`, `.pytest_cache/`, coverage output, `.venv/`/`venv/`/`env/`, `build/`, `dist/`,
  `*.spec.bak`, editor and OS noise. `TypeCraft.spec` is deliberately **not** ignored (it is a
  committed build recipe, PK-001).
- `PROJECT_STATE.md`, `TASKS.md` — status, inventory, evidence.
- **Zero production files modified.** The inherited source was committed byte-identical to
  what was audited.

### TC-000 (DONE)

Created, documentation only — zero production files modified: `REQUIREMENTS.md`,
`ARCHITECTURE.md`, `PROJECT_PLAN.md`, `TASKS.md`, `PROJECT_STATE.md`.

---

## 7. Commands run and results (2026-07-29)

| Command | Result |
|---|---|
| `Get-ChildItem -Recurse` over the repo | 45 `.py` files, 4 JSON, 5 `_dev_data` files, blueprint + proposal; no `assets/`, `tests/`, `.spec`, `.gitignore` |
| `python --version` | `Python 3.12.9` (MiniConda) |
| `python -c "import pygame"` | **FAIL** — `ModuleNotFoundError: No module named 'pygame'` |
| `python -m pytest --version` | **FAIL** — no module named pytest |
| `python -m PyInstaller --version` | **FAIL** — no module named PyInstaller |
| `python -m compileall -q <repo>` | **PASS** — exit 0, every module compiles |
| `python -c "sys.path.insert(0,<repo>); import main"` | Reached `core/game.py:10` then failed on the missing `pygame` — proves the `TypeCraft.` import needs the repo's **parent** on the path |
| `python -c "sys.path.insert(0,<parent>); import TypeCraft.main"` | Same — resolved the package, failed only on `pygame` |
| `sqlite3` inspection of `_dev_data/typecraft.db` | 5 tables + `idx_attempts_lookup`; 0 profiles / 0 attempts / 0 progress / 0 profile_badges / 10 badges; `lesson_attempts` missing the two keystroke columns |
| `git -C <repo> log --oneline` | one commit `f158a91 Initial commit`, branch `main`, remote `origin/main` |
| `git -C <repo> status --short` | every source directory and file untracked; `_dev_data/` and `__pycache__/` untracked and un-ignored |
| Python line count over the repo | 2 065 lines across 45 files |

**No test suite has been run — no test suite exists.** No production code was executed
beyond byte-compilation and import probing.

### TC-001 (2026-07-29)

| Command | Result |
|---|---|
| line-count sweep over all `.py` (excluding `__pycache__`) | 45 files, 2 065 lines — recorded in §10 |
| `git check-ignore -v _dev_data/typecraft.db` | **PASS** — matched `.gitignore:5:_dev_data/` |
| `git check-ignore -v core/__pycache__/paths.cpython-312.pyc` | **PASS** — matched `.gitignore:12:__pycache__/` |
| `git status --short` after adding `.gitignore` | **PASS** — no `_dev_data` or `__pycache__` entry remains |
| `git checkout -b repair/typecraft-v1` | branch created from `main` @ `f158a91` |
| `git commit` (inherited baseline) | see §7 commit table |
| `git commit` (`.gitignore` + control documents) | see §7 commit table |
| `git status --short` after both commits | **PASS** — working tree clean |

Commits produced by TC-001 (branch `repair/typecraft-v1`):

| Commit message | Contents |
|---|---|
| `chore: import inherited TypeCraft implementation as audited baseline` | The inherited implementation, byte-identical to the audited state: 45 `.py` files, `data/*.json`, `main.py`, `requirements.txt` (empty), the blueprint and the proposal PDF |
| `docs: add audit control files and .gitignore (TC-000, TC-001)` | `.gitignore` + `REQUIREMENTS.md`, `ARCHITECTURE.md`, `PROJECT_PLAN.md`, `TASKS.md`, `PROJECT_STATE.md` |

Resolve hashes with `git log --oneline -3` on `repair/typecraft-v1`.

---

## 8. Important decisions made

| ID | Decision | Where recorded |
|---|---|---|
| ADR-001 | Move the code into a lowercase `typecraft/` package at the repo root, with a root `main.py` shim, so the repository is importable and testable from its own root. Deviates deliberately from blueprint §3.1 (which implies bare `core.*` imports) to avoid polluting the global module namespace. | ARCHITECTURE.md §1.2, §18 |
| ADR-002 | `assets/` and `data/` live inside the package so `resource_path()` has one stable anchor in both dev and frozen modes. | ARCHITECTURE.md §18 |
| ADR-003 | `Database` moves to `isolation_level=None` plus an explicit `transaction()` context manager; per-statement autocommit is what makes DR-010 unachievable today. | ARCHITECTURE.md §13 |
| ADR-004 | One database row per attempt, reserved on the first keystroke and promoted from `in_progress` to `complete`/`incomplete`, so checkpointing cannot create duplicates. | ARCHITECTURE.md §12 |
| ADR-005 | Ledger-style keystroke accounting; delete `_error_counted`. Makes FR-043/044/045 structural rather than incidental. | ARCHITECTURE.md §6 |
| ADR-006 | PIN moves to PBKDF2-HMAC-SHA256 with a per-install salt and `compare_digest`, with a one-time legacy-hash upgrade path. | ARCHITECTURE.md §18 |
| ADR-007 | Dirty-rect presentation via a per-scene dirty-rect list, with a full-repaint debug flag retained. | ARCHITECTURE.md §14 |
| ADR-011 | The leaderboard keeps reading the `lesson_progress` cache but filters `times_completed > 0`. | ARCHITECTURE.md §18 |
| PLAN-01 | Phase 3 is split so TC-008 (transactions) lands before TC-009 (checkpointing), which depends on it; TC-008b (schema migration) is added for D-09. | PROJECT_PLAN.md |
| PLAN-02 | TC-019 (scene smoke tests) is sequenced **before** TC-018 (dirty-rect refactor) so the refactor has a regression net. | PROJECT_PLAN.md Phase 6 |
| STATE-01 | `_dev_data/typecraft.db` is kept, not deleted — verified to contain no student data, and it is the only existing DB artefact, useful as a v1→v2 migration fixture for TC-008b. | this file |

---

## 9. Safe resume instructions

1. Read this file, then `TASKS.md`, then `REQUIREMENTS.md` and `ARCHITECTURE.md`.
2. Confirm the repository state: `git -C D:\CS\Projects\Type-Craft\TypeCraft status --short`
   and `git log --oneline -3`. Expect branch `main`.
3. Pick the **Next recommended task** named at the top of this file. Do not skip its
   dependencies as listed in `TASKS.md`.
4. Mark exactly that task `IN_PROGRESS` in `TASKS.md` and update §6 of this file with its goal
   and expected files **before** editing any code.
5. Establish a baseline first: reproduce the defect or run the relevant tests before changing
   anything.
6. Make the smallest change that satisfies the task. Do not bundle unrelated refactors.
7. Verify narrowest-first: focused tests → full `pytest` → application smoke test if UI or
   integration behaviour changed.
8. Update this file (§1, §3, §4, §6, §7, §8) and `TASKS.md` before finishing, whether the task
   succeeded or failed. Record failures honestly, with the failing test ids.

**Environment caveat for the next session:** there is no virtual environment yet and pygame,
pytest, and PyInstaller are not installed, so only `compileall`-level verification is
possible until TC-003 completes. TC-001 and TC-002 are structural and can proceed without
them, but TC-002's "app starts" check must be deferred to TC-003 and recorded as deferred.

**Do not delete:** `TypeCraft_Master_Blueprint.md`, `TypeCraft Khidmat Proposal.pdf`,
`_dev_data/` (including `typecraft.db`), or any `data/*.json`.

---

## 10. Appendix — baseline module inventory (TC-001, pre-change)

Line counts as committed in the baseline commit. Use this to detect unintended churn: any
task that changes a file not listed in its own "Files" field is out of scope.
`__init__.py` files are all 0 bytes.

| Package | Module | Lines | Role |
|---|---|---:|---|
| root | `main.py` | 7 | entry point |
| core | `app_context.py` | 27 | manager singletons, first-run seeding |
| core | `game.py` | 65 | window + 30 FPS loop (D-06, D-20 live here) |
| core | `paths.py` | 99 | read-only vs writable path split (sound) |
| core | `scene.py` | 20 | Scene ABC |
| core | `state_manager.py` | 25 | scene registry + transitions |
| engine | `input_modes.py` | 101 | three strategies (D-07, D-08) |
| engine | `metrics.py` | 47 | pure formulas |
| engine | `typing_engine.py` | 134 | one attempt (D-07, D-08) |
| managers | `badge_manager.py` | 88 | catalogue sync + predicates (D-11) |
| managers | `config_manager.py` | 34 | settings.json + PIN (D-15) |
| managers | `database.py` | 101 | sqlite wrapper (D-04, D-09) |
| managers | `lesson_manager.py` | 90 | lessons.json + unlock rule (D-19) |
| managers | `profile_manager.py` | 42 | profile CRUD (D-10 origin) |
| managers | `progression.py` | 76 | the single attempt writer (D-04, D-05, D-09, D-11) |
| managers | `streak_manager.py` | 26 | D4 streak state machine |
| models | `attempt.py` | 40 | `AttemptResult`, `KeystrokeResult` |
| models | `lesson.py` | 26 | `Lesson` + `target_text()` |
| models | `profile.py` | 13 | `Profile` |
| scenes | `leaderboard.py` | 65 | (D-10, D-26) |
| scenes | `lesson.py` | 95 | drives the engine (D-06, D-16, D-17) |
| scenes | `lesson_select.py` | 70 | (D-18, D-27) |
| scenes | `main_menu.py` | 35 | — |
| scenes | `mode_select.py` | 50 | — |
| scenes | `profile_select.py` | 75 | (D-18) |
| scenes | `results.py` | 76 | (D-25) |
| scenes | `settings.py` | 76 | (D-14) |
| scenes | `teacher_dashboard.py` | 101 | (D-04, D-12, D-13, D-18) |
| ui | `audio_manager.py` | 25 | mixer wrapper (D-21) |
| ui | `button.py` | 40 | — |
| ui | `hud.py` | 34 | live metrics |
| ui | `keyboard_renderer.py` | 62 | (D-16, D-27) |
| ui | `progress_bar.py` | 22 | — |
| ui | `resource_manager.py` | 49 | the only loader/rasteriser (D-23) |
| ui | `star_rating.py` | 29 | (D-27) |
| ui | `text_input.py` | 54 | — |
| ui | `theme.py` | 33 | colours, sizes, 8 finger colours |
| ui | `widget.py` | 13 | Widget ABC |

**Total: 2 065 lines across 45 files** (11 of them empty `__init__.py`).
Non-Python baseline content: `data/lessons.json` (20 lessons / 5 tiers),
`data/badges.json` (10), `data/messages.json` (4 bands × 3),
`data/settings.default.json`, `README.md` (2 lines), `requirements.txt` (0 bytes),
`TypeCraft_Master_Blueprint.md` (48 634 bytes), `TypeCraft Khidmat Proposal.pdf`.
