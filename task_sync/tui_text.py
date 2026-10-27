"""Text helpers for the interface."""

def escape(text: str) -> str:
    """Show remote text as typed. Titles come from other people's lists and from your own habits ("[WIP] fix", "Notes [2026]"):
    Textual's markup would swallow or choke on every [..], so every [ is escaped."""
    return (text or "").replace("\\", "\\\\").replace("[", "\\[")
