"""
Critic agent
Responsibilities:
  - Review research and execution results gathered so far
  - Identify gaps, errors, or weak reasoning
  - Write a structured critique that the orchestrator can use to decide
    whether to loop back for more work or proceed to FINISH
"""

import sys
import time
import threading
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from state import AgentState
from config import config

# ── LLM
# think=False — critic is doing a pass/fail check, not complex reasoning
_llm = ChatOllama(
    model=config.model,
    temperature=config.temperature,
    extra_body={"think": False},
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

# ── Prompt
CRITIC_SYSTEM = """You are a rigorous critic in a multi-agent AI system.
Your job is to review the work done so far and identify any issues.

For each issue, note:
  1. What is missing or incorrect
  2. How severe it is (minor / major)
  3. What the next agent should do to fix it
 
If the work is complete and correct, reply with exactly: LGTM
"""

# ── Node
def critic_node(state: AgentState) -> AgentState:
    """Review accumulated results and write a critique."""

    parts = [f"Task: {state['task']}"]
    if state.get("research_results"):
        parts.append("Research results:\n" + "\n".join(state["research_results"]))
    if state.get("execution_results"):
        parts.append("Execution results:\n" + "\n".join(state["execution_results"]))

    response = _timed_invoke(
        _llm,
        [
            SystemMessage(content=CRITIC_SYSTEM),
            HumanMessage(content="\n\n".join(parts)),
        ],
        "Critic reviewing results",
    )

    critique = response.content.strip()
    approved = critique.strip().upper() == "LGTM"
    print(f"  Critic verdict: {'✓ LGTM' if approved else '✗ needs more work'}")

    return {
        **state,
        "critique": critique,
        "messages": [{"role": "critic", "content": critique}],
    }