"""VISUAL memory-repeat tools backed by the shared persistent MemoryStore."""
from memory_store import store

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