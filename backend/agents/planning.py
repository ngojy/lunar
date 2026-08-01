"""
Planning/Reasoning Agent
Responsibilities:
  - Break down complex tasks into steps
  - Create reasoning plan for specialists to follow
  - Only invoked if router.needs_reasoning = True
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from memory_integration import truncate_text


PLANNING_SYSTEM = """You are a planning agent in a multi-agent system. Your job is to break down complex tasks into clear, actionable steps.

Create a structured plan that specialists can follow to solve the task. Include:
1. Task analysis (what exactly is being asked)
2. Required steps in order
3. Key decisions or branching points
4. Expected output for each step

Be concise but comprehensive."""


def planning_node(state: AgentState) -> AgentState:
    """Create reasoning plan for complex tasks."""
    
    # Resolve model for planner
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    planner_model = resolve_model("planner", request_model, agent_settings)
    
    # Create LLM with resolved model
    llm = ChatOllama(
        model=planner_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )
    
    response = llm.invoke([
        SystemMessage(content=PLANNING_SYSTEM),
        HumanMessage(content=f"Task: {truncate_text(state['task'], 800)}"),
    ])
    
    reasoning_plan = response.content.strip()
    
    print(f"\n  Reasoning Plan Created:")
    print(f"    {truncate_text(reasoning_plan, 200)}")
    
    return {
        **state,
        "reasoning_plan": reasoning_plan,
        "messages": [
            *state.get("messages", []),
            {
                "role": "planner",
                "content": reasoning_plan,
            },
        ],
    }
