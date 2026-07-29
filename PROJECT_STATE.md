# TypeCraft — Project State

> **Read this file first, before doing anything else.** It is the resume point for every
> session. Update it at the start and end of every task, including failed ones.

---

**Last updated:** 2026-07-29
**Current phase:** Phase 4 — scene flow and core UI completion (TC-012, TC-014, TC-015,
TC-016 done; TC-017 and TC-023 remain, both P2)
**Current active task:** none — TC-016 closed. **No open P0 tasks and no open security
defects.**
**Last completed task:** TC-016 — word-wrapped target text and unambiguous cursor (2026-07-30)
**Next recommended task:** **TC-019** — full application smoke tests (P1). Sequenced before
TC-018 deliberately (PLAN-02): the dirty-rect refactor needs a regression net first. TC-017
(assets, notices) and TC-023 (lessons.json warning) are the remaining P2 items and can follow.
**Working branch:** `repair/typecraft-v1` (created from `main` at `f158a91`)

---

## 1. Overall progress

| Phase | State |
|---|---|
| 0 — Audit & baseline | **COMPLETE** — control files written, baseline committed (TC-000, TC-001) |
| 1 — Structure, deps, tests | **COMPLETE** — TC-002, TC-003, TC-004 |
| 2 — Engine & metric correctness | **COMPLETE** — TC-005 (tests), TC-006 (fix) |
| 3 — Persistence & recovery | **COMPLETE** — TC-007, TC-008, TC-008b, TC-009, TC-010, TC-013b |
| 4 — Scenes & core UI | NOT STARTED — TC-012 next |
| 5 — Teacher tools & settings | NOT STARTED |
| 6 — Performance | NOT STARTED |
| 7 — Packaging, docs, release | NOT STARTED |

Tasks: 27 defined — 20 DONE, 0 IN_PROGRESS, 7 TODO. **Open P0: 0.** Open P1: 3.
Defects: **31 found** — **24 closed**, 1 partially closed (D-22), 6 open.
**Every S1 (data-loss) defect and every security defect is closed; Phases 1–3 done.**
Tests: **634 passing, 1 strict-xfail (D-19), 0 unexpected failures.**
Coverage of `engine/` + `managers/` **97 %**.
Coverage of `engine/` + `managers/` **97 %** — **AC-02's ≥ 85 % bar is met.**
100 %: `metrics.py`, `typing_engine.py`, `lesson_manager.py`, `config_manager.py`,
`streak_manager.py`. 98 %: `badge_manager.py`. 97 %: `database.py`. 96 %: `input_modes.py`.
93 %: `progression.py`. 77 %: `profile_manager.py`.

**Metrics are trustworthy, the rules layer is proven, and writes are now atomic.** TC-006
fixed the four keystroke-accounting defects; TC-007 established by test that the unlock gate,
progress cache, badge criteria, streak machine and seeding are all correct as inherited;
TC-008 made scoring an attempt and resetting a student genuinely all-or-nothing. What remains
broken: no crash checkpoint (D-05), window-close loses an attempt (D-06), the schema cannot
store the keystroke counts (D-09), the leaderboard lists students who never finished a lesson
(D-10), and the XP economy is missing two of its pieces (D-11, D-31).
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
- **Layout as of TC-002:** all source now lives in the `typecraft/` package; `main.py` is a
  repo-root launcher; `assets/{images,fonts,sounds}/` exist but are empty; `_dev_data/` stays
  outside the package and is git-ignored. See ARCHITECTURE.md §1.2.
- Still absent: `tests/`, `TypeCraft.spec`, `pyproject.toml`, `requirements-dev.txt`, any
  documentation beyond a 2-line README, any bundled asset. `requirements.txt` is **0 bytes**.
- Added since the audit: `.gitignore`, `.gitattributes`, the five control documents.
- Environment: Python **3.12.9** (MiniConda, `C:\MiniConda\python.exe`). **pygame, pytest,
  and PyInstaller are all NOT installed.** No virtual environment exists.

---

## 3. Working features

### Confirmed by execution (TC-003 headless probe, not yet by tests)

A throwaway probe under `SDL_VIDEODRIVER=dummy`, with the writable dir redirected to a temp
folder, established that **the inherited application starts and runs**:

- `Game()` constructs and the active scene is `MainMenuScene`.
- 3 full event/update/render frames execute on the Main Menu without error.
- All 5 profile-independent scenes enter and render: `main_menu`, `profile_select`,
  `leaderboard`, `settings`, `teacher_dashboard`.
- 20 lessons across 5 tiers load from `lessons.json`.
- First-run seeding creates all 5 writable files (`typecraft.db` + 4 JSON) in an empty dir.
- `run()` exits cleanly on a posted `pygame.QUIT`.
- `python main.py` and `python -m typecraft` each sustained the loop for 6 s with no error.

**Not covered by that probe:** `lesson_select`, `mode_select`, `lesson`, and `results` (all
need an active profile), any gameplay, and every metric. It is a liveness check, not a
correctness check.

### Confirmed by tests

