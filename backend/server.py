import sys
import os
import uuid
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


api = FastAPI(title="lunar API", version="1.0.0")

# CORSMiddleware allows React at localhost:5173 to talk to the backend at localhost:3000
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# in-memory storage, stores past conversations while container is running. This is not persistent storage, so if the container is restarted, the conversation history will be lost.
conversation_history: list[dict[str, Any]] = []


# pydantic models, define shape of data coming in and out 
class ChatRequest(BaseModel):
    message: str
    web_search: bool = False

class AgentStep(BaseModel):
    agent: str
    message: str
    timestamp: str

class ChatResponse(BaseModel):
    id: str
    task: str
    answer: str
    steps: list[AgentStep]
    duration_seconds: float
    timestamp: str


# endpoints
# /health: GET, Check if the service is runnign
@api.get("/health")
def health_check():
    return {"status": "ok", "service": "lunar API", "version": "1.0.0"}


# /chat: POST, send a message to the agent and get a response
@api.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    task = request.message.strip()
    if not task:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    steps: list[AgentStep] = []
    start_time = datetime.now()

    try:
        from graph import app as agent_app

        initial_state = {
            "task": task,
            "messages": [{"role": "user", "content": task}],
            "next_agent": "",
            "research_results": [],
            "execution_results": [],
            "critique": "", 
            "final_answer": "",
            "iteration": 0,
            "metadata": {"web_search": request.web_search}
        }
        
        run_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = None

        for step in agent_app.stream(initial_state, config=run_config):
            node_name, node_state = next(iter(step.items()))
            final_state = node_state

            for msg in node_state.get("messages", []):
                role = msg.get("role", node_name)
                content = msg.get("content", "")
                steps.append(AgentStep(
                    agent=role,
                    message=content,
                    timestamp=datetime.now().isoformat()
                ))
        
        if final_state is None:
            answer = "No answer produced."
        else:
            answer = final_state.get("final_answer") or "No answer produced."

        print(f"Final state keys: {list(final_state.keys()) if final_state else 'None'}")
        print(f"Final answer: {answer}")

        duration = (datetime.now() - start_time).total_seconds()

        response = ChatResponse(
            id=str(uuid.uuid4()),
            task=task,
            answer=answer,
            steps=steps,
            duration_seconds=round(duration, 2),
            timestamp=start_time.isoformat()
        )

        conversation_history.append(response.model_dump())
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# /history: GET, retrieve the conversation history
@api.get("/history")
def get_history():
    return {"history": conversation_history}

# /history: DELETE, clear the conversation history
@api.delete("/history")
def clear_history():
    conversation_history.clear()
    return {"message": "Historycleared"}