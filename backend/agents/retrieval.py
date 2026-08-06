"""
Retrieval Agent
Responsibilities:
    - Execute web search and local RAG retrieval (files/docs/db)
  - Return relevant information for the task
  - Only invoked if router.needs_retrieval = True
"""

from __future__ import annotations

from typing import Any
from pathlib import Path
import math
import sqlite3

from state import AgentState
from config import config
from memory_integration import truncate_text

try:
    from langchain_tavily import TavilySearch
except Exception:  # pragma: no cover - optional dependency fallback
    TavilySearch = None

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover - optional dependency fallback
    DDGS = None

try:
    from langchain_ollama import OllamaEmbeddings
except Exception:  # pragma: no cover - optional dependency fallback
    OllamaEmbeddings = None


def _get_rag_settings(state: AgentState) -> dict[str, Any]:
    metadata = state.get("metadata", {})
    request_settings = metadata.get("rag_settings") if isinstance(metadata, dict) else None
    request_settings = request_settings if isinstance(request_settings, dict) else {}

    return {
        "enabled": bool(request_settings.get("enabled", True)),
        "include_web": bool(request_settings.get("include_web", True)),
        "include_files": bool(request_settings.get("include_files", True)),
        "include_db": bool(request_settings.get("include_db", False)),
        "file_roots": request_settings.get("file_roots") or config.rag_file_roots,
        "file_extensions": request_settings.get("file_extensions") or config.rag_file_extensions,
        "embedding_model": request_settings.get("embedding_model") or config.rag_embedding_model,
        "top_k": int(request_settings.get("top_k") or config.rag_top_k),
        "max_files": int(request_settings.get("max_files") or config.rag_max_files),
        "chunk_chars": int(request_settings.get("chunk_chars") or config.rag_chunk_chars),
        "chunk_overlap": int(request_settings.get("chunk_overlap") or config.rag_chunk_overlap),
        "db_type": str(request_settings.get("db_type") or config.rag_db_type),
        "db_connection": str(request_settings.get("db_connection") or config.rag_db_connection),
        "db_table": str(request_settings.get("db_table") or config.rag_db_table),
        "db_text_columns": request_settings.get("db_text_columns") or config.rag_db_text_columns,
    }


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("\n", ",").split(",") if item.strip()]
    return []


def _chunk_text(text: str, size: int, overlap: int) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []

    if len(clean) <= size:
        return [clean]

    chunks: list[str] = []
    start = 0
    step = max(1, size - overlap)
    while start < len(clean):
        end = start + size
        chunk = clean[start:end]
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _semantic_rank(
    query: str,
    candidates: list[dict[str, Any]],
    embedding_model: str,
    top_k: int,
) -> list[dict[str, Any]]:
    if not candidates:
        return []

    if OllamaEmbeddings is None:
        return candidates[:top_k]

    try:
        embedder = OllamaEmbeddings(model=embedding_model, base_url=config.ollama_host)
        query_vec = embedder.embed_query(query)
        doc_texts = [str(item.get("content", "")) for item in candidates]
        doc_vecs = embedder.embed_documents(doc_texts)

        scored: list[tuple[float, dict[str, Any]]] = []
        for item, vec in zip(candidates, doc_vecs):
            score = _cosine_similarity(query_vec, vec)
            enriched = {**item, "relevance": round(float(score), 4)}
            scored.append((score, enriched))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:top_k]]
    except Exception as exc:
        print(f"  Semantic ranking failed: {exc}")
        return candidates[:top_k]


def _search_files(query: str, settings: dict[str, Any]) -> list[dict[str, Any]]:
    roots = _normalize_list(settings.get("file_roots"))
    if not roots:
        return []

    extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in _normalize_list(settings.get("file_extensions"))}
    max_files = max(1, int(settings.get("max_files", config.rag_max_files)))
    chunk_chars = max(200, int(settings.get("chunk_chars", config.rag_chunk_chars)))
    chunk_overlap = max(0, int(settings.get("chunk_overlap", config.rag_chunk_overlap)))
    top_k = max(1, int(settings.get("top_k", config.rag_top_k)))
    embedding_model = str(settings.get("embedding_model", config.rag_embedding_model))

    collected: list[dict[str, Any]] = []
    scanned = 0

    for root in roots:
        root_path = Path(root)
        if not root_path.exists() or not root_path.is_dir():
            continue

        for file_path in root_path.rglob("*"):
            if scanned >= max_files:
                break
            if not file_path.is_file():
                continue
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            scanned += 1
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for idx, chunk in enumerate(_chunk_text(text, chunk_chars, chunk_overlap), start=1):
                collected.append(
                    {
                        "provider": "file_rag",
                        "source": "file",
                        "title": file_path.name,
                        "content": truncate_text(chunk, config.max_result_chars),
                        "url": str(file_path),
                        "query": query,
                        "rank": idx,
                    }
                )

    ranked = _semantic_rank(query, collected, embedding_model, top_k)
    if ranked:
        print(f"  File RAG returned {len(ranked)} results")
    return ranked


