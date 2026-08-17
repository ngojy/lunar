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

    # Session and Memory Context
    session_id: str
    conversation_history: list[dict]
    session_context: str

    # Router Decisions
    router_decision: dict[str, Any]
    needs_reasoning: bool
    needs_retrieval: bool
    needs_tools: bool
    specialist_types: list[str]
    needs_synthesis: bool

    # Planning (Optional)
    reasoning_plan: str

    # Parallel Capabilities Output
    retrieval_results: list[dict]
    available_tools: list[dict]
    specialist_results: dict[str, str]

    # Final Response
    final_response: str
    synthesis_performed: bool

    # Critic Control
    should_critique: bool
    critique_performed: bool
    critique_feedback: str
    critique_suggestions: list[str]

    # Arbitrary metadata agents can stash
    metadata: dict[str, Any]

    # Per-agent model overrides (agent_name -> model_string)
    agent_model_settings: dict[str, str]