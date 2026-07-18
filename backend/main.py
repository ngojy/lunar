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


app = FastAPI(title="lunar API", version="1.0.0")

# CORSMiddleware allows React at localhost:5173 to talk to the backend at localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://localhost:5173", "https://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# in-memory storage, stores past conversations while container is running. This is not persistent storage, so if the container is restarted, the conversation history will be lost.
conversation_history: list[dict[str, Any]] = []


# pydantic models, define shape of data coming in and out 
class ChatRequest(BaseModel):
    message: str

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
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lunar API", "version": "1.0.0"}


# /chat: POST, send a message to the agent and get a response
@app.post("/chat", response_model=ChatResponse)
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
            "message": [{"role": "user", "content": task}],
            "next_agent": "",
            "research_results": [],
            "execution_results": [],
            "critique": [],
            "final_answer": "",
            "iteration": 0,
            "metadata": {}
        }
        
        run_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        final_state = None

        for step in agent_app.run(initial_state, run_config):
            node_name, node_state = next(iter(step.items()))
            final_state = node_state

            for msg in node_state.get("message", []):
                role = msg.get("role", node_name)
                content = msg.get("content", "")
                steps.append(AgentStep(
                    agent=role,
                    message=content,
                    timestamp=datetime.now().isoformat()
                ))
        
        answer = (final_state or {}).get("final_answer", "No answer generated.")
        duration = (datetime.now() - start_time).total_seconds()

        response = ChatResponse(
            id=str(uuid.uuid4()),
            task=task,
            answer=answer,
            steps=steps,
            duration_seconds=round(duration, 2),
            timestamp=start_time.isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


# /history: GET, retrieve the conversation history
@app.get("/history")
def get_history():
    return {"history": conversation_history}

# /history: DELETE, clear the conversation history
@app.delete("/history")
def clear_history():
    conversation_history.clear()
    return {"message": "Historycleared"}