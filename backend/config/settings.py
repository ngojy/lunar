"""
Central config — reads from environment variables / .env file.
"""

import os
import json
from dataclasses import dataclass
from dotenv import load_dotenv
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

load_dotenv()

def _parse_available_models(raw: str) -> list[str]:
    """Parse comma-separated models from env var."""
    if not raw:
        return []
    return [m.strip() for m in raw.split(",") if m.strip()]


def _parse_csv(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _fetch_ollama_models(base_url: str, timeout: float = 2.0) -> list[str]:
    """Fetch installed Ollama model names from a reachable Ollama host."""
    url = base_url.rstrip("/") + "/api/tags"
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = payload.get("models", [])
        names: list[str] = []
        for model in models:
            name = model.get("name") if isinstance(model, dict) else None
            if name:
                names.append(name)
        return names
    except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        return []


def detect_available_models(candidate_hosts: list[str] | None = None) -> list[str]:
    """Detect available Ollama models from the first reachable host."""
    hosts = candidate_hosts or [
        os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434"),
        "http://localhost:11434",
        "http://host.docker.internal:11434",
    ]

    seen: set[str] = set()
    ordered_hosts = []
    for host in hosts:
        if host and host not in seen:
            seen.add(host)
            ordered_hosts.append(host)

    for host in ordered_hosts:
        models = _fetch_ollama_models(host)
        if models:
            return models

    return []

@dataclass
class Config:
    # Ollama host
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")

    # LLM — available models and default (no hardcoded default)
    available_models: list[str] = None
    model: str = None
    temperature: float = float(os.getenv("TEMPERATURE", "0"))

    # Agent behaviour
    max_research_results: int = int(os.getenv("MAX_RESEARCH_RESULTS", "5"))
    max_context_messages: int = int(os.getenv("MAX_CONTEXT_MESSAGES", "6"))
    max_context_chars: int = int(os.getenv("MAX_CONTEXT_CHARS", "2000"))
    max_prompt_chars: int = int(os.getenv("MAX_PROMPT_CHARS", "4000"))
    max_result_chars: int = int(os.getenv("MAX_RESULT_CHARS", "500"))

    # Tools
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")   # web search

    # RAG: local files/docs
    rag_file_roots: list[str] = None
    rag_file_extensions: list[str] = None
    rag_embedding_model: str = os.getenv("RAG_EMBEDDING_MODEL", "nomic-embed-text")
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "5"))
    rag_max_files: int = int(os.getenv("RAG_MAX_FILES", "200"))
    rag_chunk_chars: int = int(os.getenv("RAG_CHUNK_CHARS", "900"))
    rag_chunk_overlap: int = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))

    # RAG: database
    rag_db_type: str = os.getenv("RAG_DB_TYPE", "sqlite")
    rag_db_connection: str = os.getenv("RAG_DB_CONNECTION", "")
    rag_db_table: str = os.getenv("RAG_DB_TABLE", "")
    rag_db_text_columns: list[str] = None

    # Memory / persistence
    enable_checkpointing: bool = os.getenv("ENABLE_CHECKPOINTING", "false").lower() == "true"
    checkpoint_db: str = os.getenv("CHECKPOINT_DB", "checkpoints.db")

    def __post_init__(self):
        detected_models = detect_available_models([self.ollama_host])
        if not detected_models:
            detected_models = detect_available_models()

        reachable_host = None
        for candidate in [self.ollama_host, "http://localhost:11434", "http://host.docker.internal:11434"]:
            if candidate and _fetch_ollama_models(candidate):
                reachable_host = candidate
                break

        if reachable_host:
            self.ollama_host = reachable_host

        # Parse available models from env
        if self.available_models is None:
            raw_models = os.getenv("AVAILABLE_MODELS", "")
            self.available_models = _parse_available_models(raw_models)

        if not self.available_models and detected_models:
            self.available_models = detected_models
        
        # Set default model only from env; otherwise the user must choose explicitly.
        if self.model is None:
            default_from_env = os.getenv("DEFAULT_MODEL", "").strip()
            self.model = default_from_env or None

        if self.rag_file_roots is None:
            self.rag_file_roots = _parse_csv(os.getenv("RAG_FILE_ROOTS", ""))

        if self.rag_file_extensions is None:
            self.rag_file_extensions = _parse_csv(
                os.getenv("RAG_FILE_EXTENSIONS", ".txt,.md,.json,.csv,.py,.ts,.tsx,.js,.jsx,.pdf,.docx")
            )

        if self.rag_db_text_columns is None:
            self.rag_db_text_columns = _parse_csv(os.getenv("RAG_DB_TEXT_COLUMNS", "content,text,body,description"))

    def validate(self) -> None:
        if not self.available_models:
            raise ValueError("Either MODEL or AVAILABLE_MODELS must be set in your .env file.")

def resolve_model(agent_name: str, request_model: str | None, agent_model_settings: dict[str, str] | None = None) -> str | None:
    """
    Resolve which model to use for a given agent.
    Priority: request_model > agent_model_settings[agent_name] > config.model
    """
    if request_model:
        return request_model
    
    if agent_model_settings and agent_name in agent_model_settings:
        agent_model = agent_model_settings[agent_name]
        if agent_model:
            return agent_model
    
    return config.model

config = Config()