def _search_sqlite(query: str, settings: dict[str, Any]) -> list[dict[str, Any]]:
    db_connection = str(settings.get("db_connection", "")).strip()
    table = str(settings.get("db_table", "")).strip()
    text_columns = _normalize_list(settings.get("db_text_columns"))
    top_k = max(1, int(settings.get("top_k", config.rag_top_k)))
    embedding_model = str(settings.get("embedding_model", config.rag_embedding_model))

    if not db_connection or not table:
        return []

    if db_connection.startswith("sqlite:///"):
        db_connection = db_connection.replace("sqlite:///", "", 1)

    conn = sqlite3.connect(db_connection)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        table_columns = [row[1] for row in cursor.fetchall()]

        candidates = [col for col in text_columns if col in table_columns]
        if not candidates:
            candidates = [col for col in table_columns if any(h in col.lower() for h in ["text", "content", "body", "desc", "name", "title"])]

        if not candidates:
            return []

        select_cols = ", ".join(candidates)
        cursor.execute(f"SELECT rowid, {select_cols} FROM {table} LIMIT 500")
        rows = cursor.fetchall()

        docs: list[dict[str, Any]] = []
        for row in rows:
            rowid = row["rowid"]
            pieces = []
            for col in candidates:
                val = row[col]
                if val is not None and str(val).strip():
                    pieces.append(f"{col}: {val}")
            if not pieces:
                continue
            docs.append(
                {
                    "provider": "db_rag",
                    "source": "database",
                    "title": f"{table} row {rowid}",
                    "content": truncate_text(" | ".join(pieces), config.max_result_chars),
                    "url": f"sqlite:///{db_connection}#{table}:{rowid}",
                    "query": query,
                    "rank": int(rowid),
                }
            )

        ranked = _semantic_rank(query, docs, embedding_model, top_k)
        if ranked:
            print(f"  DB RAG returned {len(ranked)} results")
        return ranked
    except Exception as exc:
        print(f"  SQLite RAG failed: {exc}")
        return []
    finally:
        conn.close()


def _search_database(query: str, settings: dict[str, Any]) -> list[dict[str, Any]]:
    db_type = str(settings.get("db_type", "sqlite")).strip().lower()
    if db_type == "sqlite":
        return _search_sqlite(query, settings)

    print(f"  DB RAG unsupported db_type: {db_type}. Currently supported: sqlite")
    return []


def _dedupe_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate results by URL/title/content signature."""
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []

    for result in results:
        signature = (
            str(result.get("url", "")).strip().lower(),
            str(result.get("title", "")).strip().lower(),
            str(result.get("content", "")).strip().lower(),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(result)

    return deduped


def _normalize_item(item: Any, provider: str, query: str, rank: int) -> dict[str, Any]:
    """Normalize search outputs from different providers into one schema."""
    if isinstance(item, dict):
        title = item.get("title") or item.get("name") or query
        content = (
            item.get("content")
            or item.get("body")
            or item.get("snippet")
            or item.get("description")
            or item.get("raw_content")
            or ""
        )
        url = item.get("url") or item.get("link") or item.get("href") or ""
        score = item.get("score")
        if score is None:
            score = item.get("relevance")
        if score is None:
            score = max(0.1, 1.0 - (rank * 0.1))
    else:
        title = query
        content = str(item)
        url = ""
        score = max(0.1, 1.0 - (rank * 0.1))

    return {
        "provider": provider,
        "source": provider,
        "title": truncate_text(str(title), 120),
        "content": truncate_text(str(content), config.max_result_chars),
        "url": url,
        "relevance": score,
        "query": query,
        "rank": rank,
    }


def _coerce_results(raw: Any, provider: str, query: str) -> list[dict[str, Any]]:
    """Convert raw provider output into normalized result dictionaries."""
    if raw is None:
        return []

    if isinstance(raw, dict):
        if isinstance(raw.get("results"), list):
            items = raw["results"]
        elif isinstance(raw.get("data"), list):
            items = raw["data"]
        else:
            items = [raw]
    elif isinstance(raw, list):
        items = raw
    else:
        items = [raw]

    normalized = [
        _normalize_item(item, provider, query, index + 1)
        for index, item in enumerate(items)
    ]
    return _dedupe_results(normalized)


def _search_tavily(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search via Tavily if an API key is configured."""
    if not config.tavily_api_key or TavilySearch is None:
        return []

    try:
        search = TavilySearch(api_key=config.tavily_api_key, max_results=max_results)
        raw_results = search.invoke(query)
        results = _coerce_results(raw_results, "tavily", query)
        if results:
            print(f"  Tavily returned {len(results)} results")
        return results
    except Exception as exc:
        print(f"  Tavily search failed: {exc}")
        return []


