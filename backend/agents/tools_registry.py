"""
Tools Registry Agent
Responsibilities:
  - Catalog available tools for the task
  - Return tool descriptions and usage info
  - Only invoked if router.needs_tools = True
"""

from state import AgentState


def tools_registry_node(state: AgentState) -> AgentState:
    """Catalog available tools for specialists."""
    
    # Define available tools
    available_tools = [
        {
            "name": "web_search",
            "description": "Search the web via Tavily first, with DuckDuckGo fallback",
            "parameters": ["query"],
        },
        {
            "name": "execute_python",
            "description": "Execute Python code and get results",
            "parameters": ["code"],
        },
        {
            "name": "execute_bash",
            "description": "Execute bash commands",
            "parameters": ["command"],
        },
        {
            "name": "math_solver",
            "description": "Solve mathematical equations",
            "parameters": ["equation"],
        },
    ]
    
    # Filter tools based on task if needed
    task_lower = state.get("task", "").lower()
    
    filtered_tools = []
    
    if any(word in task_lower for word in ["search", "web", "find", "look"]):
        filtered_tools.append(available_tools[0])  # web_search
    
    if any(word in task_lower for word in ["code", "python", "execute", "run"]):
        filtered_tools.append(available_tools[1])  # execute_python
        filtered_tools.append(available_tools[2])  # execute_bash
    
    if any(word in task_lower for word in ["math", "calculate", "solve", "equation"]):
        filtered_tools.append(available_tools[3])  # math_solver
    
    # If no specific matches, include all tools
    if not filtered_tools:
        filtered_tools = available_tools
    
    print(f"\n  Tools Available: {len(filtered_tools)} tools")
    for tool in filtered_tools:
        print(f"    - {tool['name']}: {tool['description']}")
    
    return {
        **state,
        "available_tools": filtered_tools,
        "messages": [
            *state.get("messages", []),
            {
                "role": "tools_registry",
                "content": f"Cataloged {len(filtered_tools)} available tools",
            },
        ],
    }
