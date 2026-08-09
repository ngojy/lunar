"""
Synthesizer Agent
Responsibilities:
  - Combine results from multiple specialists
  - Merge retrieval, tools, and specialist outputs
  - Only invoked if router.needs_synthesis = True or multiple specialists produced output
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from memory_integration import summarize_retrieval_results, truncate_text


SYNTHESIZER_SYSTEM = """You are a synthesizer in a multi-agent system. Your job is to combine outputs from multiple specialists into a coherent, comprehensive response.

You will receive:
- Results from specialist agents (research, coding, math, vision)
- Retrieved information from search/RAG
- Available tools that were cataloged
- The original user task

Create a unified response that:
1. Incorporates insights from all specialists
2. References retrieved information appropriately
3. Explains the reasoning and approach taken
4. Provides a clear, actionable answer to the user's task

Be thorough but concise."""


def synthesizer_node(state: AgentState) -> AgentState:
    """Synthesize results from multiple sources."""
    
    # Resolve model for synthesizer
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    synthesizer_model = resolve_model("synthesizer", request_model, agent_settings)
    
    # Create LLM with resolved model
    llm = ChatOllama(
        model=synthesizer_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )
    
    # Build synthesis prompt with all available information
    synthesis_parts = [f"Task: {truncate_text(state['task'], 800)}"]
    
    # Include specialist results
    specialist_results = state.get("specialist_results", {})
    if specialist_results:
        synthesis_parts.append("Specialist Results:")
        for specialist_type, result in specialist_results.items():
            synthesis_parts.append(f"  {specialist_type.capitalize()}: {truncate_text(result, 700)}")
    
    # Include retrieval results
    retrieval_results = state.get("retrieval_results", [])
    if retrieval_results:
        synthesis_parts.append("Retrieved Information:")
        for result in summarize_retrieval_results(retrieval_results, max_items=3, max_chars=300):
            title = result.get("title", "N/A")
            content = result.get("content", "")
            synthesis_parts.append(f"  {title}: {content}")
    
    # Include reasoning plan if it exists
    if state.get("reasoning_plan"):
        synthesis_parts.append(f"Reasoning Plan Used: {truncate_text(state['reasoning_plan'], 700)}")
    
    synthesis_prompt = "\n\n".join(synthesis_parts)
    
    # Call LLM to synthesize
    response = llm.invoke([
        SystemMessage(content=SYNTHESIZER_SYSTEM),
        HumanMessage(content=synthesis_prompt),
    ])
    
    final_response = response.content.strip()
    
    print(f"\n  Synthesis Complete: {len(final_response)} characters")
    
    return {
        **state,
        "final_response": final_response,
        "synthesis_performed": True,
        "messages": [
            *state.get("messages", []),
            {
                "role": "synthesizer",
                "content": final_response,
            },
        ],
    }