def _search_duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search via DuckDuckGo using duckduckgo_search, with a LangChain fallback."""
    if DDGS is not None:
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results, safesearch="moderate"))
            results = _coerce_results(raw_results, "duckduckgo", query)
            if results:
                print(f"  DuckDuckGo returned {len(results)} results")
            return results
        except Exception as exc:
            print(f"  DuckDuckGo search failed: {exc}")

    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        tool = DuckDuckGoSearchRun()
        raw_result = tool.invoke(query)
        results = _coerce_results(raw_result, "duckduckgo", query)
        if results:
            print(f"  DuckDuckGo fallback returned {len(results)} results")
        return results
    except Exception as exc:
        print(f"  DuckDuckGo fallback failed: {exc}")
        return []


def _build_queries(task: str) -> list[str]:
    """Create one or two focused search queries from the task."""
    normalized = " ".join(task.split()).strip()
    if not normalized:
        return []

    queries = [normalized]

    if len(normalized) > 120:
        focused = normalized[:120].rsplit(" ", 1)[0].strip()
        if focused and focused != normalized:
            queries.append(focused)

    return queries[:2]


def retrieval_node(state: AgentState) -> AgentState:
    """Execute retrieval/RAG based on task."""

    task = state.get("task", "").strip()
    queries = _build_queries(task)
    max_results = max(1, config.max_research_results)
    rag_settings = _get_rag_settings(state)

    retrieval_results: list[dict[str, Any]] = []
    providers_used: list[str] = []

    for query in queries:
        print(f"  Retrieval query: {query}")

        if rag_settings.get("include_files", True):
            file_results = _search_files(query, rag_settings)
            if file_results:
                providers_used.append("file_rag")
                retrieval_results.extend(file_results)

        if rag_settings.get("include_db", False):
            db_results = _search_database(query, rag_settings)
            if db_results:
                providers_used.append("db_rag")
                retrieval_results.extend(db_results)

        if rag_settings.get("include_web", True):
            tavily_results = _search_tavily(query, max_results)
            if tavily_results:
                providers_used.append("tavily")
                retrieval_results.extend(tavily_results)
            else:
                duckduckgo_results = _search_duckduckgo(query, max_results)
                if duckduckgo_results:
                    providers_used.append("duckduckgo")
                    retrieval_results.extend(duckduckgo_results)

    retrieval_results = _dedupe_results(retrieval_results)

    if not retrieval_results:
        retrieval_results = [
            {
                "provider": "placeholder",
                "source": "placeholder",
                "title": "No search results found",
                "content": (
                    "No live search results were returned. Configure TAVILY_API_KEY "
                    "for Tavily or rely on DuckDuckGo fallback when external web results are needed."
                ),
                "url": "",
                "relevance": 0.0,
                "query": task,
                "rank": 1,
            }
        ]

    print(f"\n  Retrieval Results: {len(retrieval_results)} items")
    if providers_used:
        print(f"    Providers used: {', '.join(dict.fromkeys(providers_used))}")
    for result in retrieval_results:
        print(f"    - {result.get('title', 'N/A')} ({result.get('provider', 'unknown')})")
    
    return {
        **state,
        "retrieval_results": retrieval_results,
        "messages": [
            *state.get("messages", []),
            {
                "role": "retrieval",
                "content": f"Retrieved {len(retrieval_results)} results via {', '.join(dict.fromkeys(providers_used)) or 'fallback placeholder'}",
            },
        ],
    }