**None — there is no test suite yet (TC-004).** Everything below is code-inspection-level
confidence only and must not be reported as working until Phase 2 tests exist:

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
| ~~D-01~~ | S1 | ~~Package/import layout is unrunnable from the repo root.~~ **CLOSED by TC-002.** Code moved to a `typecraft/` package with a root `main.py` launcher; 88 imports rewritten. Both `python main.py` and `python -m typecraft` now resolve the full internal graph from the repo root. | see §7 TC-002 | TC-002 ✅ |
| ~~D-02~~ | S4 | ~~`requirements.txt` is 0 bytes; no dev/test/build manifest; no venv.~~ **CLOSED by TC-003.** `requirements.txt`, `requirements-dev.txt`, `pyproject.toml` written; `.venv` installs pygame 2.6.1, pytest 8.4.2, pytest-cov 7.1.0, hypothesis 6.163.0, PyInstaller 6.21.0. | see §7 TC-003 | TC-003 ✅ |
| ~~D-03~~ | S2 | ~~No automated tests and no test infrastructure at all.~~ **CLOSED by TC-004.** `tests/conftest.py` with 6 fixtures + 154 passing tests covering imports, layering rules, data isolation, and logging. Behavioural coverage of the engine and managers is still absent — that is TC-005/TC-007, not this defect. | see §7 TC-004 | TC-004 ✅ |
| ~~D-04~~ | S1 | ~~`Database.execute()` committed after **every** statement, so `begin()`/`rollback()` were inert and the teacher's reset-progress was non-atomic despite its `try/except: rollback(); raise`.~~ **CLOSED by TC-008.** Connection now opens with `isolation_level=None` (autocommit) plus a `transaction()` context manager that issues `BEGIN IMMEDIATE`, commits on clean exit, rolls back and re-raises on any exception, and refuses to nest. `score()` and `_reset_progress()` are each one transaction. Verified by forced mid-operation failures leaving every table unchanged. | `managers/database.py`, `managers/progression.py`, `scenes/teacher_dashboard.py`; `tests/db/test_transactions.py` | TC-008 ✅ |
| ~~D-05~~ | S1 | ~~No `in_progress` checkpoint was ever written, so a power cut mid-lesson lost the whole attempt.~~ **CLOSED by TC-009.** `ProgressionService.checkpoint()` reserves one row on the first checkpoint and UPSERTs it thereafter, driven from `LessonScene.update()` on a 10 s timer (**0 database writes across 100 keystrokes**, asserted). `score()` promotes that same row instead of inserting a second, so one attempt is always one row (ADR-004). Simulated power cut verified end to end: exactly one `incomplete` row, retaining the work done, excluded from every aggregate. | `managers/progression.py`, `scenes/lesson.py`; `tests/db/test_recovery.py` | TC-009 ✅ |
| ~~D-06~~ | S1 | ~~Closing the window mid-lesson silently discarded the attempt — `pygame.QUIT` set `running = False` without notifying the active scene.~~ **CLOSED by TC-010.** New `Scene.on_quit_requested()` hook, `GameStateManager.notify_quit()`, and `Game._request_quit()` which calls it before stopping the loop; `LessonScene` routes it through the same `_finish()` as Esc and completion. A failure there is logged and still permits exit. Verified with a posted `pygame.QUIT`, and by a test asserting Esc and window-close produce field-for-field identical rows. | `core/scene.py`, `core/state_manager.py`, `core/game.py`, `scenes/lesson.py`; `tests/db/test_quit_paths.py` | TC-010 ✅ |
| ~~D-07~~ | S2 | ~~`BackspaceMode` erases errors and credits keystrokes that were never pressed.~~ **CLOSED by TC-006.** `_apply_backspace()` is now counter-neutral — Backspace moves the cursor, clears the character it uncovers, increments the non-scoring `corrections_made`, and touches no metric. **Verified:** wrong key + Backspace now reports `total=1 correct=0 errors=1` → **0 %** (was 1/1/0 → 100 %); wrong + Backspace + right reports **50 %** with 1 mistake and 1 correction (was 100 %, 0 mistakes). *Audit note corrected during TC-005: `total_keystrokes` was never inflated and FR-043's equation always balanced — the values were semantically wrong, not arithmetically inconsistent, which is why exact expected counters were the real gate.* | `engine/typing_engine.py`; `test_D07_*` | TC-006 ✅ |
| ~~D-08~~ | S2 | ~~`_error_counted[]` suppressed repeat errors, so `correct + errors != total`.~~ **CLOSED by TC-006.** `_error_counted` deleted; every wrong keystroke posts its own error. **Verified:** 4 wrong keys then the right one now reports `total=5 correct=1 errors=4`, sum 5 = total (was sum 2 ≠ 5). Was the only defect that unbalanced FR-043's equation, and only in `lock_on_error`. | `engine/typing_engine.py`; `test_D08_*`, `test_ledger_holds_over_randomised_sequences[lock_on_error]` | TC-006 ✅ |
| ~~D-29~~ | S3 | ~~Input after completion raised `IndexError` because the `cursor >= len(target)` guard sat *after* `mode.resolve()`, which indexes `target[cursor]`.~~ **CLOSED by TC-006.** The guard moved ahead of `resolve()` and now covers Backspace too, so a finished attempt is genuinely immutable (FR-047). **Verified:** a key after completion is ignored and leaves the counters untouched. | `engine/typing_engine.py`; `test_D29_input_after_completion_is_ignored` | TC-006 ✅ |
| ~~D-30~~ | S2 | ~~**Accuracy could be farmed with Backspace.** `resolve()` returned `is_backspace=False` at cursor 0, so `feed_key()` scored the Backspace as a **correct keystroke** — 20 presses before typing anything gave 100 % accuracy, combo 20, 3 stars and an unlock with nothing typed.~~ **CLOSED by TC-006.** A no-op backspace now reports `is_backspace=True` in all three modes, so it can never reach the scoring path. **Verified:** 20 presses now report `total=0 correct=0 combo=0` → **0 %**. Guarded by `test_a_no_op_backspace_is_still_flagged_as_one`, parametrised over all three modes. | `engine/input_modes.py`; `test_D30_*`, `test_only_typing_can_produce_accuracy` | TC-006 ✅ |
| ~~D-09~~ | S2 | ~~`lesson_attempts` had no `total_keystrokes` / `correct_keystrokes` columns, so `score()` silently dropped them and no stored accuracy was auditable.~~ **CLOSED by TC-008b.** Migration to `SCHEMA_VERSION = 2` adds `total_keystrokes`, `correct_keystrokes` and `corrections_made`; `score()` writes all three. Additive-only and idempotent, run in one transaction, versioned via a new `schema_meta` table (DR-009). The real inherited `_dev_data/typecraft.db` upgraded in place with its 10 badge rows preserved. | `managers/database.py`, `managers/progression.py`; `tests/db/test_schema.py` | TC-008b ✅ |
| ~~D-10~~ | S2 | ~~Every profile appeared on the leaderboard with score 0: profile creation seeds a zero-valued `lesson_progress` row and the query had no completion filter, so in a class of thirty the ten slots went to whoever was created first.~~ **CLOSED by TC-012.** Query moved to `ProgressionService.leaderboard()` with `times_completed > 0` and `HAVING score > 0`, a stable score→`created_at`→id tie-break, and the sort column taken from a fixed allow-list (SR-006). | `managers/progression.py`, `scenes/leaderboard.py`; `tests/db/test_leaderboard.py` | TC-012 ✅ |
| ~~D-11~~ | S2 | ~~`BadgeManager.award()` added `xp_bonus` after `_award_xp()` had already recomputed the level, so badge XP did not count until a later attempt and the `rising_star`/`keyboard_master` predicates read a stale level.~~ **CLOSED by TC-013b.** `_award_xp()` split into `_add_xp()` + `_recompute_level()`; the level is derived after *all* XP, and one bounded extra badge pass catches level-dependent badges. Verified: badge XP crossing level 5 awards `rising_star` in the same attempt. | `managers/progression.py`; `tests/db/test_progression.py` | TC-013b ✅ |
| ~~D-12~~ | S2 | ~~Dashboard showed only name, level and current streak - no averages, lessons completed, XP or badge count.~~ **CLOSED by TC-013.** `student_summary()`/`class_summary()` supply all nine FR-122 fields; averages are over completed attempts only and render a dash when nothing is finished; `lessons_completed` counts distinct lessons. | `managers/progression.py`, `scenes/teacher_dashboard.py`; `tests/db/test_dashboard.py` | TC-013 OK |
| ~~D-13~~ | S2 | ~~Reset progress fired immediately on a single click, with no confirmation, beside a column of identical buttons.~~ **CLOSED by TC-013.** The first click arms a modal confirmation naming the student and what will be erased; nothing behind it is clickable; Escape cancels; confirming runs the existing transaction and refreshes the table. | `scenes/teacher_dashboard.py`; `tests/db/test_dashboard.py` | TC-013 OK |
| ~~D-14~~ | S2 | ~~Settings neither loaded nor persisted: volume hard-coded to 0.7 and mute to `False` on entry, never written back, and startup never applied stored values.~~ **CLOSED by TC-011.** `AppContext` applies stored volume/mute to `AudioManager`; `SettingsScene` initialises from it and writes every change; a corrupt file falls back with a visible notice + log and is healed by the next change. | `core/app_context.py`, `scenes/settings.py`, `managers/config_manager.py`; `tests/db/test_settings.py` | TC-011 ✅ |
| ~~D-15~~ | S2 | ~~Teacher PIN was a bare unsalted SHA-256 of four digits — 10 000 preimages, recoverable from `settings.json` in milliseconds — compared with `==`.~~ **CLOSED by TC-011b.** PBKDF2-HMAC-SHA256, 200 000 rounds, 16-byte per-install salt, self-describing `pbkdf2_sha256$rounds$salt$digest` format, verified with `hmac.compare_digest`. The brute-force test that used to recover the PIN now finds nothing. Legacy hashes are accepted once and upgraded in place. | `managers/config_manager.py`; `tests/db/test_config_and_seeding.py` | TC-011b ✅ |
| ~~D-16~~ | S3 | ~~Keyboard was 4x10 letter keys: no Space (the most-typed character in the course), no Shift, none of the punctuation Tier 4 is built from; it highlighted the key just *pressed* rather than the next expected one, and never named a finger.~~ **CLOSED by TC-015.** Full 5-row 61-key board from a single `ROWS` table with `CHAR_TO_KEY` derived from it; `highlight_expected()` guides the next character; a capital lights the letter plus the opposite hand's Shift; the finger is named in words. Coverage proved over every character of all 20 lessons. | `ui/keyboard_renderer.py`, `ui/theme.py`, `scenes/lesson.py`; `tests/db/test_keyboard.py` | TC-015 OK |
| ~~D-17~~ | S3 | ~~Target text wrapped mid-word by pixel width; the `x > max_width + 60` test fired only after the offending glyph was drawn, so the last character on each line overhung the area; and the caret was drawn after `x` had advanced, marking the gap to the right of the character it meant.~~ **CLOSED by TC-016.** New `ui/target_text.py` with token-based wrapping (words placed whole), the wrap test before placement, a caret on the character's left edge plus a block behind it, and visible measured space markers. Bounds asserted for all 20 lessons in the real text area. | `ui/target_text.py`, `scenes/lesson.py`; `tests/db/test_target_text.py` | TC-016 OK |
| ~~D-18~~ | S3 | ~~No pagination or scrolling: Profile Select ran off the window from the 9th child, Lesson Select clipped its 4th row of cards (so the last five lessons could not be started), and the dashboard list was unbounded.~~ **CLOSED by TC-014.** New `ui/scroll_panel.py` adopted by all three. Children keep content coordinates; the panel translates rendering up and input back down, so layout and hit-testing cannot drift apart. Verified at 40 students: everything visible is inside the window, everything is reachable, and a scrolled click hits the item under the cursor. | `ui/scroll_panel.py`, `scenes/profile_select.py`, `scenes/lesson_select.py`, `scenes/teacher_dashboard.py`; `tests/db/test_scrolling.py` | TC-014 OK |
| D-19 | S3 | Malformed `lessons.json` falls back to the bundled default in **total silence** — no notice, no log. A teacher's broken edit looks like it simply had no effect. Violates FR-024. | `managers/lesson_manager.py:37-42` | TC-023 |
| D-20 | S3 | Full-screen redraw: `Game._render()` does `screen.fill()` + `pygame.display.flip()` every frame, contradicting the blueprint's §5.1 dirty-rect design. The Lesson scene additionally blits ~150 cached glyph surfaces per frame. Text surfaces *are* cached so no rasterisation happens per frame. | `core/game.py:73-76`; `scenes/lesson.py:102-119` | TC-018 |
| D-21 | S3 | `assets/` does not exist. Any `ResourceManager.image()` or `.sound()` call raises; `AudioManager.play()` is never called from anywhere, so the app is completely silent. | no `assets/` directory | TC-017 |
| D-22 | S3 | **PARTIALLY CLOSED by TC-004.** The facility now exists — `core/logging_setup.py`, a rotating file at `log_path()`, configured from `typecraft/main.py`, idempotent, non-fatal if the file cannot be opened; verified end to end (`typecraft.log` written on a real run). **Still open:** the FR-024/FR-134 call sites do not log yet, so a malformed `lessons.json` or `settings.json` is still rejected silently. | log written on a real app run; no `logging` import in `managers/` yet | TC-011, TC-017, TC-023 |
| ~~D-31~~ | S2 | ~~The daily streak bonus was never awarded — `metrics.daily_streak_bonus()` had no caller, so FR-057 was unimplemented and a third of the XP economy contributed nothing.~~ **CLOSED by TC-013b.** Awarded once per local calendar day on the first completed lesson, inside the scoring transaction and after the streak is touched. Verified: 5/10/15/20/25 then saturating, once per day only. | `managers/progression.py`; `tests/db/test_progression.py` | TC-013b ✅ |
| D-23 | S4 | `ResourceManager.clear_text_cache()` exists but is never called; the cache is unbounded across a classroom session (NFR-014). | `ui/resource_manager.py:57-60` | TC-018 |
| D-24 | S4 | `_dev_data/` (including `typecraft.db`) and `__pycache__/` are untracked **and un-ignored** — a future `git add -A` would commit a database and byte-code. No `.gitignore` exists. | `git status --short` | TC-001 |
| D-25 | S4 | `ResultsScene._pick_message()` re-opens and re-parses `messages.json` on every scene entry instead of loading it once through a manager. Not on the frame path, so low severity. | `scenes/results.py:40-57` | TC-017 |
| ~~D-26~~ | S4 | ~~Leaderboard interpolated a column name into SQL with an f-string.~~ **CLOSED by TC-012.** The column now comes from `ProgressionService.LEADERBOARD_COLUMNS`, a fixed dict keyed by a UI tab name; an unknown key raises `KeyError`. Covered by a test that passes `'; DROP TABLE profiles; --` as the board name. | `managers/progression.py` | TC-012 ✅ |
| ~~D-28~~ | S4 | ~~No `.gitattributes`, and `core.autocrlf` is enabled.~~ **CLOSED by TC-002.** `.gitattributes` pins `* text=auto eol=lf` and marks binary types; verified to introduce no renormalisation churn. | `git diff --stat` empty after adding it | TC-002 ✅ |
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

