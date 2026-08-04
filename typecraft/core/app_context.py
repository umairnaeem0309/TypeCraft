"""core/app_context.py — holds the manager singletons every scene reads from."""

from typecraft.core.paths import ensure_seeded
from typecraft.managers.database import Database
from typecraft.managers.profile_manager import ProfileManager
from typecraft.managers.lesson_manager import LessonManager
from typecraft.managers.progression import ProgressionService
from typecraft.managers.badge_manager import BadgeManager
from typecraft.managers.streak_manager import StreakManager
from typecraft.managers.config_manager import ConfigManager
from typecraft.managers.sync_manager import SyncManager
from typecraft.ui.resource_manager import ResourceManager
from typecraft.ui.audio_manager import AudioManager


class AppContext:
    def __init__(self):
        ensure_seeded(["lessons.json", "badges.json", "messages.json", "settings.json"])

        self.db = Database()
        self.sync = SyncManager(self.db)
        self.resources = ResourceManager()
        self.audio = AudioManager(self.resources)
        self.config = ConfigManager()

        # FR-130: the stored sound settings are the ones the classroom last chose.
        # Applying them here is what makes them mean anything — before this, a muted
        # machine came back unmuted every launch.
        self.audio.set_volume(self.config.get("volume", 0.7))
        self.audio.set_muted(self.config.get("muted", False))

        #: Teacher-facing problems found at startup, shown in the UI (FR-024, FR-134).
        self.notices = list(self.config.warnings)

        self.lessons = LessonManager(self.db)
        self.lessons.load_file()
        self.notices.extend(self.lessons.warnings)

        self.profiles = ProfileManager(self.db, lesson_manager=self.lessons)
        self.badges = BadgeManager(self.db, self.lessons)
        self.streak = StreakManager(self.db)
        self.progression = ProgressionService(
            self.db, self.lessons, self.badges, self.streak, self.profiles,
            on_badge_awarded=lambda: self.audio.play("badge.wav"),
        )

        self.active_profile = None
