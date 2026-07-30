# TypeCraft — Requirements Specification

**Status:** Baseline v1.0 — derived 2026-07-29 from `TypeCraft_Master_Blueprint.md`,
`TypeCraft Khidmat Proposal.pdf`, the existing source tree, `data/*.json`, and the
schema of `_dev_data/typecraft.db`.

**Authority rule:** where the blueprint and the code disagree, this document records the
requirement and `PROJECT_STATE.md` records the defect. The implementation plus the
automated test suite become the executable source of truth once Phase 2 completes.

---

## 1. Purpose and problem statement

Students at The Bridge School have limited keyboard literacy and the school's computers
are low-end Windows machines with no reliable internet. Commercial typing tutors are
online, subscription-based, or too heavy to run. TypeCraft is a fully offline, gamified
desktop typing tutor that runs from a single copied folder, stores all progress locally,
and gives teachers per-student visibility without any cloud service.

## 2. Target users and roles

| Role | Description | Needs |
|---|---|---|
| Student (primary, ~ages 8–14) | Selects own profile, plays lessons | Large readable text, immediate feedback, stars/XP/badges, no login |
| Teacher / classroom facilitator | Runs the lab, monitors progress | PIN-gated dashboard, per-student stats, reset a student, edit lesson text in Notepad |
| Deployer / IT volunteer | Copies the build to machines | Single folder, no Python install, backup = copy one file |

Roles are **not** authenticated user accounts. Student profiles are unauthenticated
selections; only the teacher area is PIN-gated.

---

## 3. Functional requirements

### 3.1 Application shell and navigation

- **FR-001** The application launches to a Main Menu offering: Play, Leaderboard, Settings, Teacher Dashboard.
- **FR-002** Exactly one Scene is active at a time; transitions occur through a single state manager.
- **FR-003** Scene flow: Main Menu → Profile Select → Lesson Select → Mode Select → Lesson → Results → (Retry | Lesson Select | Leaderboard).
- **FR-004** Every scene except Main Menu provides a visible way back to its logical parent.
- **FR-005** *(revised 2026-07-31, at the user's request — the original fixed the window at
  1280×720 and §11 listed resizable/fullscreen as out of scope.)* The application draws into a
  fixed **1280×720 design canvas**; all layout is authored in those coordinates and
  `pygame.SCALED` maps the canvas to the real window, translating mouse input back. The window
  is titled "TypeCraft", is **resizable** (drag or maximise), and can be toggled fullscreen with
  **F11** or **Alt+Enter** or started fullscreen with `--fullscreen`. Scaling preserves aspect
  ratio, so no control is ever distorted or displaced.
  *Amended again 2026-07-31:* the window **opens at the design size** rather than pre-sized to
  the desktop. The code that resized the OS window used pygame's private `_sdl2.video.Window`,
  whose finalizer destroyed the display and crashed the application (defect D-33); pygame offers
  no safe public equivalent. Maximise or fullscreen achieves the same result.
- **FR-006** The loop is a fixed Event → Update → Render cycle targeting 30 FPS.

### 3.2 Profiles

- **FR-010** A student profile can be created with a display name and is assigned one of the bundled avatar keys.
- **FR-011** A profile stores: name, avatar key, total XP, level (1–10), current streak, longest streak, last active date, created timestamp.
- **FR-012** Profiles persist across application restarts.
- **FR-013** Profile Select lists all existing profiles and allows selecting one as the active profile.
- **FR-014** Profile Select remains usable with at least 40 profiles via scrolling or pagination; no profile card may render off-screen or overlap another.
- **FR-015** Creating a profile immediately unlocks exactly one lesson: the first lesson in tier/order sequence.
- **FR-016** A blank or whitespace-only profile name is rejected without creating a row.

### 3.3 Lessons and content

- **FR-020** Lesson content is loaded from `lessons.json`, which is teacher-editable in a plain text editor.
- **FR-021** At least 20 lessons exist, grouped into exactly 5 progressive tiers.
- **FR-022** Each lesson declares: stable `id`, `order`, `title`, `finger_focus`, `default_mode`, `target_wpm`, `lines`.
- **FR-023** The loader validates `schema_version`; a mismatched, malformed, or missing file falls back to the bundled default.
- **FR-024** When a fallback occurs, a teacher-visible warning is surfaced in the application **and** a diagnostic is written to a log file. Silent fallback is a defect.
- **FR-025** A lesson's target text is the lesson's `lines` joined with a single space; the student never presses Enter mid-lesson.
- **FR-026** Lesson Select shows every lesson grouped by tier, with lock state, title, and best-star badge, and no card may be clipped by the window edge.
- **FR-027** A locked lesson cannot be started.

