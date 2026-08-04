# TypeCraft Teacher Quick-Start Guide

How to get a class typing in minutes, keep their progress safe, and manage students day to day.

---

## 1. First launch

1. Copy the whole `TypeCraft` folder to the computer (USB, network share, or direct download).
2. Double-click `TypeCraft.exe`.
3. The Main Menu appears. The first time TypeCraft runs on a new computer it creates these files **beside `TypeCraft.exe`**:
   - `typecraft.db` — student profiles, attempts, and progress
   - `settings.json` — volume, mute, and the teacher PIN
   - `lessons.json` — the editable copy of the lesson list
   - `badges.json` — the editable copy of the badge catalogue
   - `messages.json` — the editable copy of result messages
   - `typecraft.log` — diagnostic log

> **Never delete these files while students are using the app.** They are the only copy of their progress on that machine.

---

## 2. Creating profiles

1. On the Main Menu, click **Choose Profile**.
2. Click **New Profile**.
3. Type the student’s unique code and name, for example `S001_Ali`, then press Enter or click **Create**.
4. The new profile appears in the grid. Each student should use the same profile every time.

Use a unique code because profiles can be created on different offline computers and later imported into one teacher database. Keep profile names short — the cards fit better on screen.

---

## 3. Setting or changing the teacher PIN

The PIN protects the Teacher Dashboard. PIN changes are available only inside that dashboard;
Settings is reserved for classroom audio preferences.

1. From the Main Menu, click **Teacher Dashboard**.
2. On a first launch, click **Set PIN**. On later visits, enter the current PIN to unlock the dashboard, then click **Change PIN**.
3. Enter a new 4-digit PIN and confirm it. When changing an existing PIN, the current PIN is verified first.

The PIN is stored securely as a salted hash in `settings.json`; the raw PIN is never written there.
If you forget it, see the *Lost PIN* section in [`troubleshooting.md`](troubleshooting.md).

---

## 4. Reading the dashboard

Open the Teacher Dashboard and enter the PIN. You will see:

| Column | Meaning |
|---|---|
| Name | Student profile name |
| Level | Current typing level (1–10) |
| XP | Total experience points |
| Lessons Done | Distinct lessons completed |
| Avg WPM | Average net words-per-minute across completed attempts |
| Avg Accuracy | Average accuracy across completed attempts |
| Badges | Number of badges earned |
| Current Streak | Consecutive days with a completed lesson |
| Longest Streak | Best ever consecutive-day streak |

Scroll up and down with the mouse wheel, Page Up/Page Down, or drag to see a large class.

---

## 5. Combining results from multiple computers

Each offline computer keeps its own `typecraft.db`. To combine classroom results,
use **Export Results** on each computer, copy the generated
`typecraft_export_<database-id>.json` files to the teacher computer beside
`TypeCraft.exe`, and click **Import Results** in the Teacher Dashboard. Profiles
are matched by their normalized name/code, not by local SQLite IDs. Importing the
same export again is safe; already imported attempts are skipped.

Back up the teacher computer's `typecraft.db` before importing. Never replace it
with a student computer's database, and do not copy `settings.json` between
machines. See [`offline-sync.md`](offline-sync.md) for the complete USB workflow.

---

## 6. Resetting a student

Resetting a student erases their lesson attempts and progress, but keeps their profile name and PIN. This cannot be undone.

1. In the Teacher Dashboard, find the student row.
2. Click **Reset**.
3. Read the confirmation box. It names the student and lists exactly what will be erased.
4. Click **Confirm** to proceed, or **Cancel** / press Escape to abort.
5. The row refreshes automatically; the student keeps their profile but starts with zero progress.

A reset runs inside a database transaction. If anything goes wrong (power cut, disk full), the student’s data is left unchanged.

---

## 7. Locked and unlocked lessons

Students start with only the first lesson unlocked. A lesson unlocks when the previous one is completed. The unlocked status is saved in `typecraft.db`.

If you edit `lessons.json` (see [`editing-lessons.md`](editing-lessons.md)), existing student progress is not affected; only the lesson content, titles, or order numbers change.
