"""
ui/keyboard_renderer.py

The on-screen keyboard that actually teaches touch typing (FR-090..FR-096).

What it replaces: a 4x10 grid of letter keys with no Space, no Shift and no
punctuation beyond `;,./`, which highlighted the key the student had **just
pressed** and never said which finger to use. A child could not have learned touch
typing from it — Space is the most-typed key in every lesson, and Tier 4 is built
entirely from capitals and punctuation the widget could not draw.

Three things it now does:

  - covers every character in `lessons.json`, including shifted ones
  - highlights the **next expected** key, not the last one pressed
  - highlights the Shift on the *opposite* hand when a capital is needed, and names
    the finger in words rather than relying on colour alone

Performance (§5.3): the whole board is drawn once to a base surface on scene entry;
each frame blits that surface and outlines at most two keys on top.
"""

import pygame

from typecraft.ui import theme

KEY_W, KEY_H, GAP = 48, 44, 5

#: (label, char, width in key-units, finger). `char` is what the key produces
#: unshifted; None marks a modifier or a key lessons never require. Finger
#: assignments are the standard touch-typing home-row reach.
ROWS = [
    [("`", "`", 1.0, "left_pinky"), ("1", "1", 1.0, "left_pinky"),
     ("2", "2", 1.0, "left_ring"), ("3", "3", 1.0, "left_middle"),
     ("4", "4", 1.0, "left_index"), ("5", "5", 1.0, "left_index"),
     ("6", "6", 1.0, "right_index"), ("7", "7", 1.0, "right_index"),
     ("8", "8", 1.0, "right_middle"), ("9", "9", 1.0, "right_ring"),
     ("0", "0", 1.0, "right_pinky"), ("-", "-", 1.0, "right_pinky"),
     ("=", "=", 1.0, "right_pinky"), ("Bksp", None, 2.0, "right_pinky")],

    [("Tab", None, 1.5, "left_pinky"), ("Q", "q", 1.0, "left_pinky"),
     ("W", "w", 1.0, "left_ring"), ("E", "e", 1.0, "left_middle"),
     ("R", "r", 1.0, "left_index"), ("T", "t", 1.0, "left_index"),
     ("Y", "y", 1.0, "right_index"), ("U", "u", 1.0, "right_index"),
     ("I", "i", 1.0, "right_middle"), ("O", "o", 1.0, "right_ring"),
     ("P", "p", 1.0, "right_pinky"), ("[", "[", 1.0, "right_pinky"),
     ("]", "]", 1.0, "right_pinky"), ("\\", "\\", 1.5, "right_pinky")],

    [("Caps", None, 1.75, "left_pinky"), ("A", "a", 1.0, "left_pinky"),
     ("S", "s", 1.0, "left_ring"), ("D", "d", 1.0, "left_middle"),
     ("F", "f", 1.0, "left_index"), ("G", "g", 1.0, "left_index"),
     ("H", "h", 1.0, "right_index"), ("J", "j", 1.0, "right_index"),
     ("K", "k", 1.0, "right_middle"), ("L", "l", 1.0, "right_ring"),
     (";", ";", 1.0, "right_pinky"), ("'", "'", 1.0, "right_pinky"),
     ("Enter", None, 2.25, "right_pinky")],

    [("Shift", "LSHIFT", 2.25, "left_pinky"), ("Z", "z", 1.0, "left_pinky"),
     ("X", "x", 1.0, "left_ring"), ("C", "c", 1.0, "left_middle"),
     ("V", "v", 1.0, "left_index"), ("B", "b", 1.0, "left_index"),
     ("N", "n", 1.0, "right_index"), ("M", "m", 1.0, "right_index"),
     (",", ",", 1.0, "right_middle"), (".", ".", 1.0, "right_ring"),
     ("/", "/", 1.0, "right_pinky"), ("Shift", "RSHIFT", 2.75, "right_pinky")],

    [("Space", " ", 6.5, "thumb")],
]