### 3.4 Typing modes

- **FR-030** Three modes are selectable before every lesson: `lock_on_error`, `backspace`, `free_advance`.
- **FR-031** Mode Select pre-highlights the lesson's `default_mode`; the student may override it.
- **FR-032** `LockOnErrorMode`: a wrong key does not advance the cursor; the expected key must be typed; Backspace is inert.
- **FR-033** `BackspaceMode`: correct and incorrect keys both advance; Backspace moves the cursor back one position and clears that position's status so it can be retyped.
- **FR-034** `FreeAdvanceMode`: every printable keystroke advances; errors stay uncorrected; Backspace is inert.
- **FR-035** `TypingEngine` contains no mode-specific branching; behaviour is delegated to an `InputMode` strategy object.
- **FR-036** Unknown mode keys raise a clear application error rather than falling back silently.

### 3.5 Typing engine and keystroke accounting

- **FR-040** The engine tracks: cursor index, per-character status (pending/correct/error), `total_keystrokes`, `errors`, `correct_keystrokes`, `combo`, `max_combo`, start time, end time.
- **FR-041** The timing clock starts on the first character-producing keystroke, not on scene entry.
- **FR-042** Backspace and modifier keys are never counted in `total_keystrokes`.
- **FR-043** **Invariant:** `correct_keystrokes + errors == total_keystrokes` at every point in an attempt, in all three modes, including after repeated wrong keys at one position and after Backspace corrections.
- **FR-044** **Invariant:** `0 <= accuracy <= 100` always, including zero-keystroke and zero-duration attempts.
- **FR-045** **Invariant:** `correct_keystrokes <= total_keystrokes` and no counter is ever negative.
- **FR-046** A Backspace correction in `BackspaceMode` never credits a keystroke that was not pressed. See **OQ-001** for the correction-accounting policy.
- **FR-047** The engine reports finished when the cursor reaches the end of the target text; further input is ignored.
- **FR-048** `combo` resets to 0 on any error keystroke and is not restored by a later correction; `max_combo` is the high-water mark.

### 3.6 Metrics

- **FR-050** Displayed and/or stored metrics: net WPM, gross WPM, accuracy %, mistake count, correct keystrokes, total keystrokes, current combo, max combo, elapsed/completion time, lesson completion state.
- **FR-051** Formulas (one word = 5 characters, `T` = minutes from first keystroke):
  `accuracy = correct/total*100`; `gross_wpm = (total/5)/T`; `net_wpm = (correct/5)/T`; both WPM floored at 0.
- **FR-052** All formulas live in pure functions in one module with no I/O and no state.
- **FR-053** `T == 0` or `total == 0` yields 0 for the affected metric, never an exception or infinity.
- **FR-054** Stars: `<85 → 0`, `85–91.99 → 1`, `92–96.99 → 2`, `>=97 → 3`.
- **FR-055** XP: if accuracy < 85, `xp = round(5*accuracy/100)`; else `xp = round((20 + min(net_wpm,40)*0.5) * (accuracy/100) * star_mult * tier_mult)` with `star_mult = {1:1.0, 2:1.3, 3:1.6}` and `tier_mult = 1.0 + 0.1*(tier-1)`.
- **FR-056** Levels: `xp_to_reach(L) = 25*(L-1)*L`, `level = max L with xp_to_reach(L) <= total_xp`, capped at 10.
- **FR-057** Daily streak bonus XP: `5 * min(current_streak, 5)`, awarded once on the first completed lesson of a local calendar day.
- **FR-058** The HUD shows live net WPM, accuracy, combo, mistakes, and elapsed time during a lesson.

### 3.7 Progression and unlocking

