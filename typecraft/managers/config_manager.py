"""managers/config_manager.py — settings.json (writable) with a hashed
teacher PIN. Never stores the PIN in plaintext.

Loading must never be able to stop the app from starting (FR-134). settings.json
sits in a folder a teacher can open in Notepad, and it is the one file whose
corruption would otherwise lock a whole class out of the software — so a malformed
or partially-edited file falls back to the bundled defaults, records a warning for
the UI, and logs the reason.
"""

import hashlib
import hmac
import json
import os
import secrets

from typecraft.core.logging_setup import get_logger
from typecraft.core.paths import resource_path, writable_data_dir

log = get_logger(__name__)

#: Last-resort values if even the bundled default is unreadable.
FALLBACK = {"volume": 0.7, "muted": False, "teacher_pin_hash": None}

#: PIN hashing (SR-002). A 4-digit PIN has only 10 000 possible values, so a bare
#: digest is equivalent to storing the PIN itself — all 10 000 can be hashed in
#: milliseconds. PBKDF2 with a per-install random salt makes that sweep cost about
#: 10 000 x 200 000 SHA-256 operations instead, and means two schools that pick the
#: same PIN do not produce the same stored hash.
PBKDF2_ROUNDS = 200_000
SALT_BYTES = 16
HASH_PREFIX = "pbkdf2_sha256"


class ConfigManager:
    def __init__(self):
        self.path = writable_data_dir() / "settings.json"
        #: Human-readable problems found while loading, for the UI to show (FR-134).
        self.warnings = []
        self._data = self._load()

    # --- loading -----------------------------------------------------------

    def _bundled_defaults(self) -> dict:
        try:
            with open(resource_path("data/settings.default.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**FALLBACK, **data}
        except (OSError, json.JSONDecodeError, ValueError):
            log.warning("bundled settings.default.json is unreadable; using built-in defaults")
            return dict(FALLBACK)

    def _load(self) -> dict:
        defaults = self._bundled_defaults()

        if not self.path.exists():
            self._write(defaults)
            return defaults

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"expected a JSON object, found {type(data).__name__}")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            # Deliberately do NOT overwrite the file: the teacher needs it intact to
            # see their mistake, exactly as with a broken lessons.json. The next
            # successful set() heals it.
            self.warnings.append(
                f"settings.json could not be read ({exc}). Default sound settings are in "
                "use and the teacher PIN may need setting again."
            )
            log.warning("settings.json rejected (%s): %s", self.path, exc)
            return defaults

        # A partially-edited file keeps whatever is valid and fills the rest in, so
        # deleting one line cannot blank out the others.
        merged = {**defaults, **data}
        return self._sanitise(merged)

    def _sanitise(self, data: dict) -> dict:
        """Coerce values into range. A hand-edited "volume": 11 must not reach
        pygame.mixer, and "muted": "no" must not read as true."""
        try:
            volume = float(data.get("volume", FALLBACK["volume"]))
        except (TypeError, ValueError):
            self.warnings.append("settings.json had an invalid volume; using the default.")
            log.warning("invalid volume %r in settings.json", data.get("volume"))
            volume = FALLBACK["volume"]
        data["volume"] = max(0.0, min(1.0, volume))

        muted = data.get("muted", False)
        if not isinstance(muted, bool):
            self.warnings.append("settings.json had an invalid mute setting; using the default.")
            log.warning("invalid muted %r in settings.json", muted)
            muted = False
        data["muted"] = muted

        return data

    # --- writing -----------------------------------------------------------

    def _write(self, data: dict) -> None:
        """Write atomically (FR-135).

        A plain open-and-write truncates the file first, so a power cut in that
        window leaves an empty or half-written settings.json — losing the teacher's
        PIN. Writing a temporary file, flushing it to disk, then renaming over the
        original means a reader only ever sees the old file or the new one.
        """
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)      # atomic on Windows and POSIX

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self._write(self._data)

    # --- teacher PIN -------------------------------------------------------

    def _hash(self, raw: str, salt: bytes = None) -> str:
        """`pbkdf2_sha256$rounds$salt_hex$digest_hex` (SR-002)."""
        salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, PBKDF2_ROUNDS)
        return f"{HASH_PREFIX}${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"

    def verify_pin(self, raw: str) -> bool:
        """Constant-time comparison (SR-003), with a one-time upgrade path.

        A PIN set by an earlier build is a bare unsalted SHA-256 hex digest. Rather
        than locking that teacher out, it is accepted once and immediately re-hashed
        with the current scheme, so the weak digest disappears from disk the first
        time the PIN is used.
        """
        stored = self._data.get("teacher_pin_hash")
        if not stored or not isinstance(stored, str):
            return False

        if stored.startswith(HASH_PREFIX + "$"):
            try:
                _, rounds, salt_hex, digest_hex = stored.split("$")
                expected = hashlib.pbkdf2_hmac(
                    "sha256", raw.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
            except (ValueError, TypeError):
                log.warning("teacher_pin_hash in settings.json is malformed")
                return False
            return hmac.compare_digest(expected.hex(), digest_hex)

        # Legacy unsalted SHA-256.
        legacy = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if hmac.compare_digest(legacy, stored):
            log.info("upgrading the stored teacher PIN to %s", HASH_PREFIX)
            self.set_pin(raw)
            return True
        return False

    def set_pin(self, raw: str) -> None:
        self.set("teacher_pin_hash", self._hash(raw))

    def has_pin(self) -> bool:
        return bool(self._data.get("teacher_pin_hash"))
