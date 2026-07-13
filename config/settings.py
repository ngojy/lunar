"""
Central config — reads from environment variables / .env file.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # LLM
    model: str = os.getenv("MODEL", "qwen3.6:35b-a3b")
    temperature: float = float(os.getenv("TEMPERATURE", "0"))

    # Agent behaviour
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "10"))
    max_research_results: int = int(os.getenv("MAX_RESEARCH_RESULTS", "5"))

    # Tools
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")   # web search

    # Memory / persistence
    enable_checkpointing: bool = os.getenv("ENABLE_CHECKPOINTING", "false").lower() == "true"
    checkpoint_db: str = os.getenv("CHECKPOINT_DB", "checkpoints.db")

    def validate(self) -> None:
        if not self.model:
            raise ValueError("MODEL is not set. Add it to your .env file.")

config = Config()