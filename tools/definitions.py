"""
Tool definitions available to agents.

Tavily is used for web search (free tier: 1000 calls/month).
PythonREPL is a sandboxed code executor.

Add new tools here and import them into the relevant agent.
"""

import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langchain_experimental.tools import PythonREPLTool
from langchain.tools import tool
from config.settings import config

load_dotenv()

tavily_api_key = os.getenv("TAVILY_API_KEY", "")


# Web search
if tavily_api_key:
    from langchain_tavily import TavilySearch
 
    def get_search_tool(max_results: int = 5):
        """Return a configured Tavily web-search tool."""
        return TavilySearch(api_key=tavily_api_key, max_results=max_results)
else:
    @tool
    def _dummy_search(query: str) -> str:
        """Search the web for information."""
        return "[Web search unavailable — add TAVILY_API_KEY to .env to enable it]"
 
    def get_search_tool(max_results: int = 5):
        return _dummy_search


# Code execution
def get_python_repl_tool() -> PythonREPLTool:
    """Return a sandboxed Python REPL tool."""
    return PythonREPLTool()


# Custom tools
@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text."""
    return len(text.split())

@tool
def summarise_list(items: list[str]) -> str:
    """Join a list of strings into a numbered summary."""
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


# Tool registry
ALL_TOOLS = [
    get_search_tool(),
    get_python_repl_tool(),
    word_count,
    summarise_list,
]