#: Horizontal offset per row, in key-units. Real keyboards stagger their rows, and
#: the space bar sits under the letters rather than flush left — without this the
#: board looked lopsided, with a 12-unit space bar hanging off the left edge.
ROW_OFFSETS = [0.0, 0.0, 0.25, 0.0, 3.75]

#: Unshifted -> shifted for the number row and punctuation. Capitals are derived
#: from str.upper(), so they are not listed here.
SHIFT_PAIRS = {
    "`": "~", "1": "!", "2": "@", "3": "#", "4": "$", "5": "%", "6": "^",
    "7": "&", "8": "*", "9": "(", "0": ")", "-": "_", "=": "+",
    "[": "{", "]": "}", "\\": "|", ";": ":", "'": '"', ",": "<", ".": ">", "/": "?",
}

#: Finger names in words. Colour alone is not guidance a child can act on
#: (FR-093), and it is no guidance at all for a colour-blind student.
FINGER_LABELS = {
    "left_pinky": "left little finger", "left_ring": "left ring finger",
    "left_middle": "left middle finger", "left_index": "left index finger",
    "right_index": "right index finger", "right_middle": "right middle finger",
    "right_ring": "right ring finger", "right_pinky": "right little finger",
    "thumb": "either thumb",
}

#: Left-hand keys take the RIGHT Shift and vice versa — reaching across is the
#: technique being taught, rather than contorting one hand.
_OPPOSITE_SHIFT = {"left": "RSHIFT", "right": "LSHIFT"}

MODIFIERS = ("LSHIFT", "RSHIFT")


def _build_char_index():
    """char -> (key id, shift required) for every character a lesson can contain."""
    index = {}
    for row in ROWS:
        for _label, char, _width, _finger in row:
            if char is None or char in MODIFIERS:
                continue
            index[char] = (char, False)
            upper = char.upper()
            if upper != char:
                index[upper] = (char, True)                # capitals
            if char in SHIFT_PAIRS:
                index[SHIFT_PAIRS[char]] = (char, True)    # shifted punctuation
    return index


CHAR_TO_KEY = _build_char_index()

_FINGER_BY_KEY = {
    char: finger
    for row in ROWS
    for _label, char, _width, finger in row
    if char is not None
}


def finger_for(char: str):
    """The finger that should type `char`, or None if the board cannot type it."""
    entry = CHAR_TO_KEY.get(char)
    return None if entry is None else _FINGER_BY_KEY.get(entry[0])


def shift_side_for(char: str):
    """Which Shift key `char` needs (`LSHIFT`/`RSHIFT`), or None if it needs none."""
    entry = CHAR_TO_KEY.get(char)
    if entry is None or not entry[1]:
        return None
    finger = _FINGER_BY_KEY.get(entry[0], "")
    return _OPPOSITE_SHIFT["left" if finger.startswith("left") else "right"]


