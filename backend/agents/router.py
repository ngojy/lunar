"""
Fast Router Agent
Responsibilities:
  - Analyze user task with full session context
  - Determine which capabilities are needed (retrieval, tools, specialists)
  - Make intelligent routing decisions with minimal latency
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from memory_integration import compact_messages, truncate_text
import json


ROUTER_SYSTEM = """You are a fast router in a multi-agent system. Your job is to analyze the user's task and determine which capabilities are needed.

You have access to:
- Retrieval: Search for external information (web, documents)
- Tools: Use available APIs and tools
- Specialists:
  * Research: Synthesize information from multiple sources
  * Coding: Generate and execute code
  * Math: Solve mathematical problems
  * Vision: Analyze images (if needed)

Based on the task and conversation history, decide:
1. Do we need external information retrieval? (needs_retrieval: true/false)
2. Do we need to check available tools? (needs_tools: true/false)
3. Which specialists should we invoke? (specialist_types: list of ["research", "coding", "math", "vision"] or empty)
4. Does the task need complex reasoning/planning? (needs_reasoning: true/false)
5. Will the final result need synthesis from multiple sources? (needs_synthesis: true/false)

Respond ONLY with valid JSON (no markdown, no explanation):
{
  "needs_retrieval": boolean,
  "needs_tools": boolean,
  "specialist_types": [],
  "needs_reasoning": boolean,
  "needs_synthesis": boolean,
  "reasoning": "brief explanation of routing decision"
}
"""


def router_node(state: AgentState) -> AgentState:
    """Route the task to appropriate capabilities."""
    
    # Resolve model for router
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    router_model = resolve_model("router", request_model, agent_settings)
    
    # Create LLM with resolved model
    llm = ChatOllama(
        model=router_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )
    
    # Build context message with session history
    context_parts = []
    
    if state.get("session_context"):
        context_parts.append(f"Session Context:\n{truncate_text(state['session_context'], 500)}")
    
    if state.get("conversation_history"):
        recent_history = compact_messages(state["conversation_history"], max_messages=4, max_chars=160)
        if recent_history:
            context_parts.append("Recent Conversation:")
            for msg in recent_history:
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                context_parts.append(f"{role}: {content}")
    
    context_parts.append(f"Current Task: {state['task']}")
    
    context_message = "\n\n".join(context_parts)
    
    # Call LLM to get routing decision
    response = llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=context_message),
    ])
    
    # Parse JSON response
    try:
        router_decision = json.loads(response.content.strip())
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        router_decision = {
            "needs_retrieval": False,
            "needs_tools": False,
            "specialist_types": [],
            "needs_reasoning": False,
            "needs_synthesis": False,
            "reasoning": "Parse error, using safe defaults"
        }
    
    # Extract decision flags
    needs_retrieval = router_decision.get("needs_retrieval", False)
    needs_tools = router_decision.get("needs_tools", False)
    specialist_types = router_decision.get("specialist_types", [])
    needs_reasoning = router_decision.get("needs_reasoning", False)
    needs_synthesis = router_decision.get("needs_synthesis", False)
    
    print(f"\n  Router Decision:")
    print(f"    Retrieval: {needs_retrieval}")
    print(f"    Tools: {needs_tools}")
    print(f"    Specialists: {specialist_types}")
    print(f"    Reasoning: {needs_reasoning}")
    print(f"    Synthesis: {needs_synthesis}")
    
    return {
        **state,
        "router_decision": router_decision,
        "needs_retrieval": needs_retrieval,
        "needs_tools": needs_tools,
        "specialist_types": specialist_types,
        "needs_reasoning": needs_reasoning,
        "needs_synthesis": needs_synthesis,
        "messages": [
            *state.get("messages", []),
            {
                "role": "router",
                "content": f"Decision: {router_decision.get('reasoning', '')}",
            },
        ],
    }
