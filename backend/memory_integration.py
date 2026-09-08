"""
Memory Integration Module
Responsibilities:
  - Load session context and conversation history
  - Retrieve relevant memory/context from previous interactions
  - Inject context into agent state
"""

from typing import Dict, List, Any, Optional

from state import AgentState
from config import config
from rag_hybrid import sqlite_manager


# Default user for session tracking (system user)
_DEFAULT_USER_ID = None


def _get_default_user_id() -> int:
    """Get or create default system user for session tracking."""
    global _DEFAULT_USER_ID
    if _DEFAULT_USER_ID is None:
        _DEFAULT_USER_ID = sqlite_manager.get_or_create_user("system", "system@localhost")
    return _DEFAULT_USER_ID


def truncate_text(text: str, max_chars: int) -> str:
    """Trim text to a bounded size while preserving meaning."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def compact_messages(messages: list[dict], max_messages: int | None = None, max_chars: int | None = None) -> list[dict]:
    """Keep only the newest messages and shorten each content field."""
    limit = max_messages if max_messages is not None else config.max_context_messages
    char_limit = max_chars if max_chars is not None else config.max_context_chars
    compacted = messages[-limit:] if limit > 0 else list(messages)
    return [
        {
            "role": msg.get("role", "unknown"),
            "content": truncate_text(str(msg.get("content", "")), char_limit),
        }
        for msg in compacted
    ]


def summarize_retrieval_results(results: list[dict], max_items: int = 3, max_chars: int | None = None) -> list[dict]:
    """Keep only the most useful retrieval results and trim payload size."""
    char_limit = max_chars if max_chars is not None else config.max_result_chars
    summarized = []
    for result in results[:max_items]:
        summarized.append(
            {
                "source": result.get("source", "unknown"),
                "title": truncate_text(str(result.get("title", "N/A")), 120),
                "content": truncate_text(str(result.get("content", "")), char_limit),
                "relevance": result.get("relevance", 0),
            }
        )
    return summarized


def create_session(session_id: str, title: Optional[str] = None) -> Dict[str, Any]:
    """Create a new session with conversation history (persistent in SQLite)."""
    user_id = _get_default_user_id()
    sqlite_manager.get_or_create_session(user_id, session_id, title=title)
    return {"session_id": session_id, "user_id": user_id}


def get_session(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve existing session chat history from persistent storage."""
    user_id = _get_default_user_id()
    db_session = sqlite_manager.get_or_create_session(user_id, session_id)
    
    # Fetch chat history from SQLite
    messages = sqlite_manager.get_session_history(db_session, limit=100)
    
    # Convert to expected format
    return [
        {"role": msg["message_role"], "content": msg["message_content"]}
        for msg in messages
    ]


def add_to_session(session_id: str, role: str, content: str) -> None:
    """Add message to session history in persistent storage."""
    user_id = _get_default_user_id()
    db_session = sqlite_manager.get_or_create_session(user_id, session_id)
    sqlite_manager.add_chat_message(db_session, user_id, role, content)


def generate_chat_title(task: str) -> str:
    """Derive an initial chat title from the first user message.

    Mirrors the frontend's `generateTitle` so the persisted title matches what
    the user sees before the first refresh.
    """
    cleaned = " ".join(task.split()).strip()
    if not cleaned:
        return "New Chat"
    if len(cleaned) > 40:
        return cleaned[:40].rstrip() + "…"
    return cleaned


def set_session_title(session_id: str, title: str = "") -> bool:
    """Derive a short title from `title` (typically the first user task) and
    persist it. Only sets it when no title exists yet, so the *initial* chat
    title is preserved across subsequent messages."""
    generated = generate_chat_title(title)
    return sqlite_manager.update_session_title(session_id, generated)


def get_session_title(session_id: str) -> Optional[str]:
    """Return the persisted title for a session, or None."""
    return sqlite_manager.get_session_title(session_id)


