"""Memory Repeat Plugin - handles storing last statement and repeating on 'dohrao' command."""
import os
import json

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_statement.json")

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
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_statement": self._last}, f, ensure_ascii=False)
        except Exception:
            pass

    def store_last(self, text: str):
        """Pichhli baat ko store karein."""
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

@tool("Pichhla user statement memory mein save karo.", {"text": S("statement to remember")})
def store_last(text: str) -> str:
    """Pichhli baat ko store karein."""
    store.store_last(text)
    return f"Statement saved: {text}"

@tool("Aakhri saved user statement wapas lao.")
def recall_last() -> str:
    """Pichhli baat lautayein."""
    last = store.recall_last()
    if last is None:
        return "Abhi tak kuch nahi suna, boss."
    return last

@tool("User ke 'dohrao' kehne par aakhri statement repeat karo.")
def handle_dohrao() -> str:
    """'dohrao' command par pichhli baat repeat karein."""
    return recall_last()