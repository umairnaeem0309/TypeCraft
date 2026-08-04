# TypeCraft

A typing tutor for The Bridge School. Everything runs on this computer — no internet, no
accounts, no installation.

---

## Start it

Double-click **`TypeCraft.exe`**.

If Windows shows a blue "Windows protected your PC" box, that is only because the file is not
code-signed: click **More info**, then **Run anyway**.

The window can be resized or maximised. Press **F11** for fullscreen.

---

## First time on a new computer

1. Copy this whole **TypeCraft** folder onto the computer — anywhere is fine (Desktop, `C:\`, a
   USB stick). Keep the folder together; the `_internal` folder next to the .exe is required.
2. Start it and choose **PLAY**, then **Create Profile** for each student. Use a unique code in each name, for example `S001_Ali`.
3. Optional but recommended: open **Teacher Dashboard** and use **Set PIN** on first launch.
   Once a PIN is set, the dashboard asks for it; use **Change PIN** inside the authenticated
   dashboard to replace it. Without a PIN, anyone can reset a student's progress.

Students then pick their own name each time they sit down.

---

## What is in this folder

| Item | What it is | Safe to delete? |
|---|---|---|
| `TypeCraft.exe` | The program | No |
| `_internal\` | Program files it needs to run | No |
| `typecraft.db` | **Every student's progress** | **No — back this up** |
| `lessons.json` | The lesson text, editable in Notepad | No |
| `badges.json`, `messages.json` | Badge names and praise messages | No |
| `settings.json` | Volume, mute, and the teacher PIN (stored as a hash) | No |
| `typecraft.log` | Diagnostic log, useful when reporting a problem | Yes |
| `typecraft-crash.log` | Only appears if the program has crashed | Yes |

The `.json` files and `typecraft.db` are created the first time you run it.

---

## Back up student progress

**Copy `typecraft.db` to a USB stick.** That single file holds every student's profile,
attempts, XP, badges and streaks.

To restore, copy it back beside `TypeCraft.exe`, replacing the file there.

Do it at the end of each week. If that file is lost, the students' progress is lost with it.

## Combine results from multiple offline computers

Each computer has its own database. On each machine, open the authenticated Teacher Dashboard and click **Export Results**. Copy every generated `typecraft_export_*.json` file beside the teacher computer's `TypeCraft.exe`, back up the teacher's `typecraft.db`, then click **Import Results**. The app matches profiles by their unique names/codes and maps local database IDs safely. Re-importing the same export does not duplicate attempts.

Never replace the teacher database with a student database, and never copy `settings.json` between machines. See `offline-sync.md` in the project documentation for the detailed USB workflow.

---

## Update to a newer version

1. Back up `typecraft.db` first.
2. Replace **`TypeCraft.exe`** and the **`_internal`** folder with the new ones.
3. Leave `typecraft.db` and the `.json` files alone.

Student progress and any lesson edits survive, because they live beside the program rather than
inside it.

---

## Change the lesson text

Open `lessons.json` in Notepad. You may safely change:

- `title` — the name shown on a lesson card
- `lines` — the text students type
- `target_wpm` — the speed goal

**Never change an `id`.** Those are how student results are matched to lessons; changing one
orphans that student's history.

Save the file and restart TypeCraft. If the file has a mistake in it, TypeCraft keeps working
with the built-in lessons and shows a warning at the top of the screen — your file is left
untouched so you can find the error.

---

## Common problems

**It will not start / closes immediately.**
Check `typecraft-crash.log` and `typecraft.log` in this folder, and send them on when reporting
the problem.

**No sound.**
Check **Settings** — the Mute button turns amber when muted. Some school PCs have no working
audio device; TypeCraft runs silently in that case and everything else still works.

**A student cannot see their name.**
The list scrolls. Use the mouse wheel or **Page Down** — the scrollbar on the right shows there
is more below.

**I forgot the teacher PIN.**
Close TypeCraft, open `settings.json` in Notepad, and change the
`"teacher_pin_hash"` line to `"teacher_pin_hash": null`. Save, restart, and set a new PIN in
 the Teacher Dashboard. This does not affect any student's progress.

**A student's progress needs clearing.**
Teacher Dashboard → **Reset** on their row → confirm. Their name and avatar are kept; attempts,
XP, badges and streaks are erased. It cannot be undone, so back up `typecraft.db` first.

---

## What students see

Lessons unlock in order. Finishing one with **85% accuracy or better** unlocks the next; speed
never blocks progress. Retries are unlimited and never lose anything already earned.

Three typing modes are offered before each lesson:

- **Lock on Error** — the cursor waits until the right key is pressed. Best for beginners.
- **Backspace Allowed** — mistakes can be corrected. A corrected mistake still counts, so
  accuracy reflects what was actually typed.
- **Free Advance** — every keypress moves on. For speed practice.
