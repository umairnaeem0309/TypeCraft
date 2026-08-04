# Editing TypeCraft Lessons

How to change lesson content, add lessons, and keep the file valid.

---

## 1. Which file to edit

Edit the **writable** copy of `lessons.json` that sits **beside `TypeCraft.exe`** (or in `_dev_data/` when running from source). This is the live copy used by the app.

Do not edit the bundled default inside `_internal/data/lessons.json` — it is read-only and will be restored if the app is reinstalled.

---

## 2. File structure

The short snippet below is **illustrative JSON structure**, not a complete production lesson. Bundled lessons follow the tier length and character rules in Section 4.

```json
{
  "schema_version": 1,
  "tiers": [
    {
      "tier": 1,
      "name": "Home Row",
      "color": "#4CAF50",
      "lessons": [
        {
          "id": "t1l1",
          "order": 1,
          "title": "Home Row: f and j",
          "finger_focus": ["left_index", "right_index"],
          "default_mode": "lock_on_error",
          "target_wpm": 8,
          "lines": [
            "f j fj jf fff jjj fj jf fj fj f j f j fj jf fff jjj fj jf"
          ]
        }
      ]
    }
  ]
}
```

---

## 3. Field-by-field contract

| Field | Required | Rules |
|---|---|---|
| `schema_version` | Yes | Must be `1`. Do not change this. |
| `tiers` | Yes | Array of tier objects, ordered 1–N. |
| `tier` | Yes | Integer ≥ 1. Determines the tab/stage. |
| `name` | Yes | Display name of the tier (e.g. `Home Row`). |
| `color` | Yes | CSS hex colour for the tier (e.g. `#4CAF50`). |
| `lessons` | Yes | Array of lesson objects in this tier. |
| `id` | Yes | Unique string across the whole file. **Never change an id after students have attempted that lesson.** |
| `order` | Yes | Integer ordering across all lessons. Start at 1 and increment by 1. Determines unlock order. |
| `title` | Yes | Short display title. |
| `finger_focus` | Yes | List of finger names from the supported set (see below). |
| `default_mode` | Yes | One of `lock_on_error`, `backspace`, `free_advance`. |
| `target_wpm` | Yes | Suggested WPM for that lesson. Does not block progress. |
| `lines` | Yes | Array of strings joined with spaces into one continuous target. Keep each lesson substantial but appropriate to its tier: early lessons use key-restricted drills and words, middle lessons use sentences, and advanced lessons use longer paragraphs. Multiple strings remain supported for backward compatibility. |

Supported finger names:

- `left_pinky`, `left_ring`, `left_middle`, `left_index`
- `right_pinky`, `right_ring`, `right_middle`, `right_index`
- `left_thumb`, `right_thumb`

---

## 4. Curriculum content rules

TypeCraft uses a gradual school-friendly sequence. Do not append the same generic paragraph to every lesson.

- **Tier 1 — Home Row:** substantial key drills and home-row words using only `a s d f j k l` and spaces. Target roughly 120–280 characters.
- **Tier 2 — Top Row:** meaningful words and short sentences using only the home and top rows. Target roughly 160–320 characters.
- **Tier 3 — Bottom Row:** several simple lowercase sentences with periods. Target roughly 220–320 characters.
- **Tier 4 — Capitals & Punctuation:** medium-length school sentences introducing capitals, commas, and question marks. Target roughly 240–320 characters.
- **Tier 5 — Speed & Fluency:** varied, meaningful paragraphs. Target roughly 350–600 characters.

A lesson must not require a letter or symbol before the tier that teaches it. The 85% accuracy unlock rule remains the progression gate; `target_wpm` is guidance, not a barrier.

## 5. The “never change an id” rule

Student progress is linked to lesson `id`s inside `typecraft.db`. If you change an id, the app treats it as a brand new lesson.

- **Safe:** change `title`, `lines`, `target_wpm`, `finger_focus`, or `default_mode`.
- **Unsafe:** change the `id` of an existing lesson. Student progress for the old id becomes invisible.

If you must rename an id, reset the affected students (see [`teacher-quickstart.md`](teacher-quickstart.md)) or accept that their old attempts will no longer count toward unlocking.

---

## 6. Worked example: adding a new lesson

Add a new lesson to Tier 1 after `t1l4`:

```json
{
  "id": "t1l5",
  "order": 5,
  "title": "Home Row Extra",
  "finger_focus": ["left_index", "right_index"],
  "default_mode": "lock_on_error",
  "target_wpm": 10,
  "lines": [
    "a sad lad asks dad all fall a flask falls sad lads ask dad a lad adds a salad dad asks a sad lad all fall a flask falls a lad asks dad sad lads ask a lad add a salad a sad lad asks dad a flask falls all fall a lad adds a salad sad dad asks a lad"
  ]
}
```

Then update the `order` fields so they stay contiguous. In this case `t1l5` gets `order: 5`; nothing else needs to change.

Save the file and restart TypeCraft. The new lesson appears in the lesson grid. It is locked until the previous lesson is completed.

---

## 7. What happens if the file is malformed

If `lessons.json` is invalid JSON or misses required fields:

- TypeCraft **does not crash**.
- It falls back to the bundled default lessons.
- A yellow warning notice appears at the top of every scene.
- The reason is written to `typecraft.log`.
- Your broken file is **left on disk unchanged** so you can inspect and fix it.

To recover:

1. Open `typecraft.log` and read the error line.
2. Open `lessons.json` in a JSON editor.
3. Fix the syntax error or missing field.
4. Restart TypeCraft.

A common mistake is a trailing comma after the last item in an array or object. Another is using a `'` (single quote) inside a string without escaping it — JSON only accepts double quotes.
