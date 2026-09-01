import sys
import os
import uuid
import json
from datetime import datetime
from typing import Any, Optional, AsyncGenerator

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import asyncio
from pydantic import BaseModel
from config import config, detect_available_models
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from routes.storage import router as storage_router
from routes.memory import router as memory_router
from rag_hybrid import sqlite_manager


api = FastAPI(title="lunar API", version="1.0.0")

# CORSMiddleware allows React at localhost:5173 to talk to the backend at localhost:3000
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include storage routes
api.include_router(storage_router)
# Include memory routes
api.include_router(memory_router)


# Persistent storage comment - using SQLite via memory_integration
from memory_integration import get_session, add_to_session, load_session_context, set_session_title, get_session_title

# in-memory storage for current session context (temporary during request processing)
conversation_history: list[dict[str, Any]] = []


# pydantic models, define shape of data coming in and out 
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    web_search: bool = False
    execution_mode: str = "agent"
    model: Optional[str] = None
    temperature: float = 0.0
    user_name: str = ""
    agent_model_settings: Optional[dict[str, str]] = None
    rag_settings: Optional[dict[str, Any]] = None
    request_critique: bool = False
    auto_critique: bool = True

class AgentStep(BaseModel):
    agent: str
    message: str
    timestamp: str


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatResponse(BaseModel):
    id: str
    session_id: str
    task: str
    answer: str
    steps: list[AgentStep]
    duration_seconds: float
    timestamp: str
    critique_performed: bool = False
    critique_feedback: Optional[str] = None
    critique_suggestions: list[str] = []
    execution_mode: str = "agent"
    model_used: str = ""
    token_usage: TokenUsage


def _to_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_token_usage(messages: list[dict[str, Any]]) -> Optional[TokenUsage]:
    prompt_total = 0
    completion_total = 0
    found_any = False

    for msg in messages:
        usage_meta = msg.get("usage_metadata") if isinstance(msg, dict) else None
        response_meta = msg.get("response_metadata") if isinstance(msg, dict) else None

        prompt = None
        completion = None

        if isinstance(usage_meta, dict):
            prompt = _to_int(usage_meta.get("prompt_tokens") or usage_meta.get("input_tokens"))
            completion = _to_int(usage_meta.get("completion_tokens") or usage_meta.get("output_tokens"))

        if (prompt is None or completion is None) and isinstance(response_meta, dict):
            prompt = prompt if prompt is not None else _to_int(response_meta.get("prompt_eval_count") or response_meta.get("prompt_tokens") or response_meta.get("input_tokens"))
            completion = completion if completion is not None else _to_int(response_meta.get("eval_count") or response_meta.get("completion_tokens") or response_meta.get("output_tokens"))

        if prompt is not None or completion is not None:
            prompt_total += prompt or 0
            completion_total += completion or 0
            found_any = True

    if not found_any:
        return None

    return TokenUsage(
        prompt_tokens=prompt_total,
        completion_tokens=completion_total,
        total_tokens=prompt_total + completion_total,
    )


# endpoints
# /health: GET, Check if the service is running
@api.get("/health")
def health_check():
    return {"status": "ok", "service": "lunar API", "version": "1.0.0"}


# /models: GET, return list of available models
@api.get("/models")
def get_available_models():
    models = detect_available_models([config.ollama_host]) or config.available_models or []
    return {"models": models}


