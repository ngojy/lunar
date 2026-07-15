"""
Memory utilities.
- InMemoryHistory  : simple list-based store, good for single-session use
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from config import config

# In-memory message history

@dataclass
class InMemoryHistory:
    """Lightweight wrapper around a plain list of message dicts."""
    messages: list[dict[str, Any]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)

    def __repr__(self) -> str:  # pragma: no cover
        return f"InMemoryHistory({len(self)} messages)"