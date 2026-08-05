"""
Coding Specialist Agent
Responsibilities:
  - Generate and execute Python code
  - Solve computational problems
"""

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config, resolve_model
from tools import get_python_repl_tool
from memory_integration import truncate_text
from agents.utils import timed_invoke
import time

_repl = get_python_repl_tool()

CODE_SYSTEM = """You are a coding specialist in a multi-agent system.
Generate Python code to solve the given task.

Requirements:
- Use only standard library unless task requires specific packages
- Always print final results to stdout
- Keep code concise and correct
- Return ONLY raw Python code, no markdown, no explanation"""


def coding_specialist_node(state: AgentState) -> AgentState:
    """Execute coding specialist node for parallel execution."""
    
    # Resolve model
    request_model = state.get("metadata", {}).get("model")
    agent_settings = state.get("agent_model_settings", {})
    specialist_model = resolve_model("coding_specialist", request_model, agent_settings)
    
    llm = ChatOllama(
        model=specialist_model or config.model,
        temperature=config.temperature,
        base_url=config.ollama_host,
        extra_body={"think": False},
    )
    
    # Build coding context
    context_parts = [f"Task: {truncate_text(state['task'], 800)}"]
    
    if state.get("reasoning_plan"):
        context_parts.append(f"Reasoning Plan: {truncate_text(state['reasoning_plan'], 700)}")
    
    if state.get("available_tools"):
        context_parts.append("Available Tools:")
        for tool in state["available_tools"]:
            context_parts.append(f"  - {tool['name']}: {tool['description']}")
    
    context_message = "\n\n".join(context_parts)
    
    code_response = timed_invoke(
        llm,
        [
            SystemMessage(content=CODE_SYSTEM),
            HumanMessage(content=context_message),
        ],
        "Coding Specialist generating code",
        show_completion=True,
    )
    
    code = code_response.content.strip()
    
    # Strip markdown fences if present
    if code.startswith("```"):
        lines = code.splitlines()
        code = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )
    
    # Execute code
    print("  Executing code...")
    start = time.time()
    try:
        output = _repl.invoke(code)
        elapsed = time.time() - start
        print(f"  ✓  Code executed successfully  {elapsed:.2f}s")
    except Exception as e:
        output = f"[Execution error: {e}]"
        elapsed = time.time() - start
        print(f"  ✗  Execution error after {elapsed:.2f}s: {e}")
    
    specialist_output = f"Code:\n{code}\n\nOutput:\n{output}"
    
    # Update specialist_results
    specialist_results = state.get("specialist_results", {})
    specialist_results["coding"] = specialist_output
    
    return {
        **state,
        "specialist_results": specialist_results,
        "messages": [
            *state.get("messages", []),
            {
                "role": "coding_specialist",
                "content": specialist_output,
            },
        ],
    }