# Streaming response generator function
async def generate_streaming_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Generate a streaming response with steps and tokens for real-time display.
    Each line is newline-delimited JSON (NDJSON).
    """
    task = request.message.strip()
    if not task:
        yield json.dumps({"type": "error", "message": "Message cannot be empty"}) + "\n"
        return
    
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get persistent session messages from database
    session_messages = get_session(session_id)
    
    # Persist the initial chat title (derived from the first user message).
    # Only set when empty, so the title is fixed on first use.
    set_session_title(session_id, task)
    
    start_time = datetime.now()

    try:
        selected_model = request.model or config.model
        if not selected_model:
            yield json.dumps({"type": "error", "message": "Model selection is required"}) + "\n"
            return

        mode = (request.execution_mode or "agent").strip().lower()
        if mode not in {"chat", "agent"}:
            yield json.dumps({"type": "error", "message": "execution_mode must be 'chat' or 'agent'"}) + "\n"
            return

        answer = ""
        token_usage = None
        critique_performed = False
        critique_feedback = None
        critique_suggestions: list[str] = []
        retrieved_documents: list[dict[str, Any]] = []
        seen_step_signatures: set[tuple[str, str]] = set()

        if mode == "chat":
            llm = ChatOllama(
                model=selected_model,
                temperature=request.temperature,
                base_url=config.ollama_host,
            )

            llm_messages = [
                SystemMessage(
                    content=(
                        "You are Lunar. In chat mode, respond directly and conversationally to the user. "
                        "Do not describe internal agents or execution pipelines unless the user asks."
                    )
                )
            ]

            for msg in session_messages[-20:]:
                role = msg.get("role")
                content = str(msg.get("content", "")).strip()
                if not content:
                    continue
                if role == "user":
                    llm_messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    llm_messages.append(AIMessage(content=content))

            llm_messages.append(HumanMessage(content=task))
            
            # Stream step: generating response
            yield json.dumps({
                "type": "step",
                "agent": "assistant",
                "message": "Generating response..."
            }) + "\n"
            await asyncio.sleep(0.01)  # Allow event to flush
            
            llm_response = llm.invoke(llm_messages)
            answer = (str(getattr(llm_response, "content", "")).strip() or "No answer produced.")
            message_dict = llm_response.model_dump() if hasattr(llm_response, "model_dump") else {}
            token_usage = _extract_token_usage([message_dict])
        else:
            from graph import app as agent_app

            agent_model_settings = request.agent_model_settings or {}

            initial_state = {
                "task": task,
                "messages": [{"role": "user", "content": task}],
                "session_id": session_id,
                "conversation_history": session_messages,
                "session_context": "",
                "router_decision": {},
                "needs_reasoning": False,
                "needs_retrieval": False,
                "needs_tools": False,
                "specialist_types": [],
                "needs_synthesis": False,
                "reasoning_plan": "",
                "retrieval_results": [],
                "available_tools": [],
                "specialist_results": {},
                "final_response": "",
                "synthesis_performed": False,
                "should_critique": False,
                "critique_performed": False,
                "critique_feedback": "",
                "critique_suggestions": [],
                "metadata": {
                    "web_search":   request.web_search,
                    "execution_mode": mode,
                    "model":        selected_model,
                    "temperature":  request.temperature,
                    "user_name":    request.user_name,
                    "rag_settings": request.rag_settings or {},
                    "request_critique": request.request_critique,
                    "auto_critique": request.auto_critique,
                },
                "agent_model_settings": agent_model_settings,
            }
            
            run_config = {"configurable": {"thread_id": session_id}}
            final_state = None
            last_message_count = 0

            for step in agent_app.stream(initial_state, config=run_config):
                node_name, node_state = next(iter(step.items()))
                final_state = node_state

                all_messages = node_state.get("messages", [])
                new_messages = all_messages[last_message_count:]
                last_message_count = len(all_messages)

                for msg in new_messages:
                    role = msg.get("role", node_name)
                    content = msg.get("content", "")

                    signature = (str(role), str(content))
                    if signature in seen_step_signatures:
                        continue
                    seen_step_signatures.add(signature)

                    # Stream each step as it happens
                    step_event = json.dumps({
                        "type": "step",
                        "agent": role,
                        "message": content,
                        "timestamp": datetime.now().isoformat()
                    }) + "\n"
                    yield step_event
                    await asyncio.sleep(0.01)  # Allow event to flush

            if final_state is None:
                answer = "No answer produced."
            else:
                answer = final_state.get("final_response") or "No answer produced."

            all_messages = final_state.get("messages", []) if final_state else []
            token_usage = _extract_token_usage(all_messages)
            critique_performed = final_state.get("critique_performed", False) if final_state else False
            critique_feedback = final_state.get("critique_feedback", None) if final_state else None
            critique_suggestions = final_state.get("critique_suggestions", []) if final_state else []

            # Extract retrieved documents from retrieval results
            retrieved_documents = []
            if final_state:
                retrieval_results = final_state.get("retrieval_results", [])
                if isinstance(retrieval_results, list):
                    for result in retrieval_results:
                        if isinstance(result, dict):
                            doc_dict = {
                                "doc_id": result.get("doc_id", result.get("id")),
                                "filename": result.get("filename", result.get("title", "Unknown")),
                                "relevance_score": result.get("relevance_score", result.get("score", 0.0)),
                                "chunk_count": result.get("chunk_count"),
                            }
                            retrieved_documents.append(doc_dict)

        if token_usage is None:
            prompt_tokens = max(1, round(len(task) / 4))
            completion_tokens = max(1, round(len(answer) / 4))
            token_usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
        
        # Stream the final response word-by-word
        words = answer.split()
        for i, word in enumerate(words):
            token_event = json.dumps({
                "type": "token",
                "content": word + (" " if i < len(words) - 1 else "")
            }) + "\n"
            yield token_event
            await asyncio.sleep(0.01)  # Small delay for realistic streaming effect
        
        # Add user and assistant messages to persistent session history
        add_to_session(session_id, "user", task)
        add_to_session(session_id, "assistant", answer)

        duration = (datetime.now() - start_time).total_seconds()

        # Send completion with metadata
        done_event = json.dumps({
            "type": "done",
            "session_id": session_id,
            "duration_seconds": round(duration, 2),
            "critique_performed": critique_performed,
            "critique_feedback": critique_feedback,
            "critique_suggestions": critique_suggestions,
            "execution_mode": mode,
            "model_used": selected_model,
            "retrieved_documents": retrieved_documents if mode == "agent" else [],
            "token_usage": {
                "prompt_tokens": token_usage.prompt_tokens,
                "completion_tokens": token_usage.completion_tokens,
                "total_tokens": token_usage.total_tokens,
            }
        }) + "\n"
        yield done_event

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_event = json.dumps({
            "type": "error",
            "message": str(e)
        }) + "\n"
        yield error_event


# /chat/stream: POST, streaming endpoint for real-time response with thought process
@api.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming endpoint that returns newline-delimited JSON events.
    Events include:
    - "step": thought/process message from agents
    - "token": word tokens from final response
    - "done": completion metadata
    - "error": error message
    """
    return StreamingResponse(
        generate_streaming_response(request),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no"}  # Disable proxy buffering
    )


# /history: GET, retrieve the conversation history
@api.get("/history")
def get_history():
    return {"history": conversation_history}

# /history: DELETE, clear the conversation history
@api.delete("/history")
def clear_history():
    conversation_history.clear()
    return {"message": "History cleared"}

# /sessions: GET, retrieve list of all sessions with message counts
@api.get("/sessions")
def list_sessions():
    try:
        sessions_list = sqlite_manager.list_sessions_with_counts()
        sessions = []
        for session in sessions_list:
            sessions.append({
                "session_id": session["session_id"],
                "title": session["title"],
                "message_count": session["message_count"],
                "last_message_at": session["last_message_at"],
            })
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return {"sessions": [], "total": 0}

# /session/{session_id}: GET, retrieve session history from persistent storage
@api.get("/session/{session_id}")
def get_session_endpoint(session_id: str):
    messages = get_session(session_id)
    title = get_session_title(session_id)
    return {
        "session_id": session_id,
        "title": title,
        "messages": messages if messages else [],
    }

# /session/{session_id}: DELETE, clear a session from persistent storage
@api.delete("/session/{session_id}")
def clear_session(session_id: str):
    try:
        success = sqlite_manager.delete_session(session_id)
        if success:
            return {"status": "success", "message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
