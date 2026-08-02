"""
Critic agent (Phase 3)
Responsibilities:
  - Conditionally review specialist results
  - Identify gaps, errors, or weak reasoning
  - Provide improvement suggestions (no automatic iterations)
  - Only invoked on: code generation, multiple specialists, failures, explicit requests
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from memory_integration import summarize_retrieval_results, truncate_text
from agents.utils import timed_invoke


# Prompt
CRITIC_SYSTEM = """You are a rigorous critic in a multi-agent AI system.
Your job is to review the work and identify any issues or improvements.

For each issue found, note:
  1. What is missing or incorrect
  2. How severe it is (minor / major / critical)
  3. What could be improved

Format your response as:
VERDICT: [PASS/NEEDS_IMPROVEMENT/CRITICAL]
FEEDBACK: [Brief summary of findings]
SUGGESTIONS:
- [Suggestion 1]
- [Suggestion 2]
- [Suggestion 3]

If the work is complete and correct, respond with:
VERDICT: PASS
FEEDBACK: The response is complete and accurate.
SUGGESTIONS:
"""


def should_critique(state: AgentState) -> bool:
    """
    Determine if critique should run.
    Only invoke on specific conditions (Phase 3).
    """
    # Explicit user request
    if state.get("metadata", {}).get("request_critique", False):
        return True
    
    # Auto-critique disabled
    if not state.get("metadata", {}).get("auto_critique", True):
        return False
    
    specialist_results = state.get("specialist_results", {})
    
    # Code generation: always critique
    if "coding" in specialist_results:
        return True
    
    # Multiple specialists ran: critique synthesis
    if len(specialist_results) > 1:
        return True
    
    # Check for failure signals
    coding_result = specialist_results.get("coding", "")
    if "error" in coding_result.lower() or "exception" in coding_result.lower():
        return True
    
    # Default: no critique needed
    return False


def parse_critique(critique_text: str) -> tuple[str, str, list[str]]:
    """
    Parse critique response into verdict, feedback, and suggestions.
    Returns: (verdict, feedback, suggestions_list)
    """
    lines = critique_text.strip().split("\n")
    verdict = "UNKNOWN"
    feedback = ""
    suggestions = []
    
    in_suggestions = False
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("VERDICT:"):
            verdict = line.replace("VERDICT:", "").strip()
        elif line.startswith("FEEDBACK:"):
            feedback = line.replace("FEEDBACK:", "").strip()
        elif line.startswith("SUGGESTIONS:"):
            in_suggestions = True
        elif in_suggestions and line.startswith("-"):
            suggestion = line.replace("-", "").strip()
            if suggestion:
                suggestions.append(suggestion)
    
    return verdict, feedback, suggestions


# Node
def critic_node(state: AgentState) -> AgentState:
    """Review specialist results and provide critique."""

    # Resolve model for critic
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    critic_model = resolve_model("critic", request_model, agent_settings)
    
    # Create LLM with resolved model
    llm = ChatOllama(
        model=critic_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )

    # Build context for critique
    parts = [f"Task: {truncate_text(state['task'], 800)}"]
    
    specialist_results = state.get("specialist_results", {})
    for specialist_type, result in specialist_results.items():
        # Truncate long results
        truncated = truncate_text(result, 500)
        parts.append(f"{specialist_type.upper()} Result:\n{truncated}")
    
    # Include retrieval results if available
    retrieval_results = state.get("retrieval_results", [])
    if retrieval_results:
        parts.append("Retrieved Information:")
        for result in summarize_retrieval_results(retrieval_results, max_items=3):
            title = result.get("title", "N/A")
            parts.append(f"  - {title}")

    response = timed_invoke(
        llm,
        [
            SystemMessage(content=CRITIC_SYSTEM),
            HumanMessage(content="\n\n".join(parts)),
        ],
        "Critic reviewing results",
        show_completion=True,
    )

    critique_text = response.content.strip()
    verdict, feedback, suggestions = parse_critique(critique_text)
    
    print(f"  Critic verdict: {verdict}")
    if suggestions:
        print(f"    Suggestions: {len(suggestions)} items")

    return {
        **state,
        "critique_performed": True,
        "critique_feedback": feedback,
        "critique_suggestions": suggestions,
        "messages": [
            *state.get("messages", []),
            {
                "role": "critic",
                "content": f"{verdict}: {feedback}",
            },
        ],
    }
