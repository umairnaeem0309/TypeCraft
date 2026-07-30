# TypeCraft Deployment and Backup Guide

How to put TypeCraft on a school computer, move it between machines, and protect student data.

---

## 1. What you copy

The release is the entire `dist/TypeCraft/` folder produced by PyInstaller. It contains:

- `TypeCraft.exe` — the application
- `_internal/` — read-only application files (do not edit)
- After first run, writable files appear **beside `TypeCraft.exe`**:
  - `typecraft.db`
  - `settings.json`
  - `lessons.json`
  - `badges.json`
  - `messages.json`
  - `typecraft.log`

Copy the **whole folder**, not just the `.exe`.

---

## 2. USB distribution

1. Build or obtain the release folder (see [`testing-and-release-checklist.md`](testing-and-release-checklist.md)).
2. Copy the whole `TypeCraft` folder to a USB drive.
3. On each target computer, copy the folder from the USB to a local drive.
4. Double-click `TypeCraft.exe`.

> **Do not run the app directly from the USB stick for everyday use.** USB drives are slower and easier to lose. Use them only for installation or backup.

---

## 3. Backing up student data

The only files you need to back up are the writable files beside `TypeCraft.exe`:

- `typecraft.db` — student profiles and attempts (most important)
- `settings.json` — PIN, volume, mute
- `lessons.json`, `badges.json`, `messages.json` — teacher-edited copies
- `typecraft.log` — useful for diagnosing problems

Recommended backup methods:

- Copy the entire `TypeCraft` folder to a network share or USB stick.
- Copy just the files listed above to a zip file named `TypeCraft-backup-<date>.zip`.

Back up before any of these events:
- Major Windows updates
- Re-imaging the lab machine
- Editing `lessons.json`
- Migrating to a new version of TypeCraft

---

## 4. Restoring from backup

1. Close TypeCraft on the target machine.
2. Copy the backed-up files beside the existing `TypeCraft.exe`, replacing the current ones.
3. Restart TypeCraft.

If a backup only contains `typecraft.db`, that is enough to restore all student progress. The JSON files will be re-seeded from the bundled defaults if they are missing.

---

## 5. Updating the app without losing data

TypeCraft keeps student data **outside** the read-only `_internal/` folder. This means you can update the app by replacing only the application files:

1. Close TypeCraft.
2. Rename the old `TypeCraft` folder to `TypeCraft-old` (just in case).
3. Copy the new `TypeCraft` folder to the same location.
4. From the old folder, copy these files into the new folder:
   - `typecraft.db`
   - `settings.json`
   - `lessons.json`
   - `badges.json`
   - `messages.json`
5. Start the new `TypeCraft.exe`.

If you only replace `_internal/`, that also works, but copying the whole folder is safer because the new folder may contain updated DLLs.

---

## 6. Moving to a different computer

1. Install TypeCraft on the new computer.
2. Close TypeCraft on both machines.
3. Copy the writable files from the old computer to the new one, beside `TypeCraft.exe`.
4. Start TypeCraft on the new computer.

The app does not support syncing between multiple live computers. Pick one computer as the source of truth before migrating.

---

## 7. What NOT to delete

Never delete or edit these files while students are using the app:

- `typecraft.db`
- `_internal/` (read-only, but deleting it breaks the app)

The `_internal/` folder is rebuilt every time you run the build script. The writable files are not — they are your school’s data.
