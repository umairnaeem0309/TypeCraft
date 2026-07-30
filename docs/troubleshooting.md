# TypeCraft Troubleshooting Guide

Common problems and how to fix them.

---

## 1. No audio

Symptom: typing sounds, completion sounds, or badge sounds do not play.

Check these in order:

1. **Speaker/headphones** are plugged in and the volume is up.
2. **Windows mixer** — right-click the speaker icon, open Volume Mixer, and make sure `TypeCraft.exe` is not muted.
3. **In-app mute** — open Settings from the Main Menu and make sure **Mute** is off.
4. **In-app volume** — in Settings, raise the volume.
5. **No audio device** — TypeCraft silently continues if no audio device is present. It will not crash, but it will be silent.

If you changed the volume or mute, the change is saved to `settings.json` immediately.

---

## 2. Black window or window does not appear

Symptom: TypeCraft starts, but the window is black, blank, or never opens.

Try:

1. **Wait 10 seconds.** On very slow machines the first render can take a moment.
2. **Check the log.** Open `typecraft.log` beside `TypeCraft.exe` and look for error lines near the bottom.
3. **Run with the dummy driver** (developers only) to see if it is a display issue:
   ```cmd
   set SDL_VIDEODRIVER=dummy
   TypeCraft.exe
   ```
   If this starts but the normal window does not, the problem is likely the graphics driver.
4. **Update the graphics driver.** TypeCraft uses pygame/SDL2 and needs basic OpenGL support.
5. **Lower display scaling.** On high-DPI laptops, set Windows display scaling to 100 % and try again.

---

## 3. Slow performance

Symptom: typing feels laggy or the cursor lags behind keystrokes.

1. **Close other programs.** TypeCraft should run on 4 GB RAM, but a browser with many tabs can starve it.
2. **Lower screen resolution.** Running at a lower Windows resolution reduces the load on integrated graphics.
3. **Run with `--full-repaint` only for debugging.** By default TypeCraft uses dirty-rect updates. If you launched with `--full-repaint`, remove it.
4. **Check the profile CSV.** Launch with:
   ```cmd
   TypeCraft.exe --profile
   ```
   This writes `typecraft_profile.csv` beside the exe. Open it and check the `render_ms` column. If values are consistently above 33 ms, the machine is below spec.

---

## 4. Corrupt JSON warning

Symptom: a yellow notice says *“Lessons file could not be loaded; using defaults”* (or similar).

What happened: one of the editable JSON files (`lessons.json`, `badges.json`, `messages.json`, `settings.json`) is malformed.

Fix:

1. Open `typecraft.log` and find the exact file and error.
2. Open the file in a plain text editor (Notepad) or JSON editor.
3. Fix the syntax error. Common issues:
   - Trailing comma after the last item
   - Single quotes instead of double quotes
   - Missing closing brace or bracket
4. Save and restart TypeCraft.

If you cannot fix it, delete the offending JSON file. TypeCraft will re-seed it from the bundled default on the next launch. You will lose any custom edits in that file, but student progress in `typecraft.db` is unaffected.

---

## 5. Lost PIN

Symptom: you forgot the teacher PIN and cannot open the Teacher Dashboard or Settings.

The PIN is stored in `settings.json` as a hash — it cannot be read directly. To reset it:

1. Close TypeCraft.
2. Delete `settings.json` beside `TypeCraft.exe`.
3. Restart TypeCraft.
4. The app creates a fresh `settings.json` with no PIN. Set a new one from the Teacher Dashboard or Settings screen.

**Important:** deleting `settings.json` only resets the PIN, volume, and mute. It does not touch student profiles or attempts in `typecraft.db`.

---

## 6. Database recovery

Symptom: TypeCraft crashes on launch with an error mentioning `typecraft.db`, or student data looks wrong.

### 6.1 If you have a backup

1. Close TypeCraft.
2. Rename the current `typecraft.db` to `typecraft.db.broken`.
3. Copy your backed-up `typecraft.db` beside `TypeCraft.exe`.
4. Restart TypeCraft.

### 6.2 If you do not have a backup

1. Close TypeCraft.
2. Rename `typecraft.db` to `typecraft.db.recover`.
3. Restart TypeCraft. A fresh empty database will be created.
4. If the app starts, the original database may be corrupted.
5. If the corrupt file contains critical data, contact support with `typecraft.db.recover` and `typecraft.log`.

### 6.3 Preventing corruption

- Always close TypeCraft before copying `typecraft.db`.
- Do not edit `typecraft.db` with external tools unless you know SQLite.
- Keep regular backups (see [`deployment-and-backup.md`](deployment-and-backup.md)).

---

## 7. Still stuck?

Collect these items when asking for help:

- `typecraft.log`
- The exact Windows version
- The text of any error message or warning notice
- Whether the problem happens every time or only sometimes

Attach the log and a description of the steps that led to the problem.