- ~~**B-01**~~ **CLEARED by TC-003.** `.venv` exists at the repo root with pygame 2.6.1,
  pytest 8.4.2, pytest-cov 7.1.0, hypothesis 6.163.0, and PyInstaller 6.21.0 on Python 3.12.9.
  Use `.venv\Scripts\python.exe` (or activate it) for every command from here on — the
  MiniConda base interpreter still has none of these.
- **B-02 (decision needed from the user)** **OQ-001** — Backspace correction accounting.
  Blueprint §2.4 implies no retroactive edits; the code comment claims corrections do fix the
  books; the implementation does neither correctly. TC-006 will implement the recommended
  blueprint-literal ledger unless directed otherwise. Non-blocking until TC-006.
- **B-03 (decision, low urgency)** OQ-003 — whether permissively-licensed third-party assets
  may be bundled. Affects TC-017 only.

---

## 6. Files changed

### TC-016 (last task, DONE)

- `typecraft/ui/target_text.py` - **new.** `TargetTextLayout` computed once per lesson entry:
  token-based word wrapping, wrap test before placement, per-character rects, `caret_rect()`
  on the left edge (resting after the final glyph when finished), `bounds()`, `line_count()`,
  and a visible measured space marker.
- `typecraft/scenes/lesson.py` - `TEXT_AREA` constant; layout built in `on_enter`;
  `_render_target_text()` now only recolours and blits, drawing a block behind the current
  character plus the caret.