- **FR-060** Lessons unlock strictly sequentially in tier/order sequence.
- **FR-061** A **completed** attempt with accuracy >= 85.0 % unlocks the next lesson. 84.99 % does not.
- **FR-062** WPM never gates unlocking.
- **FR-063** Retries are unlimited and never lock a previously unlocked lesson.
- **FR-064** Only attempts with status `complete` affect unlocks, XP, badges, streaks, averages, and leaderboards.
- **FR-065** `lesson_progress` caches per-(profile, lesson) best net WPM, best accuracy, best stars, and completion count, updated on every completed attempt.
- **FR-066** Unlocking the final lesson's successor is a no-op, not an error.

### 3.8 Incomplete attempts and crash recovery

- **FR-070** Pressing Escape after at least one keystroke, before completion, persists an attempt with status `incomplete`.
- **FR-071** Closing the window while a lesson is active persists an `incomplete` attempt when the process can still write.
- **FR-072** Escape before any keystroke persists nothing.
- **FR-073** While a lesson is active, the engine's state is checkpointed to a row with status `in_progress` on a time or keystroke-count interval, never on every keystroke.
- **FR-074** On startup, every row with status `in_progress` is reclassified to `incomplete` before any read of aggregate data.
- **FR-075** `incomplete` and `in_progress` rows are excluded from every average, leaderboard, unlock check, badge predicate, and dashboard statistic.
- **FR-076** An `incomplete` attempt awards 0 stars and 0 XP and does not touch streaks or badges.

### 3.9 Gamification

- **FR-080** Ten badges exist with the codes, names, descriptions, and XP bonuses defined in `badges.json`.
- **FR-081** Badge criteria are evaluated after every completed attempt and after XP/level/streak updates for that attempt.
- **FR-082** A badge is awarded at most once per profile; re-evaluation is idempotent.
- **FR-083** A badge's `xp_bonus` is added to total XP and the level is recomputed after badge XP is applied.
- **FR-084** Zero to three stars are recorded per completed attempt and the best per lesson is cached.
- **FR-085** The Results screen shows a randomly chosen child-appropriate message from the band matching the attempt's accuracy (`low` <85, `mid` 85–91.99, `high` 92–99.99, `perfect` 100).
- **FR-086** Streaks: no prior activity → 1; same local calendar day → unchanged; next day → +1; gap > 1 day → 1; `today` earlier than `last_active_date` → unchanged (clock-rollback guard).
- **FR-087** `longest_streak` is the maximum `current_streak` ever reached.

### 3.10 Visual keyboard

- **FR-090** An on-screen QWERTY keyboard is displayed during a lesson.
- **FR-091** Keys are colour-coded by the eight touch-typing fingers.
- **FR-092** The key required for the **next expected character** is highlighted distinctly.
- **FR-093** The finger that should press the next expected character is explicitly indicated (labelled or visually called out, not colour alone).
- **FR-094** The keyboard renders every character class appearing in bundled lesson content: lowercase letters, digits, Space, both Shift keys, and the punctuation `, . ? ; ' -` and any other character present in `lessons.json`.
- **FR-095** When the next expected character requires Shift, the correct Shift key is highlighted together with the base key.
- **FR-096** The keyboard base layer is rendered once per lesson entry, not per frame.

### 3.11 Lesson text display

- **FR-100** Correct characters render green, incorrect red, pending neutral.
- **FR-101** The cursor position is unambiguously marked.
- **FR-102** Target text wraps at word boundaries within the available width and is never clipped by the window edge.
- **FR-103** Space characters are visibly represented in the target text.
- **FR-104** Text sizing and contrast are legible for children at 1280×720 (body text >= 24 px, target text >= 32 px).

### 3.12 Leaderboard

- **FR-110** A fully offline classroom leaderboard is available from the Main Menu.
- **FR-111** Two separate rankings are shown: best net WPM and best accuracy.
- **FR-112** Only completed attempts contribute; a profile with zero completed attempts must not appear as a scored entry.
- **FR-113** Ties are broken deterministically and the rule is documented on screen or in the docs (rule: higher score, then earlier `created_at`, then profile id ascending).
- **FR-114** With no qualifying data the board shows an explicit empty-state message.

### 3.13 Teacher dashboard

