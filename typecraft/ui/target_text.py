"""
ui/target_text.py

Layout for the text a student is typing (FR-100..FR-104).

What it replaces: a loop that blitted one glyph at a time, advanced `x`, and
wrapped when `x > max_width + 60`. Three problems with that, all visible to a
child:

  - it wrapped mid-word, so "practice" could become "practi" / "ce"
  - the `+ 60` meant the test fired only *after* the offending glyph had already
    been drawn past the right edge, so the last character on a line overhung the
    text area
  - the caret was drawn after `x` had advanced, so it sat to the right of the
    character it was supposed to mark

Layout is computed **once** per lesson entry and cached, because it never changes:
the target text is fixed for the whole attempt and only the per-character colours
move. Widths come from `font.size()`, which measures without rasterising, so
building the layout adds nothing to the text cache.
"""

import pygame

#: Space is drawn as a visible marker (FR-103) — a child cannot see how many spaces
#: a drill expects otherwise. Layout measures the *displayed* glyph, so the caret
#: and the text can never disagree about where a character sits.
SPACE_GLYPH = "·"

LINE_GAP = 10


def displayed(char: str) -> str:
    return SPACE_GLYPH if char == " " else char


class TargetTextLayout:
    """Fixed positions for every character of the target text.

    `glyphs` is a list of `(index, displayed_char, rect)` in screen coordinates.
    """

    def __init__(self, text: str, font, area, line_gap: int = LINE_GAP):
        self.text = text
        self.area = pygame.Rect(area)
        self.line_height = font.get_height() + line_gap
        self.glyphs = []
        self.lines = []
        self._build(font)

    # --- construction ------------------------------------------------------

    def _tokens(self):
        """Split the text into runs of `(start_index, characters)`, where a run is
        either one word or one space. Laying out whole tokens is what keeps words
        intact — the previous per-character loop had no concept of a word."""
        tokens = []
        i = 0
        while i < len(self.text):
            if self.text[i] == " ":
                tokens.append((i, " "))
                i += 1
            else:
                start = i
                while i < len(self.text) and self.text[i] != " ":
                    i += 1
                tokens.append((start, self.text[start:i]))
        return tokens

    def _build(self, font) -> None:
        widths = [font.size(displayed(ch))[0] for ch in self.text]

        x, y = self.area.x, self.area.y
        line = []

        def newline():
            nonlocal x, y, line
            self.lines.append([g[0] for g in line])
            line = []
            x, y = self.area.x, y + self.line_height

        def place(index, char):
            nonlocal x
            rect = pygame.Rect(x, y, widths[index], self.line_height)
            entry = (index, displayed(char), rect)
            line.append(entry)
            self.glyphs.append(entry)
            x += rect.width

        for start, token in self._tokens():
            token_width = sum(widths[start:start + len(token)])

            # Wrap *before* placing anything, so no glyph is ever positioned past
            # the right edge (FR-102). `line and` guards the case of a token wider
            # than the whole area, which must not loop forever.
            if line and x + token_width > self.area.right:
                newline()

            if token_width > self.area.width:
                # A single word longer than one line — a teacher can type anything,
                # so break it rather than run off the edge.
                for offset, char in enumerate(token):
                    if line and x + widths[start + offset] > self.area.right:
                        newline()
                    place(start + offset, char)
                continue

            for offset, char in enumerate(token):
                place(start + offset, char)

        if line:
            self.lines.append([g[0] for g in line])

    # --- queries -----------------------------------------------------------

    def rect_for(self, index: int):
        if 0 <= index < len(self.glyphs):
            # glyphs are appended in text order, so the index is the position.
            return self.glyphs[index][2]
        return None

    def caret_rect(self, cursor: int, width: int = 3) -> pygame.Rect:
        """A thin bar on the **left edge** of the character to be typed next.

        At the end of the text it sits just after the final glyph, so a finished
        attempt does not look as though one more character is expected.
        """
        rect = self.rect_for(cursor)
        if rect is not None:
            return pygame.Rect(rect.x, rect.y, width, rect.height)
        if self.glyphs:
            last = self.glyphs[-1][2]
            return pygame.Rect(last.right, last.y, width, last.height)
        return pygame.Rect(self.area.x, self.area.y, width, self.line_height)

    def bounds(self) -> pygame.Rect:
        """The smallest rect containing every glyph — used to assert nothing is
        laid out outside the text area."""
        if not self.glyphs:
            return pygame.Rect(self.area.x, self.area.y, 0, 0)
        rect = self.glyphs[0][2].copy()
        for _index, _char, glyph_rect in self.glyphs[1:]:
            rect.union_ip(glyph_rect)
        return rect

    def line_count(self) -> int:
        return len(self.lines)
