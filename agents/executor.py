"""
Executor agent
Responsibilities:
  - Write Python code to solve the computational part of the task
  - Run the code in a sandboxed REPL
  - Store stdout / result in shared state
"""

import sys
import time
import threading
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config
from tools import get_python_repl_tool

# ── LLM
# think=True — writing correct code benefits from step-by-step reasoning
_llm = ChatOllama(
    model=config.model,
    temperature=config.temperature,
    extra_body={"think": True},
)

_repl = get_python_repl_tool()

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
CODE_SYSTEM = """You are a Python expert.
Write a self-contained Python script that solves the task below.
- Use only the standard library unless the task explicitly requires third-party packages.
- Always print the final result to stdout.
- Keep the code concise and correct.
- Return ONLY the raw Python code, no markdown fences, no explanation."""

# ── Node
def executor_node(state: AgentState) -> AgentState:
    """Generate Python code for the task and execute it."""

    context_parts = [f"Task: {state['task']}"]
    if state.get("research_results"):
        context_parts.append("Available research:\n" + "\n".join(state["research_results"]))

    code_response = _timed_invoke(
        _llm,
        [
            SystemMessage(content=CODE_SYSTEM),
            HumanMessage(content="\n\n".join(context_parts)),
        ],
        "Executor writing code",
    )

    code = code_response.content.strip()

    # Strip accidental markdown fences
    if code.startswith("```"):
        lines = code.splitlines()
        code = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    # Run the code
    print("  Running code...")
    start = time.time()
    try:
        output = _repl.invoke(code)
        elapsed = time.time() - start
        print(f"  ✓  Code executed  {elapsed:.2f}s")
    except Exception as e:
        output = f"[Execution error: {e}]"
        print(f"  ✗  Execution error: {e}")

    result_entry = f"Code:\n{code}\n\nOutput:\n{output}"
    existing = state.get("execution_results", [])

    return {
        **state,
        "execution_results": existing + [result_entry],
        "messages": [{"role": "executor", "content": "Code executed."}],
    }