- **FR-120** The dashboard is PIN-gated once a PIN has been configured; with no PIN configured it opens directly and prompts the teacher to set one.
- **FR-121** An incorrect PIN denies access and shows an error; the entry field is cleared.
- **FR-122** Per student the dashboard shows: name, level, total XP, average net WPM, average accuracy, lessons completed (distinct lessons with >=1 completed attempt), badge count, current streak, longest streak.
- **FR-123** Averages are computed over completed attempts only and display an explicit placeholder when there are none.
- **FR-124** The dashboard supports at least 40 profiles via scrolling or pagination.
- **FR-125** "Reset progress" for one student requires an explicit confirmation step before any write.
- **FR-126** Reset is atomic: attempts, progress, badges, XP, level, and streak data are removed and the first lesson re-unlocked in a single transaction; a failure mid-way leaves the database exactly as before.
- **FR-127** Reset preserves the profile row identity (id, name, avatar, created_at).

### 3.14 Settings

- **FR-130** Volume and mute state are read from `settings.json` at startup and applied to the audio subsystem.
- **FR-131** The Settings screen displays the currently persisted volume and mute values on entry.
- **FR-132** Changing volume or mute writes to `settings.json` and survives a restart.
- **FR-133** A 4-digit teacher PIN can be set; only a hash is stored. Non-4-digit input is rejected with a message.
- **FR-134** A missing, malformed, or partially corrupt `settings.json` falls back to bundled defaults, surfaces a visible warning, and logs a diagnostic; it never crashes startup.
- **FR-135** Settings writes are atomic (temp file + replace) so a power loss cannot leave a truncated `settings.json`.

---

## 4. Non-functional requirements

- **NFR-001** Python >= 3.10; the codebase uses no syntax newer than 3.10.
- **NFR-002** Pygame 2.x is the only required third-party runtime dependency.
- **NFR-003** Persistence uses the standard library `sqlite3` only.
- **NFR-004** The application is fully offline: no sockets, HTTP, browser, web server, or external database. No network call exists in the source.
- **NFR-005** Targets Windows 10 and Windows 11, x64.
- **NFR-006** The application sustains >= 30 FPS on a 4th-generation Intel CPU with integrated graphics and 4 GB RAM, in the Lesson scene with the keyboard and HUD visible.
- **NFR-007** No file I/O, database I/O, font rasterisation, image loading, or image scaling occurs inside the per-frame render path.
- **NFR-008** Rendered text surfaces, loaded images, fonts, and the keyboard base layer are cached and reused.
- **NFR-009** Cold start to interactive Main Menu is <= 5 s on target hardware.
- **NFR-010** Total distributed folder size <= 150 MB.
- **NFR-011** Every filesystem path is derived from `core/paths.py`; no module builds an ad hoc data path or relative `open()`.
- **NFR-012** All SQL uses parameter binding; no user or profile data is string-interpolated into SQL.
- **NFR-013** `except Exception` is used only where the exception is re-raised after rollback or converted into an explicit application error with a logged diagnostic.
- **NFR-014** Text-cache growth is bounded across a long classroom session (cleared or capped on scene exit).

## 5. Data and persistence requirements

- **DR-001** Student data lives in one SQLite file `typecraft.db` in the writable data directory.
- **DR-002** Tables: `profiles`, `lesson_attempts`, `lesson_progress`, `badges`, `profile_badges`, with the columns in ARCHITECTURE.md §8.
- **DR-003** `lesson_attempts` stores `total_keystrokes` and `correct_keystrokes` in addition to `errors` (required by FR-050; **absent in the current schema**).
- **DR-004** `lesson_attempts.status` ∈ {`in_progress`, `complete`, `incomplete`}.
- **DR-005** `lesson_id` is a logical string key into `lessons.json`, validated at runtime against the loaded lesson set, not a SQL foreign key.
- **DR-006** Dates are ISO-8601 local-time text: `YYYY-MM-DD` for `last_active_date`, `YYYY-MM-DDTHH:MM:SS` elsewhere.
- **DR-007** Indexes exist on `lesson_attempts(profile_id, lesson_id, status)` and the `lesson_progress(profile_id, lesson_id)` composite key.
- **DR-008** Schema creation is idempotent; opening an existing database never destroys data.
- **DR-009** Schema changes are applied by versioned, additive, idempotent migrations. A newer build opening an older database upgrades it in place without data loss.
- **DR-010** Multi-statement mutations (score-an-attempt, reset-a-student) execute in one explicit transaction with rollback on failure.
- **DR-011** Writable data directory contents: `typecraft.db`, `lessons.json`, `badges.json`, `messages.json`, `settings.json`, `typecraft.log`.
- **DR-012** First launch seeds an editable JSON file **only** when it does not already exist. Existing teacher-edited files are never overwritten.
- **DR-013** Student data and edited JSON survive replacing the bundled read-only application files (an "update").
- **DR-014** A single-file backup story: copying `typecraft.db` preserves all student progress; dropping it back restores it.