class KeyboardRenderer:
    def __init__(self, resource_manager, origin=(0, 0)):
        self.resources = resource_manager
        self.origin = origin
        self.key_rects = {}
        self.finger_colors = theme.FINGER_COLORS
        self.base_layer = None
        self.prerender_count = 0
        self._active_key = None
        self._active_shift = None
        self._active_finger = None
        self._expected_char = None
        self._caption_surf = None

    # --- geometry ----------------------------------------------------------

    @staticmethod
    def size():
        width = max(
            ROW_OFFSETS[i] * KEY_W + sum(w * KEY_W + GAP for _l, _c, w, _f in row)
            for i, row in enumerate(ROWS)
        )
        return int(width), len(ROWS) * (KEY_H + GAP)

    def prerender(self) -> None:
        """Draw every key once (§5.3). Scene entry only, never per frame."""
        width, height = self.size()
        self.base_layer = pygame.Surface((width, height), pygame.SRCALPHA).convert_alpha()
        self.prerender_count += 1

        font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_SMALL)
        self.key_rects = {}

        y = 0
        for row_index, row in enumerate(ROWS):
            x = ROW_OFFSETS[row_index] * KEY_W
            for label, char, units, finger in row:
                key_w = int(units * KEY_W)
                rect = pygame.Rect(int(x), y, key_w, KEY_H)
                color = self.finger_colors.get(finger, theme.COLOR_LOCKED)
                pygame.draw.rect(self.base_layer, color, rect, border_radius=6)
                pygame.draw.rect(self.base_layer, theme.COLOR_TEXT, rect, width=2, border_radius=6)

                text = self.resources.text_surface(label, font, theme.COLOR_BUTTON_TEXT)
                self.base_layer.blit(text, text.get_rect(center=rect.center))

                if char is not None:
                    self.key_rects[char] = rect
                x += key_w + GAP
            y += KEY_H + GAP

    # --- guidance ----------------------------------------------------------

    def highlight_expected(self, char) -> None:
        """Point at the key the student should press **next** (FR-092).

        `None` (lesson finished, or a character the board cannot show) clears the
        guidance rather than leaving the previous key lit, which would invite one
        more keystroke or point at the wrong key.
        """
        self._expected_char = char
        entry = CHAR_TO_KEY.get(char) if char is not None else None

        if entry is None:
            self._active_key = self._active_shift = self._active_finger = None
            self._caption_surf = None
            return

        self._active_key = entry[0]
        self._active_shift = shift_side_for(char)
        self._active_finger = finger_for(char)
        self._caption_surf = None

    #: Kept so any older call site still works; guidance is what matters now.
    def highlight(self, key, finger=None) -> None:
        self.highlight_expected(key)

    @property
    def expected_finger_label(self):
        return FINGER_LABELS.get(self._active_finger)

    def dirty_rect(self) -> pygame.Rect:
        """Rectangle covering the keyboard body plus the caption drawn above it.

        Used by LessonScene to mark the right region dirty when guidance changes.
        """
        width, height = self.size()
        y = max(0, self.origin[1] - theme.FONT_SIZE_BODY - 8)
        return pygame.Rect(self.origin[0], y, width, height + self.origin[1] - y)

    @property
    def active_keys(self):
        """The keys currently outlined — the base key plus a Shift if needed."""
        return tuple(k for k in (self._active_key, self._active_shift) if k)

    # --- rendering ---------------------------------------------------------

    def render(self, surface) -> None:
        if self.base_layer is None:
            self.prerender()
        surface.blit(self.base_layer, self.origin)

        for key in self.active_keys:
            if key in self.key_rects:
                rect = self.key_rects[key].move(self.origin)
                pygame.draw.rect(surface, theme.COLOR_ACCENT, rect, width=4, border_radius=6)

        self._render_caption(surface)

    def _render_caption(self, surface) -> None:
        """Name the key and the finger in words (FR-093)."""
        if self._active_finger is None:
            return

        if self._caption_surf is None:
            font = self.resources.font(theme.FONT_DEFAULT, theme.FONT_SIZE_BODY)
            shown = "Space" if self._expected_char == " " else self._expected_char
            label = self.expected_finger_label
            # "use your either thumb" is not English. The thumb label already reads
            # as a complete phrase, so it takes no possessive.
            phrase = (f"use {label}" if label.startswith("either")
                      else f"use your {label}")
            parts = [f"Next: {shown}", phrase]
            if self._active_shift:
                side = "right" if self._active_shift == "RSHIFT" else "left"
                parts.append(f"hold {side} Shift")
            self._caption_surf = self.resources.text_surface(
                " - ".join(parts), font, theme.COLOR_TEXT)

        y = max(0, self.origin[1] - theme.FONT_SIZE_BODY - 8)
        surface.blit(self._caption_surf, self._caption_surf.get_rect(midleft=(self.origin[0], y)))