- `tests/db/test_target_text.py` - **new**, 35 tests.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 634 passing, 1 xfail (D-19 only); app smoke-tested.

### TC-015 (DONE)

- `typecraft/ui/keyboard_renderer.py` - rewritten. Single `ROWS` table of
  `(label, char, width, finger)` describing a 5-row 61-key QWERTY including Space, both Shifts,
  the number row and all punctuation; `SHIFT_PAIRS`; `CHAR_TO_KEY` **derived** from the table;
  `finger_for()`, `shift_side_for()` (opposite hand), `FINGER_LABELS`;
  `highlight_expected()` replacing the just-pressed `highlight()`; `active_keys`;
  `prerender_count` for the performance assertion; a caption naming key, finger and Shift.
- `typecraft/ui/theme.py` - ninth `thumb` colour for the space bar.
- `typecraft/scenes/lesson.py` - `_update_keyboard_hint()` called on entry, after each
  keystroke and after Backspace; keyboard centred using `KeyboardRenderer.size()`.
- `tests/db/test_keyboard.py` - **new**, 94 tests.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 596 passing, 1 xfail (D-19 only); app smoke-tested.

### TC-014 (DONE)

- `typecraft/ui/scroll_panel.py` - **new.** Clipping viewport: wheel (both SDL encodings),
  middle-drag, PgUp/PgDn/Home/End, clamped offset, `screen_rect`/`content_pos` translation,
  `translated()` returning `None` outside the viewport, `clipped()` context manager,
  `render_children()`, and a scrollbar drawn only when scrollable.
- `typecraft/scenes/profile_select.py`, `lesson_select.py`, `teacher_dashboard.py` - layouts moved
  into content space (first row at y=0), input translated before dispatch, rendering clipped.
- `tests/db/test_scrolling.py` - **new**, 19 tests. `tests/db/test_dashboard.py` - click helpers
  corrected to use screen coordinates.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 502 passing, 1 xfail (D-19 only); app smoke-tested.

### TC-013 (DONE)

