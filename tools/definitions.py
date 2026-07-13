"""
Tool definitions available to agents.

Tavily is used for web search (free tier: 1000 calls/month).
PythonREPL is a sandboxed code executor.

Add new tools here and import them into the relevant agent.
"""

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_experimental.tools import PythonREPLTool
from langchain.tools import tool
from config.settings import config

# ── Web search
def get_search_tool(max_results: int | None = None) -> TavilySearchResults:
    """Return a configured Tavily web-search tool."""
    return TavilySearchResults(
        max_results=max_results or config.max_research_results,
        tavily_api_key=config.tavily_api_key,
    )

# ── Code execution
def get_python_repl_tool() -> PythonREPLTool:
    """Return a sandboxed Python REPL tool."""
    return PythonREPLTool()

@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text."""
    return len(text.split())

@tool
def summarise_list(items: list[str]) -> str:
    """Join a list of strings into a numbered summary."""
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))

# ── Tool registry
ALL_TOOLS = [
    get_search_tool(),
    get_python_repl_tool(),
    word_count,
    summarise_list,
]