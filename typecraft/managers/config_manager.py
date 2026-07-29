"""managers/config_manager.py — settings.json (writable) with a hashed
teacher PIN. Never stores the PIN in plaintext."""

import hashlib
import json

from typecraft.core.paths import resource_path, writable_data_dir


class ConfigManager:
    def __init__(self):
        self.path = writable_data_dir() / "settings.json"
        if not self.path.exists():
            default_path = resource_path("data/settings.default.json")
            with open(default_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._write(data)
        with open(self.path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self._write(self._data)

    def _hash(self, raw: str) -> str:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_pin(self, raw: str) -> bool:
        stored = self._data.get("teacher_pin_hash")
        if not stored:
            return False
        return self._hash(raw) == stored

    def set_pin(self, raw: str) -> None:
        self.set("teacher_pin_hash", self._hash(raw))

    def has_pin(self) -> bool:
        return bool(self._data.get("teacher_pin_hash"))