## 6. Security requirements

- **SR-001** The teacher PIN is stored only as a hash; the plaintext PIN never appears in `settings.json`, logs, or the database.
- **SR-002** PIN hashing uses a salted, iterated KDF (`hashlib.pbkdf2_hmac`, >= 100 000 iterations, per-install random salt). A bare unsalted SHA-256 of a 4-digit PIN is trivially reversible and is a defect.
- **SR-003** PIN verification is constant-time (`hmac.compare_digest`).
- **SR-004** Teacher-only actions (view dashboard, reset progress) are reachable only after successful PIN verification when a PIN is configured.
- **SR-005** No secret, credential, or token is embedded in the source or the build.
- **SR-006** All SQL is parameterised (see NFR-012). Any dynamic identifier (e.g. a sort column) is chosen from a fixed server-side allow-list, never taken from input.
- **SR-007** Malformed teacher-edited JSON cannot execute code or crash the app; it is parsed with `json` only and validated before use.

## 7. Performance requirements

- **PR-001** Steady-state frame time in the Lesson scene <= 33.3 ms at the 95th percentile on target hardware.
- **PR-002** Only regions that changed are pushed to the display each frame (dirty-rect `display.update`), verified by an instrumented frame-time and blit-count measurement before and after.
- **PR-003** Keystroke-to-visual-feedback latency <= 2 frames (<= 67 ms).
- **PR-004** Lesson Select builds its card layout once on scene entry; it performs at most one database query per lesson on entry and none per frame.
- **PR-005** Scene transition completes within 500 ms.
- **PR-006** Memory footprint <= 250 MB resident after a 30-minute session with 40 profiles.

## 8. Packaging and deployment requirements

- **PK-001** A committed `TypeCraft.spec` builds with PyInstaller 6.x in `onedir` mode.
- **PK-002** The build is `--windowed` (no console) and named `TypeCraft`.
- **PK-003** `assets/` and the `data/` defaults are bundled as read-only data; read-only resources resolve through `sys._MEIPASS`.
- **PK-004** Writable files are created beside `TypeCraft.exe`, never inside `_internal/` or the extraction directory.
- **PK-005** `dist/TypeCraft/` runs on a clean Windows 10/11 machine with no Python installed.
- **PK-006** The folder can be copied to another path or drive and still run, retaining its own data.
- **PK-007** Restarting the packaged app preserves profiles, attempts, progress, badges, XP, levels, and streaks.
- **PK-008** Replacing the bundled application files while keeping the writable files preserves all student data.
- **PK-009** The repository provides one documented command each to set up a dev environment, run the tests, and produce the build.

## 9. Documentation requirements

- **DOC-001** `README.md`: what TypeCraft is, requirements, dev setup, run, test, build, repo map.
- **DOC-002** Teacher quick-start guide: first launch, creating profiles, setting the PIN, reading the dashboard, resetting a student.
- **DOC-003** Student usage guide: choosing a profile, picking a mode, reading the HUD and keyboard, stars/XP/badges.
- **DOC-004** Deployment and backup guide: copying the folder, USB distribution, backing up and restoring `typecraft.db`, updating the app without losing data.
- **DOC-005** `lessons.json` editing guide: field-by-field contract, the "never change an id" rule, worked example, what happens on a malformed file.
- **DOC-006** Troubleshooting guide: no audio, black window, slow performance, corrupt JSON warning, lost PIN, database recovery.
- **DOC-007** Testing and release checklist: the manual and automated gates required before handing over a build.
- **DOC-008** Documentation matches the shipped build; every command in the docs has been executed.

---

## 10. Acceptance criteria

The project is accepted when all of the following are objectively evidenced in
`PROJECT_STATE.md`:

