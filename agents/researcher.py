"""
Researcher agent
Responsibilities:
  - Formulate search queries based on the task
  - Execute web searches via Tavily (falls back gracefully if key is missing)
  - Summarise and filter results before storing them in shared state
"""

import sys
import time
import threading
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from state import AgentState
from config import config
from tools import get_search_tool

# ── LLM
# think=True — researcher benefits from reasoning through what to search for
_llm = ChatOllama(
    model=config.model,
    temperature=config.temperature,
    extra_body={"think": True},
)

_search: BaseTool = get_search_tool()

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
QUERY_SYSTEM = """You are a research assistant.
Given a task, generate 1-3 focused search queries that will retrieve the most
relevant information. Return ONLY the queries, one per line, no numbering."""

SUMMARISE_SYSTEM = """You are a research analyst.
Summarise the following search results into bullet-point findings relevant to
the task. Be factual and concise. Omit irrelevant results."""

# ── Node
def researcher_node(state: AgentState) -> AgentState:
    """Run web searches and append summarised findings to research_results."""
    # 1. Generate search queries
    query_response = _timed_invoke(
        _llm,
        [
            SystemMessage(content=QUERY_SYSTEM),
            HumanMessage(content=f"Task: {state['task']}"),
        ],
        "Researcher generating queries",
    )
    queries = [q.strip() for q in query_response.content.strip().splitlines() if q.strip()]
    print(f"  Queries: {queries[:3]}")

    # 2. Execute searches
    raw_results: list[str] = []
    for query in queries[:3]:
        print(f"  Searching: {query}")
        try:
            results = _search.invoke(query)
            if isinstance(results, list):
                for r in results:
                    snippet = r.get("content", "") if isinstance(r, dict) else str(r)
                    raw_results.append(snippet)
            else:
                raw_results.append(str(results))
        except Exception as e:
            raw_results.append(f"[Search error for '{query}': {e}]")

    # 3. Summarise
    summary_response = _timed_invoke(
        _llm,
        [
            SystemMessage(content=SUMMARISE_SYSTEM),
            HumanMessage(
                content=f"Task: {state['task']}\n\nRaw results:\n" + "\n---\n".join(raw_results)
            ),
        ],
        "Researcher summarising results",
    )
    summary = summary_response.content.strip()

    existing = state.get("research_results", [])
    return {
        **state,
        "research_results": existing + [summary],
        "messages": [{"role": "researcher", "content": f"Completed {len(queries)} searches."}],
    }