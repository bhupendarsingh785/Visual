"""Memory store for last heard statement - persists across screen off/on."""
import json
import os

MEMORY_FILE = os.path.join(os.path.expanduser("~"), ".visual", "last_statement.json")


class MemoryStore:
    def __init__(self):
        self._last = None
        self._load()

    def _load(self):
        try:
            if os.path.exists(MEMORY_FILE):
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._last = data.get("last_statement")
        except Exception:
            self._last = None

    def _save(self):
        try:
            os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_statement": self._last}, f, ensure_ascii=False)
        except Exception:
            pass

    def store_last(self, text: str):
        """Pichhli baat save karein."""
        self._last = text
        self._save()

    def recall_last(self):
        """Pichhli baat lautayein."""
        return self._last

    def clear(self):
        self._last = None
        self._save()


# Global instance
store = MemoryStore()