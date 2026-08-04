# TypeCraft Testing and Release Checklist

Use this checklist before handing a build to a school or uploading a release.

---

## 1. Automated tests

Run from the repository root inside the virtual environment:

```bash
.venv\Scripts\python -m pytest -q
```

- [ ] **707 tests pass, 4 skipped, 0 xfail, 0 unexpected failures.**
- [ ] Coverage of `engine/` + `managers/` remains ≥ 85 %.

Run the slow packaging test at least once before release:

```bash
.venv\Scripts\python -m pytest tests/integration/test_packaging.py -v
```

- [ ] The built `dist/TypeCraft/TypeCraft.exe` launches under SDL dummy.
- [ ] `typecraft.log` is written beside the executable, not under `_internal/`.

---

## 2. Build a release

```bash
.venv\Scripts\python scripts/build_release.py
```

- [ ] Command completes without errors.
- [ ] `dist/TypeCraft/` contains `TypeCraft.exe` and `_internal/`.
- [ ] `dist/TypeCraft/_internal/assets/` and `dist/TypeCraft/_internal/data/` exist.
- [ ] No writable files (`.db`, `.json`, `.log`) exist inside `dist/TypeCraft/_internal/`.

---

## 3. Clean Windows acceptance

On a machine with no Python installed:

- [ ] Copy the entire `dist/TypeCraft/` folder.
- [ ] Double-click `TypeCraft.exe` — the Main Menu opens.
- [ ] Create a profile.
 [ ] Start a lesson and type at least one character.
- [ ] Close the window, reopen, and confirm the incomplete attempt was saved.
- [ ] Complete a lesson and confirm stars, XP, and badge messages appear.
- [ ] Open the Teacher Dashboard, set a PIN, leave and reopen it, enter the current PIN, change the PIN, and view the student summary.
- [ ] Reset a student and confirm the dashboard refreshes.
- [ ] Restart the computer, reopen the app, and confirm data persists.

---

## 4. Documentation verification

- [ ] `README.md` is updated and does not say “not releasable.”
- [ ] All commands in `docs/` files are correct and have been followed at least once.
- [ ] `docs/deployment-and-backup.md` explains how to back up `typecraft.db`.
- [ ] `docs/troubleshooting.md` covers lost PIN, corrupt JSON, and database recovery.
- [ ] `docs/editing-lessons.md` includes the “never change an id” rule and a worked example.

---

## 5. Final packaging

- [ ] Version number is recorded in `pyproject.toml` if changed.
- [ ] `typecraft_profile*.csv` is not included in the release folder (it is ignored by git).
- [ ] The release folder is zipped as `TypeCraft-<version>-windows.zip` or similar.
- [ ] The zip contains the whole `TypeCraft/` folder.

---

## 6. Handover

When giving the build to a school, include:

1. The release zip or the release folder.
2. Printed or emailed links to:
   - `docs/teacher-quickstart.md`
   - `docs/student-guide.md`
   - `docs/deployment-and-backup.md`
   - `docs/troubleshooting.md`
3. A note: *“Back up the files beside TypeCraft.exe, especially `typecraft.db`, before any Windows update or reinstall.”*

---

## 7. Post-release monitoring

For the first week after deployment:

- [ ] Collect any `typecraft.log` files that contain errors.
- [ ] Confirm teachers can open the dashboard and reset students.
- [ ] Confirm students can complete lessons and see their progress persist.
- [ ] File any new issues in the project tracker with the log attached.
