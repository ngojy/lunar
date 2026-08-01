"""
Research Specialist Agent
Responsibilities:
  - Synthesize information from retrieval results
  - Answer research-oriented questions
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from memory_integration import summarize_retrieval_results, truncate_text
from agents.utils import timed_invoke


RESEARCH_SYSTEM = """You are a research specialist in a multi-agent system.
Analyze the task and the available information (retrieval results, reasoning plan) 
to provide comprehensive research findings.

Synthesize the information into clear, factual findings that answer the core question.
Be analytical and reference the sources where appropriate."""


def research_specialist_node(state: AgentState) -> AgentState:
    """Execute research specialist node for parallel execution."""
    
    # Resolve model
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    specialist_model = resolve_model("research_specialist", request_model, agent_settings)
    
    llm = ChatOllama(
        model=specialist_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )
    
    # Build research context
    context_parts = [f"Task: {truncate_text(state['task'], 800)}"]
    
    if state.get("retrieval_results"):
        context_parts.append("Retrieved Information:")
        for result in summarize_retrieval_results(state["retrieval_results"], max_items=3):
            context_parts.append(f"  - {result.get('title', 'N/A')}: {result.get('content', '')}")
    
    if state.get("reasoning_plan"):
        context_parts.append(f"Reasoning Plan: {truncate_text(state['reasoning_plan'], 700)}")
    
    context_message = "\n\n".join(context_parts)
    
    response = timed_invoke(
        llm,
        [
            SystemMessage(content=RESEARCH_SYSTEM),
            HumanMessage(content=context_message),
        ],
        "Research Specialist analyzing",
        show_completion=True,
    )
    
    specialist_output = response.content.strip()
    
    print(f"  Research Specialist: {len(specialist_output)} chars")
    
    # Update specialist_results
    specialist_results = state.get("specialist_results", {})
    specialist_results["research"] = specialist_output
    
    return {
        **state,
        "specialist_results": specialist_results,
        "messages": [
            *state.get("messages", []),
            {
                "role": "research_specialist",
                "content": specialist_output,
            },
        ],
    }
