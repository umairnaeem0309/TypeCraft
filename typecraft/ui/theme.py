"""ui/theme.py — colours, sizes, fonts. The one place to restyle TypeCraft."""

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 30

# Standard vertical rhythm (avoids arbitrary y-values scattered across scenes)
LAYOUT_TITLE_Y = 70
LAYOUT_SUBTITLE_Y = 110

#: Height of the footer band at the bottom of a screen. Tall enough for body-sized
#: text with breathing room — the hint used to be a small line 40 px from the
#: bottom, which the keyboard then overlapped by 5 px.
LAYOUT_FOOTER_HEIGHT = 64
#: Clear space kept between the keyboard and the footer band.
LAYOUT_FOOTER_MARGIN = 20

COLOR_BG = (245, 247, 250)
COLOR_TEXT = (30, 30, 40)
COLOR_TEXT_MUTED = (120, 125, 135)
COLOR_PRIMARY = (76, 175, 80)              # Main action / Play / Confirm
COLOR_PRIMARY_DARK = (56, 142, 60)           # Used sparingly for pressed/dark accents
COLOR_ACCENT = (33, 150, 243)                # Leaderboard / secondary actions
COLOR_ADMIN = (121, 85, 72)                  # Teacher Dashboard (distinct from primary)
COLOR_WARNING = (255, 152, 0)                 # Caution / optional modes
COLOR_NEUTRAL = (120, 125, 135)              # Settings / back / cancel
COLOR_ERROR = (229, 57, 53)                  # Quit / reset / danger
COLOR_CORRECT = (76, 175, 80)
COLOR_PENDING = (150, 150, 160)
COLOR_CARD_BG = (255, 255, 255)
COLOR_CARD_SHADOW = (0, 0, 0, 40)
COLOR_LOCKED = (200, 200, 205)
COLOR_BUTTON_TEXT = (255, 255, 255)

FONT_DEFAULT = "default"
FONT_SIZE_TITLE = 56
FONT_SIZE_HEADING = 36
FONT_SIZE_BODY = 28
FONT_SIZE_SMALL = 22
FONT_SIZE_TARGET_TEXT = 40

FINGER_COLORS = {
    "left_pinky": (244, 67, 54),
    "left_ring": (255, 152, 0),
    "left_middle": (255, 235, 59),
    "left_index": (139, 195, 74),
    "right_index": (0, 188, 212),
    "right_middle": (63, 81, 181),
    "right_ring": (156, 39, 176),
    "right_pinky": (233, 30, 99),
    # Space is typed with a thumb, so it needs a ninth colour distinct from the
    # eight fingers rather than being left uncoloured.
    "thumb": (120, 144, 156),
}