- `typecraft/managers/progression.py` - `COMPLETED` SQL fragment (one definition of "attempts
  that count"), `student_summary(profile_id)`, `class_summary()`.
- `typecraft/scenes/teacher_dashboard.py` - rewritten: a `COLUMNS` table definition, all nine
  FR-122 fields, a dash for absent averages, and a two-step modal reset confirmation
  (`pending_reset`, `_ask_reset`, `_confirm_reset`, `_cancel_reset`) that refreshes the table
  afterwards and syncs `ctx.active_profile`.
- `tests/db/test_dashboard.py` - **new**, 22 tests.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 480 passing, 1 xfail (D-19 only); app smoke-tested.

### TC-011 + TC-011b (DONE)

- `typecraft/managers/config_manager.py` — safe loader (`_load`/`_sanitise`) with fallback,
  `warnings` list and logging; **atomic** `_write()` (temp file → `fsync` → `os.replace`);
  PBKDF2 `_hash()`, `verify_pin()` with `hmac.compare_digest` and a one-time legacy-hash
  upgrade.
- `typecraft/core/app_context.py` — applies stored volume/mute at startup; exposes `notices`.
- `typecraft/ui/audio_manager.py` — `volume` / `muted` read-only properties.
- `typecraft/scenes/settings.py` — initialises from the running config, persists every change,
  renders startup notices.
- `tests/db/test_settings.py` — **new**, 23 tests. `tests/db/test_config_and_seeding.py` — two
  D-15 markers removed, 5 tests added (hash format, legacy upgrade, malformed hash, atomic
  write, no leftover temp file).
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 458 passing, 1 xfail (D-19 only); `config_manager.py` 97 % covered;
app smoke-tested.

### TC-012 (DONE)

- `typecraft/managers/progression.py` — `LEADERBOARD_COLUMNS` allow-list and
  `leaderboard(board, limit=10)`.
- `typecraft/scenes/leaderboard.py` — `_load_rows()` delegates to the service; the FR-113 tie
  rule is now stated on screen.
- `tests/db/test_leaderboard.py` — **new**, 15 tests.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 428 passing, 3 xfail; app smoke-tested.

### TC-013b (DONE)

- `typecraft/managers/progression.py` — `_award_xp()` split into `_add_xp()` (adds XP only) and
  `_recompute_level()` (returns whether the level moved). `score()` now orders the work: attempt
  XP → streak touch → **streak bonus if this is the first completed lesson of the local calendar
  day** → unlock → recompute level → badges → recompute → one *bounded* extra badge pass when
  the level moved.
- `tests/db/test_progression.py` — 2 xfail markers removed; 6 new tests. Three existing XP
  assertions updated for the newly-awarded streak bonus.
- `tests/db/test_badges.py` — one XP assertion updated likewise.
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 413 passing, 3 xfail; app smoke-tested.

### TC-010 (DONE)

- `typecraft/core/scene.py` — `on_quit_requested()` hook (default no-op).
- `typecraft/core/state_manager.py` — `notify_quit()`.
- `typecraft/core/game.py` — `_request_quit()` calls the scene before stopping the loop and
  logs any failure rather than letting it block exit; `_register_scenes()` extracted to a
  module-level `build_state_manager(ctx)` so a wired manager can be built without a window.
- `typecraft/scenes/lesson.py` — `on_quit_requested()` routing through `_finish()`.
- `tests/conftest.py` — `app_ctx` now wires `ctx.states` via `build_state_manager`.
- `tests/db/test_quit_paths.py` — **new**, 10 tests.
- `TASKS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md` §3/§12/§17.

**Evidence:** 406 passing, 5 xfail; app smoke-tested.

### TC-009 (DONE)

- `typecraft/managers/progression.py` — `CHECKPOINT_INTERVAL_SEC = 10.0`;
  `checkpoint(engine, row_id)` building its row from `engine.result(IN_PROGRESS)` so the
  checkpoint and the final write share one code path; `_insert_attempt()` generalised to
  `_write_attempt(attempt, row_id)` (INSERT, or UPDATE to promote a reserved row);
  `score()` takes an optional `row_id`.
- `typecraft/scenes/lesson.py` — `_attempt_row_id` / `_since_checkpoint` per attempt;
  `_has_started()`, `_checkpoint()`, and `_finish(status)` as the **single exit point** for an
  attempt so Esc, completion and (next) window-close cannot diverge; `update()` checkpoints on
  the timer.
- `tests/db/test_recovery.py` — **new**, 9 tests.
- `TASKS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md` §12/§17.

**Evidence:** 396 passing, 5 xfail; app smoke-tested.

### TC-008b (DONE)

- `typecraft/managers/database.py` — `SCHEMA_VERSION = 2`; `schema_meta` table; `_migrate()`
  (one transaction, additive-only, guarded by `PRAGMA table_info` so it is idempotent);
  `schema_version()`, `_add_column()`, `_set_schema_version()`.
- `typecraft/managers/progression.py` — `_insert_attempt()` writes the three new columns.
- `tests/db/test_schema.py` — D-09 marker removed; 4 new tests (fresh-DB version, a synthesised
  v1 → v2 upgrade preserving every value, idempotency across three reopens, and a keystroke
  round-trip asserting the stored accuracy is reproducible from the stored counters).
- `TASKS.md`, `PROJECT_STATE.md`.

**Evidence:** 387 passing, 5 xfail. `_dev_data/typecraft.db` — the actual inherited artefact —
reports `schema_version 2`, has all three new columns, and still holds its 10 badge rows.

### TC-008 (DONE)

- `typecraft/managers/database.py` — `isolation_level=None`; `transaction()` context manager
  (`BEGIN IMMEDIATE`, commit on clean exit, rollback + re-raise on exception, refuses to nest);
  `execute()` no longer commits; `begin`/`commit`/`rollback` kept but now actually work and are
  guarded by an `_in_txn` flag; `in_transaction` property; `close()` discards an open
  transaction; `PRAGMA synchronous = FULL` and an explicit `PRAGMA journal_mode = DELETE`
  (ADR-012 — deliberately not WAL).
- `typecraft/managers/progression.py` — `score()` wrapped in one transaction; attempt INSERT
  extracted to `_insert_attempt()`; snapshots and restores the Profile fields it mutates so a
  rollback cannot leave the in-memory object holding XP that was never earned.
- `typecraft/scenes/teacher_dashboard.py` — `_reset_progress()` uses `with db.transaction()`
  instead of the ineffective `begin`/`try`/`except`; also zeroes the in-memory profile to match.
- `tests/db/test_transactions.py` — 3 xfail markers removed; 12 new tests for the contract.
- `ARCHITECTURE.md` §8.2 (WAL → rollback journal), §18 (ADR-012 added, ADR-003 accepted),
  §19 (R2 closed); `TASKS.md`; `PROJECT_STATE.md`.

### TC-007 (DONE) — tests only, zero production changes

- `tests/conftest.py` — added the `attempt_factory` fixture, which derives stars and XP
  through the real formulas so a test states a performance rather than hard-coding numbers.
- `tests/db/test_schema.py` — **new**: table set, bootstrap idempotency, reopen-without-loss,
  the attempt-lookup index, composite-key and unique-code enforcement, orphan `in_progress`
  reclassification (and that it leaves `complete`/`incomplete` rows alone), plus the D-09 xfail.
- `tests/db/test_transactions.py` — **new**: three D-04 xfails, including a forced mid-reset
  failure and a forced failure inside `score()`.
- `tests/db/test_progression.py` — **new**: profile seeding, complete vs incomplete
  persistence, exclusion from averages, progress-cache bests, XP accumulation and level
  recompute, participation XP; D-11 and D-31 xfails.
- `tests/db/test_unlocking.py` — **new**: 20 lessons in 5 tiers, chain ordering, unique ids,
  the exact 85.0 boundary, WPM-independence, incomplete attempts never unlocking, idempotency,
  no re-locking, one-step-only advance, tier crossing, final-lesson no-op.
- `tests/db/test_badges.py` — **new**: catalogue sync and non-duplication, all ten criteria
  incl. the 100 %/30 wpm/50 combo boundaries and distinct-lesson counting, award idempotency
  with no double-paid XP, and no badges from incomplete attempts.
- `tests/db/test_config_and_seeding.py` — **new**: first-run seeding, never overwriting an
  edited file, gap-filling, the teacher's file winning, fallback across four kinds of
  corruption without touching their file, PIN set/verify/persist; D-19 and two D-15 xfails.
- `tests/unit/test_streaks.py` — **new**: the full D4 state machine with injected dates.
- `TASKS.md`, `PROJECT_STATE.md`, `REQUIREMENTS.md`.

### TC-006 (DONE)

- `typecraft/engine/typing_engine.py` — `_error_counted` deleted (D-08); the
  `cursor >= len(target)` guard moved to the top of `feed_key()` as an
  `if self.is_finished(): return self._ignored()` (D-29, and it now covers Backspace too, so a
  finished attempt is immutable); `_apply_backspace()` rewritten counter-neutral with a
  `corrections_made` tally (D-07); `metrics()` gained `total_keystrokes`,
  `correct_keystrokes`, `corrections_made`; `result()` passes `corrections_made`.
- `typecraft/engine/input_modes.py` — new `_inert_backspace()` helper returning
  `is_backspace=True`, used by all three modes for a no-op backspace (D-30); module docstring
  rewritten to state the OQ-001 policy, replacing the note that claimed the opposite.
- `typecraft/models/attempt.py` — `AttemptResult.corrections_made`.
- `tests/unit/test_input_modes.py` — two assertions corrected (they pinned the D-30
  mechanism); new `test_a_no_op_backspace_is_still_flagged_as_one` over all three modes.
- `tests/unit/test_typing_engine.py`, `tests/unit/test_invariants.py` — all 10 `xfail`
  markers removed; the D-07 navigation test's target widened from 2 to 3 characters so its
  scenario stays reachable under the new finished-guard.
- `TASKS.md`, `PROJECT_STATE.md`.

### TC-005 (DONE)

- `tests/unit/test_metrics.py` — **new**, 76 tests: accuracy, gross/net WPM, the
  `net = gross × accuracy` identity, star boundaries at 84.99/85/91.99/92/96.99/97, the three
  blueprint XP worked examples, participation XP, the speed-bonus cap, the full 10-level
  table, and the streak-bonus saturation.
- `tests/unit/test_input_modes.py` — **new**, 22 tests: registry, `create_mode` including the
  unknown-key error, backspace permission per mode, each mode's advance/error decisions, and
  a test that `resolve()` never mutates the state it is given.
- `tests/unit/test_typing_engine.py` — **new**, 25 tests (18 pass, 7 strict-xfail): initial
  state, clock-starts-on-first-keystroke, perfect runs in all three modes, deterministic WPM
  via the injected clock, zero-duration safety, combo behaviour, backspace inertness,
  `result()` status inference, and 7 defect reproductions.
- `tests/unit/test_invariants.py` — **new**, 8 tests (5 pass, 3 strict-xfail): 400 randomised
  sequences × 40 keystrokes per mode from a fixed seed, a hypothesis property test with
  shrinking, and the "only typing can produce accuracy" integrity property.
- `typecraft/engine/typing_engine.py` — the single production change: a `clock=time.monotonic`
  constructor parameter, used in place of the three direct `time.monotonic()` calls, so WPM is
  deterministic under test with no sleeping. No behavioural change.
- `REQUIREMENTS.md` — OQ-001 marked RESOLVED with the accounting policy.
- `TASKS.md`, `PROJECT_STATE.md`, `ARCHITECTURE.md` §6.

### TC-004 (DONE)

- `tests/conftest.py` — **new.** 6 fixtures: `writable_dir`, `seeded_dir`, `db`, `display`,
  `app_ctx`, `profile`. Sets `SDL_VIDEODRIVER`/`SDL_AUDIODRIVER=dummy` at import time.
- `tests/unit/test_imports.py` — **new**, 141 tests (parametrised per module): every module
  imports from the repo root, the six documented subpackages exist, no `TypeCraft.` prefix
  has crept back, the entry point is reachable.
- `tests/unit/test_layering.py` — **new**: dependency direction per ARCHITECTURE.md §2,
  `engine`/`managers`/`models` stay pygame-free, `sqlite3` only in `managers/database.py`,
  no scene imports another scene, `__file__` used only in `core/paths.py`,
  `engine/metrics.py` stays pure.
- `tests/unit/test_data_isolation.py` — **new**: proves the fixtures cannot reach real data.
- `tests/unit/test_logging_setup.py` — **new**: log file location, handler idempotency,
  child-logger naming, survival of an unwritable path, no console handler when frozen.
- `typecraft/core/paths.py` — added `log_path()`.
- `typecraft/core/logging_setup.py` — **new**: `configure_logging()`, `get_logger()`,
  `reset_logging()`.
- `typecraft/main.py` — 2 lines: configure logging and log startup, so the facility is wired
  rather than dead code.
- `tests/.gitkeep` — removed (real tests now occupy the directory).
- `ARCHITECTURE.md` §5, §11, §15, §17, §19; `TASKS.md`; `PROJECT_STATE.md`.

### TC-003 (DONE)

- `requirements.txt` — was 0 bytes; now the single runtime pin `pygame>=2.5.2,<3.0`.
- `requirements-dev.txt` — **new**: pytest, pytest-cov, hypothesis, PyInstaller 6.x.
- `pyproject.toml` — **new**: `requires-python = ">=3.10"`, pytest config
  (`testpaths=["tests"]`, `-q --strict-markers`, a `slow` marker), coverage config.
- `README.md` — rewritten: requirements, venv setup, run, test, build, repo map, the two
  invariants that matter (all paths via `core/paths.py`; only `database.py` imports
  `sqlite3`), and an explicit "not releasable yet" banner. Full DOC-001 treatment is TC-021.
- `tests/.gitkeep` — **new**, so the `testpaths` setting resolves before TC-004 lands.
- `.venv/` — created, git-ignored, not committed.
- `TASKS.md`, `PROJECT_STATE.md`.

### TC-002 (DONE)

- `typecraft/` — **new package.** All 45 source files plus `data/` moved in via `git mv`
  (recorded as pure renames, zero content churn in the move commit).
- `typecraft/assets/{images,fonts,sounds}/.gitkeep` — **new**, empty; populated by TC-017.
- 88 import statements rewritten `TypeCraft.` → `typecraft.` across 27 files. The only
  surviving bare `TypeCraft` strings are the window caption (`core/game.py:21`), the menu
  title (`scenes/main_menu.py:40`), and two prose lines — all correct.
- `typecraft/core/paths.py` — `_project_root()` split into `_package_root()` (anchors
  `resource_path`, = `typecraft/`) and `_repo_root()` (anchors the dev writable dir, =
  repo root). This is the one behavioural edit in the task, and it is what keeps
  `_dev_data/` outside the package. Docstrings updated.
- `main.py` — **new** repo-root launcher (`from typecraft.main import main`).
- `typecraft/__main__.py` — **new**, makes `python -m typecraft` equivalent.
- `.gitattributes` — **new**, pins LF (D-28).
- `ARCHITECTURE.md` §1.1/§1.2/§10/§16/§18/§19, `TASKS.md`, `PROJECT_STATE.md`.

### TC-001 (DONE)

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

### TC-002 (2026-07-29)

| Command | Result |
|---|---|
| `git mv` × 9 (7 packages + `__init__.py` + `main.py`) | **PASS** — all 45 files staged as `R` (pure renames), no content change |
| `python <rewrite script>` | **PASS** — 88 import statements rewritten across 27 files; regex limited to `from\|import TypeCraft.` so prose and UI strings were untouched |
| `grep -rnE '\b(from\|import)\s+TypeCraft\.' typecraft/` | **PASS** — `NONE` |
| `grep -rn TypeCraft typecraft/ --include=*.py` | 4 hits, all intentional: window caption, menu title, 2 prose lines |
| `python -m compileall -q typecraft main.py` | **PASS** — exit 0 |
| `resource_path()` probe (4 × `data/*.json`, `assets/images`) | **PASS** — all resolve, all exist, anchored at `…\TypeCraft\typecraft` |
| `writable_data_dir()` probe | **PASS** — `…\TypeCraft\_dev_data`, exists, `typecraft.db` present (dev DB **not** orphaned) |
| metrics smoke (`stars_for(93)`, `level_for(150)`, `xp_for(88,18,1,1)`) | `2`, `3`, `26` — the XP value matches blueprint §2.4's worked example #1 (Tier 1 @ 88 %/18 wpm → 1★/26 XP). Incidental, not a substitute for TC-005 |
| `python main.py` | Resolves `main.py` → `typecraft.main` → `typecraft.core.game`, then fails at `import pygame`. Before TC-002 this failed immediately with `No module named 'TypeCraft'` |
| `python -m typecraft` | Identical behaviour — same pygame boundary |
| `git diff --stat` after `.gitattributes` | **PASS** — no renormalisation churn |
| `git status --short` after commits | **PASS** — working tree clean |

**Deferred (not skipped):** "`python main.py` reaches the Main Menu" — impossible until
pygame exists. Carried into TC-003's check list. Everything up to the pygame import boundary
is proven; nothing beyond it has been executed, and TC-002 is **not** evidence that the
application runs. **→ Closed in TC-003 below.**

### TC-003 (2026-07-29)

All commands run with `.venv\Scripts\python.exe` from the repo root.

| Command | Result |
|---|---|
| `python -m venv .venv` | **PASS** |
| `pip install -r requirements.txt -r requirements-dev.txt` | **PASS** — pygame 2.6.1, pytest 8.4.2, pytest-cov 7.1.0, hypothesis 6.163.0, pyinstaller 6.21.0 (+ transitive) |
| `python --version` | `Python 3.12.9` |
| `python -c "import pygame; print(pygame.version.ver)"` | `2.6.1` |
| `python -m pytest --version` | `pytest 8.4.2` |
| `python -m PyInstaller --version` | `6.21.0`, with a benign warning that the venv's base interpreter is MiniConda — re-check at TC-020 |
| `python -m pytest` | Runs; `no tests ran in 1.72s` (expected — `tests/` is empty until TC-004) |
| headless probe (`SDL_VIDEODRIVER=dummy`, writable dir → temp) | **PASS** — see §3. Reached `MainMenuScene`, 3 frames rendered, 5 profile-independent scenes entered + rendered, 20 lessons / 5 tiers loaded, 5 writable files seeded, `run()` exited cleanly on QUIT |
| `SDL_VIDEODRIVER=dummy timeout 6 python main.py` | exit 124 (**still running after 6 s = healthy**), no output on stderr |
| `SDL_VIDEODRIVER=dummy timeout 6 python -m typecraft` | exit 124, identical |

**The TC-002 deferral is closed: the inherited application starts and runs.** This is a
liveness result only — no gameplay path and no metric has been exercised, and the 25 open
defects are all still open.

### TC-004 (2026-07-29)

| Command | Result |
|---|---|
| `python -m pytest` | **154 passed in 2.94 s**, 0 failed, 0 errors |
| `python -m pytest --cov --cov-report=term-missing` | **PASS** — coverage tooling works; 34 % overall (1 504 statements, 988 missed) |
| `python -m pytest --cov=typecraft.engine --cov=typecraft.managers` | 29 % across those two packages. Worst: `typing_engine.py` 15 %, `badge_manager.py` 18 %, `metrics.py` 21 %, `streak_manager.py` 21 %. Best: `database.py` 82 % (exercised by the `db` fixture) |
| `ls -la _dev_data/` before and after a full suite run | **PASS — isolation proven.** All five files kept their original 02:04:35 mtimes and **no `typecraft.log` was created**. Nothing in `_dev_data/` was read or written by the suite |
| `SDL_VIDEODRIVER=dummy timeout 5 python main.py` | Ran; wrote `_dev_data/typecraft.log` containing `INFO typecraft.main: TypeCraft starting`. Confirms the logging wiring works end to end **and** that the log only appears when the app actually runs |

Notable: `test_only_paths_module_derives_locations_from_dunder_file` and
`test_metrics_is_pure` both passed on the inherited code — NFR-011 and FR-052 were already
being honoured, which is why `core/paths.py` needed no repair.

### TC-005 (2026-07-29)

| Command | Result |
|---|---|
| `pytest tests/unit/test_metrics.py` | 76 passed. **All formulas in `engine/metrics.py` are correct as inherited** — including all three blueprint worked examples and the whole 10-level table |
| `pytest tests/unit/test_input_modes.py` | 22 passed. **The three strategies are correct as inherited**; the defects are all in `feed_key()`'s bookkeeping, not in the mode decisions |
| `pytest tests/unit/test_typing_engine.py -rxX` | 18 passed, **7 xfail** |
| `pytest tests/unit/test_invariants.py -rxX` | 5 passed, **3 xfail** |
| `pytest -q -rxX` (full suite) | **281 tests: 271 passed, 10 xfail, 0 unexpected failures** |
| `pytest --cov=typecraft.engine --cov=typecraft.managers` | `metrics.py` **100 %**, `typing_engine.py` **99 %**, `input_modes.py` **94 %**; combined engine+managers 58 % (up from 29 %) |

**One assumption of mine was wrong, and the tests caught it.** I had marked the randomised
ledger check as xfail for all three modes. `strict=True` turned the unexpected passes into
failures, which forced the correction: only **D-08** breaks FR-043's equation, and only in
`lock_on_error`. D-07 and D-30 keep the equation balanced while making the values wrong
(D-07 moves a count from `errors` to `correct`; D-30 increments `total` and `correct`
together). Consequence for TC-006: an invariant check alone cannot prove the fix — the exact
expected counter values must be asserted, which is what `test_typing_engine.py` now does.

**The 10 strict-xfail tests — the exact TC-006 acceptance list:**

| Test id | Defect |
|---|---|
| `test_typing_engine.py::test_D08_repeated_wrong_key_keeps_the_ledger_consistent` | D-08 |
| `test_typing_engine.py::test_D08_every_wrong_keystroke_counts_as_a_mistake` | D-08 |
| `test_typing_engine.py::test_D07_corrected_error_still_counts_against_accuracy` | D-07 |
| `test_typing_engine.py::test_D07_backspace_alone_cannot_manufacture_accuracy` | D-07 |
| `test_typing_engine.py::test_D07_navigating_back_over_a_correct_character_does_not_inflate_accuracy` | D-07 |
| `test_typing_engine.py::test_D30_backspace_at_the_start_cannot_be_farmed_for_accuracy` | D-30 |
| `test_typing_engine.py::test_D29_input_after_completion_is_ignored` | D-29 |
| `test_invariants.py::test_ledger_holds_over_randomised_sequences[lock_on_error]` | D-08 |
| `test_invariants.py::test_only_typing_can_produce_accuracy` | D-30 |
| `test_invariants.py::test_ledger_holds_under_hypothesis` | D-08 |

Also corrected during this task: one of my own test expectations was wrong, not the code —
`xp_for(50.0, …)` returns 2, not 3, because Python's `round(2.5)` is banker's rounding. Pinned
with a comment so it is a decision on record.

### TC-006 (2026-07-29)

| Command | Result |
|---|---|
| `pytest -q -rxX` | **284 passed, 0 failed, 0 xfail.** All 10 strict-xfail markers removed |
| `pytest --cov=typecraft.engine` | `typing_engine.py` **100 %**, `metrics.py` **100 %**, `input_modes.py` 96 %, `engine/` overall **99 %** |
| `SDL_VIDEODRIVER=dummy timeout 5 python main.py` | Ran clean; `LessonScene` drives `feed_key()`, so this confirms the changed engine still works in the real app |
| Direct exploit probe (outside the test harness) | All four defects dead — table below |

| Scenario | Before TC-006 | After TC-006 |
|---|---|---|
| 20× Backspace, nothing typed (D-30) | total 20, correct 20, combo 20, **100 %** | total 0, correct 0, combo 0, **0 %** |
| wrong key + Backspace (D-07) | total 1, correct 1, errors 0, **100 %** | total 1, correct 0, errors 1, **0 %** |
| wrong + Backspace + right (D-07) | **100 %**, 0 mistakes | **50 %**, 1 mistake, 1 correction |
| 4 wrong then right (D-08) | total 5, errors 1, **sum 2 ≠ 5** | total 5, errors 4, **sum 5 = 5** |
| key after completion (D-29) | `IndexError` | ignored, counters unchanged |

**Two TC-005 assertions were corrected, not weakened.**
`test_free_advance_ignores_backspace` and `test_backspace_at_the_start_of_the_text_is_a_no_op`
asserted `is_backspace is False` for a no-op backspace — which *is* the D-30 mechanism, so
they pinned the bug rather than the requirement. Replaced with
`test_a_no_op_backspace_is_still_flagged_as_one`, parametrised over all three modes, encoding
the rule: "the backspace did nothing" must never be expressed as "this was not a backspace".

**One test premise was wrong.** `test_D07_navigating_back_over_a_correct_character…` used a
2-character target, so its second keystroke completed the text and the new finished-guard
correctly ignored the Backspaces. The target was widened to 3 characters; the assertions are
unchanged and now also check `corrections_made`.

### TC-008 (2026-07-29)

| Command | Result |
|---|---|
| `pytest -q -rxX` | **382 passed, 6 xfail, 0 unexpected failures** in 27 s. All three D-04 markers removed |
| `pytest --cov=typecraft.engine --cov=typecraft.managers` | 97 % overall; `database.py` 93 %, `progression.py` 94 % |
| `SDL_VIDEODRIVER=dummy timeout 5 python main.py` | Ran clean — every write in the app now goes through the changed `Database` |
| `ls _dev_data/` after a real run | No `typecraft.db-wal` or `-shm` file, confirming ADR-012's journal choice |

**ADR-012 — I corrected one of my own specifications.** ARCHITECTURE §8.2 originally called
for `journal_mode = WAL`. That is wrong for this deployment: in WAL mode recently-committed
rows can sit in `typecraft.db-wal` rather than the main file, so a teacher copying
`typecraft.db` to a USB stick after a crash would **silently lose them** — breaking DR-014's
one-file backup story and the blueprint's own instruction to teachers. Implemented with the
default rollback journal (deletes itself on commit, so the `.db` is always a complete
snapshot) plus `synchronous = FULL` for per-commit fsync. Two tests assert the journal mode is
not WAL and that `synchronous` is FULL.

**Extra fix, in scope and worth noting.** `_award_xp()` and `BadgeManager.award()` mutate the
**live** Profile object, not just the database row. Without intervention a rolled-back
`score()` left the in-memory profile holding XP that was never earned, and the next successful
`save()` would have written it to disk — a rollback that leaks. `score()` now snapshots and
restores those fields, and `_reset_progress()` zeroes the in-memory profile to match the row it
wrote. Covered by `test_a_rolled_back_score_leaves_the_in_memory_profile_unchanged`.

### TC-007 (2026-07-29)

| Command | Result |
|---|---|
| `pytest -q -rxX` | **367 passed, 9 xfail, 0 unexpected failures** in 24 s |
| `pytest --cov=typecraft.engine --cov=typecraft.managers` | **97 %** — AC-02's ≥ 85 % bar met. 100 % for `metrics`, `typing_engine`, `lesson_manager`, `config_manager`, `streak_manager`; 98 % `badge_manager`; 97 % `database`; 93 % `progression`; 77 % `profile_manager` |

**Zero production files were changed.** This was pure characterisation.

**Confirmed correct as inherited** — worth recording, because it narrows where the remaining
risk is: schema bootstrap idempotency and reopen-without-loss; orphan `in_progress` recovery
(and that it leaves other statuses alone); first-lesson-only unlock on profile creation; the
85.0 gate exact at 84.99 / 85.0 / 85.01 and independent of WPM; incomplete attempts excluded
from unlocks, XP, badges, streaks and averages; progress-cache bests per lesson; badge
idempotency with no double-paid XP; all ten badge criteria including distinct-lesson counting;
the entire streak state machine including the clock-rollback guard, month/year/leap-day
boundaries and the high-water mark; seeding never overwriting an edited file; and the
`lessons.json` fallback surviving four kinds of corruption without touching the teacher's file.

**The 9 strict-xfail reproductions — the acceptance lists for the next tasks:**

| Test id | Defect | Fixed by |
|---|---|---|
| `test_transactions.py::test_rollback_undoes_every_statement_since_begin` | D-04 | TC-008 |
| `test_transactions.py::test_a_failure_midway_through_a_reset_changes_nothing` | D-04 | TC-008 |
| `test_transactions.py::test_a_failure_while_scoring_leaves_no_partial_attempt` | D-04 | TC-008 |
| `test_schema.py::test_attempts_table_stores_the_keystroke_counts` | D-09 | TC-008b |
| `test_progression.py::test_badge_xp_raises_the_level_in_the_same_attempt` | D-11 | TC-013b |
| `test_progression.py::test_first_completed_lesson_of_the_day_awards_the_streak_bonus` | D-31 | TC-013b |
| `test_config_and_seeding.py::test_the_pin_hash_is_salted` | D-15 | TC-011b |
| `test_config_and_seeding.py::test_the_pin_cannot_be_recovered_by_brute_force` | D-15 | TC-011b |
| `test_config_and_seeding.py::test_a_broken_lessons_file_is_reported` | D-19 | TC-023 |

**One of my test premises was wrong again, not the code.**
`test_completing_the_final_lesson_…` asserted that only one lesson would ever be unlocked.
In fact `_update_progress_cache()` inserts an `is_unlocked=1` row for the lesson just
completed, which is sound — you cannot complete a locked lesson through the UI. Assertion
corrected to check that the unlocked set is exactly {lesson 1, the final lesson} and is a
subset of the real lesson ids.

**Scope note on the leaderboard.** TC-007's brief listed "leaderboard exclusion rules", but
the query lives in `scenes/leaderboard.py`. Duplicating that SQL in a test here would have let
the scene stay broken while the test passed, so this task asserts only the root cause (a fresh
profile gets a zero-valued `lesson_progress` row) and the query test moves to **TC-012**,
where its `tests/db/test_leaderboard.py` was already assigned.

**New product question raised by TC-006, deliberately not decided (see OQ-006).** Because
completion fires the instant the cursor reaches the end, a wrong *final* character in
`BackspaceMode` can never be corrected — FR-033 promises revisiting, FR-047 ends the attempt.
Not a regression (the inherited `LessonScene` already transitioned on the finishing keystroke)
and out of scope for an engine-accounting task, so it is logged for the Phase 4 UI work.

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

**Environment note for the next session:** use the repo-root virtual environment —
`.venv\Scripts\python.exe` on Windows, or activate it first. The MiniConda base interpreter
has no pygame, pytest, or PyInstaller, so commands run outside the venv will fail
misleadingly. `.venv/` is git-ignored; recreate it with the two commands in `README.md` if it
is missing.

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
