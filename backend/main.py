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
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "lunar API", "version": "1.0.0"}


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
        