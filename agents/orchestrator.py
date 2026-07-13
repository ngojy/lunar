"""
Orchestrator agent
Responsibilities:
  - Analyse the incoming task
  - Decide which specialist agent(s) to call and in what order
  - Assemble the final answer once specialists are done
  - Guard against infinite loops via the iteration counter
"""

import sys
import time
import threading
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config

# ── LLM
# think=False - routing needs a fast single-word reply, not a reasoning chain
_llm = ChatOllama(
    model=config.model,
    temperature=config.temperature,
    extra_body={"think": False},
)

_assembler_llm = ChatOllama(
    model=config.model,
    temperature=config.temperature,
    extra_body={"think": True},   # assembler benefits from careful reasoning
)

# ── Spinner
def _spin(label: str, stop_event: threading.Event, start: float):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    i = 0
    while not stop_event.is_set():
        elapsed = time.time() - start
        sys.stdout.write(f"\r  {frames[i % len(frames)]}  {label}  {elapsed:.1f}s ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1

def _timed_invoke(llm, messages, label: str):
    stop = threading.Event()
    start = time.time()
    t = threading.Thread(target=_spin, args=(label, stop, start), daemon=True)
    t.start()
    try:
        result = llm.invoke(messages)
    finally:
        stop.set()
        t.join()
        elapsed = time.time() - start
        sys.stdout.write(f"\r  ✓  {label}  {elapsed:.2f}s\n")
        sys.stdout.flush()
    return result

# ── Prompts
ROUTER_SYSTEM = """You are an orchestrator in a multi-agent system.
Your job is to analyse a task and decide which specialist agent should handle it next.

Available agents:
  - researcher  : searches the web and gathers information
  - executor    : writes and runs Python code to compute or transform data
  - critic      : reviews and improves a draft answer
  - FINISH      : the task is complete — compile the final answer

Rules:
  - Reply with ONLY one of: researcher, executor, critic, FINISH
  - Do not add explanation or punctuation
  - If you have enough information, go straight to FINISH
"""

ASSEMBLER_SYSTEM = """You are a senior analyst.
Given a task and all research/execution results collected so far, write a clear,
well-structured final answer for the user. Be concise but complete."""

# ── Nodes
def orchestrator_router(state: AgentState) -> AgentState:
    """Decide which agent runs next."""
    iteration = state.get("iteration", 0)

    # Hard stop to prevent runaway loops
    if iteration >= config.max_iterations:
        print(f"  ⚠  Max iterations ({config.max_iterations}) reached — forcing FINISH")
        return {**state, "next_agent": "FINISH", "iteration": iteration + 1}

    context_parts = [f"Task: {state['task']}"]
    if state.get("research_results"):
        context_parts.append(f"Research so far: {state['research_results']}")
    if state.get("execution_results"):
        context_parts.append(f"Execution results: {state['execution_results']}")
    if state.get("critique"):
        context_parts.append(f"Critique: {state['critique']}")

    messages = [
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content="\n".join(context_parts)),
    ]

    response = _timed_invoke(_llm, messages, f"Orchestrator routing  (iteration {iteration + 1})")
    next_agent = response.content.strip().lower()
 
    # Validate — fall back to FINISH on unexpected output
    valid = {"researcher", "executor", "critic", "finish"}
    if next_agent not in valid:
        print(f"  ⚠  Unexpected route '{next_agent}' — defaulting to FINISH")
        next_agent = "finish"

    return {
        **state,
        "next_agent": next_agent,
        "iteration": iteration + 1,
        "messages": [{"role": "orchestrator", "content": f"Routing to: {next_agent}"}],
    }

def orchestrator_assembler(state: AgentState) -> AgentState:
    """Compile all specialist results into the final answer."""
    parts = [f"Task: {state['task']}"]
    if state.get("research_results"):
        parts.append("Research:\n" + "\n".join(state["research_results"]))
    if state.get("execution_results"):
        parts.append("Execution:\n" + "\n".join(state["execution_results"]))
    if state.get("critique"):
        parts.append(f"Critique:\n{state['critique']}")
 
    messages = [
        SystemMessage(content=ASSEMBLER_SYSTEM),
        HumanMessage(content="\n\n".join(parts)),
    ]

    response = _timed_invoke(_assembler_llm, messages, "Assembling final answer")
    final_answer = response.content.strip()

    return {
        **state,
        "final_answer": final_answer,
        "messages": [{"role": "orchestrator", "content": "Final answer assembled."}],
    }