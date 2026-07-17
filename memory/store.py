"""
Memory utilities.
- InMemoryHistory  : simple list-based store, good for single-session use
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import os
from dotenv import load_dotenv

load_dotenv()


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


# Persistent checkpointer
def get_checkpointer():
    """
    Return a LangGraph SQLite checkpointer if persistence is enabled,
    otherwise return None.
    """
    enable = os.getenv("ENABLE_CHECKPOINTING", "false").lower() == "true"
 
    if not enable:
        return None
 
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        db = os.getenv("CHECKPOINT_DB", "checkpoints.db")
        return SqliteSaver.from_conn_string(db)
    except ImportError:
        print(
            "[memory] langgraph-checkpoint-sqlite not installed. "
            "Run: pip install langgraph-checkpoint-sqlite"
        )
        return None