def load_session_context(state: AgentState) -> AgentState:
    """
    Load session context and conversation history from persistent storage.
    Also retrieves relevant agent memories.
    """
    
    # Get or create session and fetch chat history
    session_id = state.get("session_id", "default")
    conversation_history = get_session(session_id)
    
    # Compact messages to fit context limits
    compacted_history = compact_messages(conversation_history)
    
    # Load relevant agent memories
    task = state.get("task", "")
    relevant_memories = retrieve_relevant_memories(task, limit=5) if task else []
    
    # Build session context string (e.g., expertise areas, previous solutions)
    session_context_parts = []
    
    if compacted_history:
        # Analyze history for patterns
        expertise_areas = set()
        for msg in compacted_history:
            content_lower = msg.get("content", "").lower()
            if any(word in content_lower for word in ["python", "javascript", "code", "sql"]):
                expertise_areas.add("programming")
            if any(word in content_lower for word in ["data", "analysis", "statistic", "ml"]):
                expertise_areas.add("data science")
            if any(word in content_lower for word in ["research", "paper", "study"]):
                expertise_areas.add("research")
        
        if expertise_areas:
            session_context_parts.append(f"User Expertise: {', '.join(expertise_areas)}")
        
        session_context_parts.append(f"Conversation History: {len(compacted_history)} messages")
    
    # Add relevant memories to context
    if relevant_memories:
        session_context_parts.append(f"Retrieved Memories: {len(relevant_memories)} relevant items")
    
    session_context = "\n".join(session_context_parts) or "New session, no prior context"
    session_context = truncate_text(session_context, config.max_context_chars)
    
    print(f"\n  Session Context Loaded:")
    print(f"    Session ID: {session_id}")
    print(f"    History: {len(compacted_history)} messages")
    print(f"    Memories: {len(relevant_memories)} retrieved")
    print(f"    Context: {session_context[:100]}...")
    
    return {
        **state,
        "session_id": session_id,
        "conversation_history": compacted_history,
        "session_context": session_context,
        "agent_memory": relevant_memories,
        "retrieval_results": state.get("retrieval_results", []),
        "available_tools": state.get("available_tools", []),
        "specialist_results": state.get("specialist_results", {}),
    }


# Agent Memory Functions
def store_fact(fact: str, category: str = "general") -> int:
    """Store a learned fact in agent memory."""
    user_id = _get_default_user_id()
    key = fact[:50].strip()  # First 50 chars as key
    memory_id = sqlite_manager.add_memory(
        user_id=user_id,
        memory_type="fact",
        key_concept=key,
        content=fact,
        category=category,
        relevance_score=1.0
    )
    return memory_id


def store_experience(experience: str, outcome: str, category: str = "learned") -> int:
    """Store a past experience with outcome."""
    user_id = _get_default_user_id()
    key = experience[:50].strip()
    memory_id = sqlite_manager.add_memory(
        user_id=user_id,
        memory_type="experience",
        key_concept=key,
        content=f"Experience: {experience}\nOutcome: {outcome}",
        category=category,
        relevance_score=1.0
    )
    return memory_id


def store_behavioral_rule(rule: str, category: str = "behavior") -> int:
    """Store a behavioral rule for agents to follow."""
    user_id = _get_default_user_id()
    key = rule[:50].strip()
    memory_id = sqlite_manager.add_memory(
        user_id=user_id,
        memory_type="behavioral_rule",
        key_concept=key,
        content=rule,
        category=category,
        relevance_score=1.0
    )
    return memory_id


def retrieve_relevant_memories(task: str, memory_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant memories based on task/query."""
    user_id = _get_default_user_id()
    
    # Search for relevant memories by content matching
    memories = sqlite_manager.search_memory(
        user_id=user_id,
        query_text=task,
        memory_type=memory_type,
        limit=limit
    )
    
    # Update usage count for retrieved memories
    for memory in memories:
        sqlite_manager.update_memory_usage(memory["id"])
    
    return memories


def get_all_memories(memory_type: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all stored memories, optionally filtered by type and category."""
    user_id = _get_default_user_id()
    return sqlite_manager.get_memory(user_id=user_id, memory_type=memory_type, category=category)


def format_memories_for_context(memories: List[Dict[str, Any]]) -> str:
    """Format memories into a context string for LLM."""
    if not memories:
        return "No relevant memories found."
    
    formatted = []
    for mem in memories:
        mem_type = mem.get("memory_type", "unknown")
        key = mem.get("key_concept", "")
        content = mem.get("content", "")
        category = mem.get("category", "")
        
        header = f"[{mem_type.upper()}" 
        if category:
            header += f" - {category}"
        header += f"] {key}"
        
        formatted.append(f"{header}\n{content}")
    
    return "\n\n".join(formatted)


def load_agent_memory_context(state: AgentState, memory_type: Optional[str] = None) -> str:
    """Load relevant agent memories and return as formatted context."""
    task = state.get("task", "")
    memories = retrieve_relevant_memories(task, memory_type=memory_type, limit=5)
    return format_memories_for_context(memories)
