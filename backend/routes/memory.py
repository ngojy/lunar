"""
Agent Memory API Routes
Endpoints for storing, retrieving, and managing agent/LLM memory
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from rag_hybrid import sqlite_manager
from memory_integration import (
    store_fact,
    store_experience,
    store_behavioral_rule,
    retrieve_relevant_memories,
    get_all_memories,
    format_memories_for_context,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


class MemoryEntry(BaseModel):
    memory_type: str  # "fact", "experience", "behavioral_rule"
    key_concept: str
    content: str
    category: Optional[str] = None
    relevance_score: float = 1.0


class MemoryResponse(BaseModel):
    id: int
    memory_type: str
    key_concept: str
    content: str
    category: Optional[str]
    relevance_score: float
    usage_count: int
    last_used: Optional[str]


@router.post("/store-fact", response_model=dict)
def store_fact_endpoint(entry: MemoryEntry):
    """Store a learned fact in agent memory."""
    try:
        memory_id = store_fact(entry.content, category=entry.category or "general")
        return {"id": memory_id, "status": "success", "message": "Fact stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store-experience", response_model=dict)
def store_experience_endpoint(entry: MemoryEntry):
    """Store a past experience with outcome."""
    try:
        # For experiences, content should be "experience|outcome" format
        parts = entry.content.split("|", 1)
        experience = parts[0].strip() if parts else entry.content
        outcome = parts[1].strip() if len(parts) > 1 else "No outcome recorded"
        
        memory_id = store_experience(experience, outcome, category=entry.category or "learned")
        return {"id": memory_id, "status": "success", "message": "Experience stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store-rule", response_model=dict)
def store_rule_endpoint(entry: MemoryEntry):
    """Store a behavioral rule for agents."""
    try:
        memory_id = store_behavioral_rule(entry.content, category=entry.category or "behavior")
        return {"id": memory_id, "status": "success", "message": "Behavioral rule stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve", response_model=dict)
def retrieve_memories_endpoint(
    task: str = Query(..., description="Task or query to find relevant memories"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type: fact, experience, behavioral_rule"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of memories to retrieve"),
):
    """Retrieve relevant memories based on task/query."""
    try:
        memories = retrieve_relevant_memories(task, memory_type=memory_type, limit=limit)
        formatted = format_memories_for_context(memories)
        
        return {
            "count": len(memories),
            "memories": memories,
            "formatted_context": formatted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=dict)
def list_memories_endpoint(
    memory_type: Optional[str] = Query(None, description="Filter by type"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """List all stored memories, optionally filtered."""
    try:
        memories = get_all_memories(memory_type=memory_type, category=category)
        
        return {
            "count": len(memories),
            "memories": memories,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{memory_id}", response_model=dict)
def delete_memory_endpoint(memory_id: int):
    """Delete a specific memory entry."""
    try:
        sqlite_manager.delete_memory(memory_id)
        return {"status": "success", "message": f"Memory {memory_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-all", response_model=dict)
def clear_all_memories_endpoint(memory_type: Optional[str] = Query(None)):
    """Clear all memories of a specific type (or all if no type specified)."""
    try:
        # Get user ID
        user_id = sqlite_manager.get_or_create_user("system", "system@localhost")
        
        # Get memories to delete
        memories = sqlite_manager.get_memory(user_id, memory_type=memory_type, limit=10000)
        
        # Delete them
        deleted_count = 0
        for mem in memories:
            sqlite_manager.delete_memory(mem["id"])
            deleted_count += 1
        
        return {
            "status": "success",
            "message": f"Cleared {deleted_count} memories",
            "deleted_count": deleted_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=dict)
def search_memories_endpoint(
    query: str = Query(..., description="Search query text"),
    memory_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    """Search memories by text content."""
    try:
        user_id = sqlite_manager.get_or_create_user("system", "system@localhost")
        memories = sqlite_manager.search_memory(user_id, query, memory_type=memory_type, limit=limit)
        
        return {
            "count": len(memories),
            "query": query,
            "memories": memories,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
