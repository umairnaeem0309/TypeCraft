# Offline classroom export and import

TypeCraft is offline and each computer has its own `typecraft.db`. To combine
results from several computers without copying or merging SQLite files manually,
use the Teacher Dashboard's JSON export/import controls.

## First setup

1. Build or copy one clean `dist/TypeCraft` folder to each student computer.
2. Do this before the first launch. Never copy a used computer's whole folder to
   another computer.
3. Give every student a unique profile code in the profile name, for example:
   `S001_Ali`, `S002_Sara`, and `S003_Hassan`.
4. A profile may be created on any machine. The numeric database ID is local and
   is not used to identify the student during import.

## Collecting results

On each student computer:

1. Close any lesson currently in progress.
2. Open **Teacher Dashboard** and enter the teacher PIN.
3. Click **Export Results**.
4. TypeCraft creates a file named `typecraft_export_<database-id>.json` beside
   `TypeCraft.exe` (or beside the source-run data in `_dev_data`).
5. Copy that JSON file to the teacher's USB drive.

Only student profiles, attempts, progress, and known badges are exported. The
teacher PIN, `settings.json`, audio settings, and SQLite file are never exported.

## Importing on the teacher computer

1. Back up the teacher computer's `typecraft.db`.
2. Copy all collected `typecraft_export_*.json` files beside the teacher's
   `TypeCraft.exe`.
3. Open TypeCraft, enter the Teacher Dashboard, and click **Import Results**.
4. The dashboard refreshes and reports the number of new profiles and attempts.
5. Keep the JSON files as an audit backup until the teacher verifies the results.

Profiles are matched by the normalized profile name. A new code creates a new
profile on the teacher computer; an existing code updates that profile. Local
numeric profile IDs are mapped safely and never copied between databases.

## Repeating an import safely

Importing the same JSON file again is safe. TypeCraft records the source database
ID and source attempt ID, so an already imported attempt is skipped rather than
duplicated. If a student completes more work later, export again from that
machine; the new attempts are imported while the old ones are skipped.

Keep students on one assigned profile and do not change the code/name between
machines. If two students use the same name, the teacher must rename them to
unique codes before exporting; otherwise the import cannot safely know which
student is which.

## Safety rules

- Close TypeCraft before copying an export file.
- Back up the teacher's `typecraft.db` before every import.
- Never replace the teacher database with a student database.
- Never copy `settings.json` between machines; it contains each machine's
  teacher PIN and audio preferences.
- Do not put `typecraft.db` on a shared network drive or cloud-synchronized
  folder.
