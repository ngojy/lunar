"""
Tool definitions available to agents.

Web search priority:
  1. Tavily     — best quality, 1000 free searches/month (requires TAVILY_API_KEY)
  2. DuckDuckGo — completely free, no API key needed (automatic fallback)

Add new tools here and import them into the relevant agent.
"""

import os
from dotenv import load_dotenv
from langchain_tavily import TavilySearch
from langchain_experimental.tools import PythonREPLTool
from langchain.tools import tool

load_dotenv()

tavily_api_key = os.getenv("TAVILY_API_KEY", "")


# Web search
if tavily_api_key:
    from langchain_tavily import TavilySearch
 
    def get_search_tool(max_results: int = 5):
        """Return a configured Tavily web-search tool."""
        print("[tools] Using Tavily search")
        return TavilySearch(api_key=tavily_api_key, max_results=max_results)
else:
    from langchain_community.tools import DuckDuckGoSearchRun
    def get_search_tool(max_results: int = 5):
        """Return DuckDuckGo search tool — free fallback."""
        print("[tools] Tavily key not found — using DuckDuckGo")
        return DuckDuckGoSearchRun()


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