- **AC-01** A clean checkout reaches a running application using only the documented commands.
- **AC-02** `pytest` passes with zero failures and zero errors; coverage of `engine/` and `managers/` >= 85 % statements.
- **AC-03** 20 lessons across 5 tiers load from `lessons.json` and are all reachable.
- **AC-04** All three input modes pass their behavioural unit tests (FR-032…FR-034).
- **AC-05** FR-043, FR-044, FR-045 invariants hold under randomised keystroke sequences in all three modes.
- **AC-06** Unlock tests pass at 84.99 % (locked) and 85.0 % (unlocked).
- **AC-07** A profile completes a lesson, the app is restarted, and all XP/level/stars/streak/badges are unchanged.
- **AC-08** Escape mid-lesson and window-close mid-lesson each produce exactly one `incomplete` row and do not change aggregates.
- **AC-09** A simulated kill during a lesson leaves an `in_progress` row that becomes `incomplete` on the next start.
- **AC-10** The leaderboard omits profiles with zero completed attempts.
- **AC-11** The dashboard shows all FR-122 fields for >= 40 profiles with working pagination.
- **AC-12** A forced failure inside reset leaves the database byte-identical in content to before the attempt.
- **AC-13** Volume and mute survive a restart; a corrupted `settings.json` produces a visible warning and a working app.
- **AC-14** For every character in bundled lesson content, the keyboard highlights a key and names a finger.
- **AC-15** Measured 95th-percentile frame time <= 33.3 ms in the Lesson scene on target-class hardware, with before/after numbers recorded.
- **AC-16** First run does not overwrite a pre-existing edited `lessons.json`.
- **AC-17** `dist/TypeCraft/` launches on a clean Windows machine without Python, survives relocation and restart.
- **AC-18** All DOC-001…DOC-007 files exist and are accurate.
- **AC-19** `TASKS.md` has no `TODO`/`IN_PROGRESS`/`BLOCKED` item at priority P0 or P1.

## 11. Out of scope

- Any online, cloud, sync, or account feature; telemetry; automatic updates.
- Non-QWERTY layouts, non-English lesson content, right-to-left text.
- macOS and Linux builds (source may run there; not supported or tested).
- Multi-user OS accounts, per-student OS logins, or encryption of the database.
- In-app lesson authoring UI (lessons are edited as JSON in a text editor).
- Networked or cross-machine leaderboards; printing or exporting reports (beyond copying the DB).
- Touch, gamepad, accessibility screen-reader support.
- *(Resizable/fullscreen window was out of scope until 2026-07-31; it is now FR-005.)*
- Reflowing layout: the canvas scales as a whole rather than re-arranging for narrow or
  ultra-wide windows. Letterboxing is accepted at non-16:9 aspect ratios.
- Audio content creation beyond a minimal permitted-licence set of short cues.

## 12. Assumptions

- **AS-01** Students share a single Windows user account; profile selection is trust-based, not authenticated.
- **AS-02** The school PC clock may be wrong; date logic must tolerate backward jumps.
- **AS-03** Machines have a working keyboard; audio output may be absent — audio is optional and must degrade silently.
- **AS-04** Teachers can edit a text file and copy a folder, but will not install Python or use a database tool.
- **AS-05** A classroom is at most ~40 student profiles per machine.
- **AS-06** Bundled assets must be original or permissively licensed (no proprietary fonts/sounds/images).
- **AS-07** The existing `_dev_data/typecraft.db` is a development artifact with no real student data (verified: 0 profiles, 0 attempts) and may be deleted or rebuilt.

## 13. Unresolved questions

