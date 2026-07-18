# modules/chat_memory.py
# Manages retrieval-aware chat history for the QA chain.
# Does NOT affect agent.py or app.py — add-only.

from collections import deque

class ChatMemory:
    """
    Lightweight rolling window of (user, assistant) turn pairs.
    Used to inject prior context into retrieval queries.
    """
    def __init__(self, max_turns: int = 5):
        self._history = deque(maxlen=max_turns)

    def add(self, user: str, assistant: str):
        self._history.append({"user": user, "assistant": assistant})

    def get_context_string(self) -> str:
        """Returns last N turns as a plain string for query augmentation."""
        if not self._history:
            return ""
        lines = []
        for turn in self._history:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
        return "\n".join(lines)

    def get_turns(self) -> list[dict]:
        return list(self._history)

    def clear(self):
        self._history.clear()


# Module-level singleton — shared across the QA chain session
report_memory = ChatMemory(max_turns=5)