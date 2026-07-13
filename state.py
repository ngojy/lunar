"""
Shared state definition for the multi-agent system.
All agents read from and write to this TypedDict.
"""

from typing import Annotated, Any
from typing_extensions import TypedDict
import operator

class AgentState(TypedDict):
    # Accumulated message history (each agent appends, never overwrites)
    messages: Annotated[list[dict], operator.add]

    # The user's original task/request
    task: str

    # Which agent runs next (set by orchestrator)
    next_agent: str

    # Structured results from each specialist agent
    research_results: list[str]
    execution_results: list[str]
    critique: str

    # Final answer assembled by the orchestrator
    final_answer: str

    # Iteration counter to prevent infinite loops
    iteration: int

    # Arbitrary metadata agents can stash
    metadata: dict[str, Any]