- **OQ-001 — RESOLVED 2026-07-29 (blueprint-literal, accepted by default after the choice was
  put to the user).** Backspace changes the cursor and the on-screen character status **only**;
  it never edits `total_keystrokes`, `errors`, or `correct_keystrokes`. Every
  character-producing keystroke posts exactly one ledger entry that is never reversed, so
  `correct + errors == total` holds by construction and no keystroke can be invented. A
  corrected mistake therefore still counts against accuracy: wrong key → Backspace → right
  key is 2 keystrokes and 1 error, i.e. 50 %, not 100 %. A separate non-scoring
  `corrections_made` counter is displayed so a self-correcting student still gets credit for
  noticing. `_error_counted` is deleted, so a repeated wrong key at one position posts a full
  error each time. Implemented in TC-006; asserted by `tests/unit/test_typing_engine.py` and
  `tests/unit/test_invariants.py`. Original wording of the question retained below.

  ~~**OQ-001 (blocks TC-006 policy choice)**~~ Backspace correction accounting. Blueprint §2.4 defines `correct_keystrokes = total_keystrokes − errors` with no retroactive edits, so a corrected error still counts against accuracy. The code comment in `engine/input_modes.py` declares the opposite ("locked decision": corrections retroactively fix the books). The current implementation does neither correctly — it credits `correct_keystrokes` at Backspace time *and* again on the retype, inventing a keystroke that was never pressed.
  **Recommended resolution (default if unanswered):** implement blueprint-literal accounting — Backspace un-does the position it removes (decrementing whichever counter that position contributed and `total_keystrokes` with it), the retype re-counts it normally, and a separate non-scoring `corrections_made` counter is displayed to the student. This preserves FR-043 exactly, cannot invent keystrokes, and still shows a corrected attempt as accurate.
- **OQ-002** Is 40 profiles per machine the right classroom ceiling for FR-014/FR-124 sizing?
- **OQ-003** May permissively-licensed third-party assets be bundled (fonts/sounds), or must all assets be original? Affects TC-017 and AS-06.
- **OQ-004** Should a wrong Shift key (e.g. left Shift for a left-hand capital) be flagged as a technique error, or only the resulting character checked? Current spec: only the character is checked.
- **OQ-005** Does the teacher need any progress export beyond copying `typecraft.db`? Currently out of scope.
- **OQ-006 (raised by TC-006, for Phase 4)** In `BackspaceMode`, a wrong **final** character
  can never be corrected: the attempt completes the instant the cursor reaches the end of the
  target, and `LessonScene` transitions straight to Results. FR-033 promises that incorrect
  characters can be revisited; FR-047 says a finished attempt ignores further input. Both are
  currently honoured, and they collide only on the last character.
  **Options:** (a) accept it — the student retries the lesson, which is unlimited (FR-063);
  (b) treat the attempt as complete only when the cursor reaches the end *and* the student
  confirms, giving a chance to fix the last character in `BackspaceMode` only; (c) auto-finish
  only when the final character is correct. Not a regression — this is inherited behaviour. No
  code decision was taken in TC-006; the engine follows FR-047 literally. Recommend (a) unless
  classroom observation shows it frustrates students.

---

## 14. Requirement → task traceability

| Requirement group | Tasks |
|---|---|
| FR-001…FR-006, NFR-001…NFR-003 | TC-001, TC-002, TC-003, TC-019, **TC-025** |
| FR-010…FR-016 | TC-007, TC-014 |
| FR-020…FR-027 | TC-005, TC-007, TC-014, TC-016 |
| FR-030…FR-036 | TC-005, TC-006 |
| FR-040…FR-048 | TC-005, TC-006 |
| FR-050…FR-058 | TC-005, TC-006, TC-008b |
| FR-060…FR-066 | TC-007 |
| FR-070…FR-076 | TC-008, TC-009, TC-010 |
| FR-080…FR-087 | TC-007, TC-013b |
| FR-057 (daily streak bonus — unimplemented, D-31) | TC-013b |
| FR-090…FR-096 | TC-015 |
| FR-100…FR-104 | TC-016, TC-024, **TC-026** |
| FR-110…FR-114 | TC-012 |
| FR-120…FR-127 | TC-008, TC-013, TC-014 |
| FR-130…FR-135 | TC-011, TC-011b |
| NFR-004…NFR-014, PR-001…PR-006 | TC-018, TC-022 |
| DR-001…DR-014 | TC-008, TC-008b, TC-009, TC-020 |
| SR-001…SR-007 | TC-011b, TC-012 |
| PK-001…PK-009 | TC-003, TC-020, TC-022 |
| DOC-001…DOC-008 | TC-021 |
| AC-01…AC-19 | TC-022 |

Coverage rule: every FR/NFR/DR/SR/PR/PK/DOC id above must appear in at least one task's
"Requirement IDs" field in `TASKS.md`. Any requirement without a task, or task without a
requirement, is a traceability defect to be fixed before the next task starts.
