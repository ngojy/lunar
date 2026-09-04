"""
SQLite Connection Manager and CRUD Helpers
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

SQLITE_DB_PATH = "data/rag_hybrid.db"


def ensure_db_path():
    """Ensure data directory exists."""
    os.makedirs(os.path.dirname(SQLITE_DB_PATH) or ".", exist_ok=True)


_schema_ready = False
_schema_initializing = False


def ensure_schema() -> None:
    """Lazily initialize the SQLite schema and run migrations.

    Safe to call from any DB-touching code path; the actual DDL/migration
    work runs only once per process. This guarantees the running server picks
    up new columns (e.g. sessions.title) even on pre-existing databases.
    """
    global _schema_ready, _schema_initializing
    if _schema_ready or _schema_initializing:
        return
    _schema_initializing = True
    try:
        init_schema()
        migrate_schema()
        _schema_ready = True
    finally:
        _schema_initializing = False


def migrate_schema() -> None:
    """Apply idempotent schema migrations for tables created before new columns existed."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        if "title" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT")
            conn.commit()
    finally:
        conn.close()


def get_connection():
    """Get SQLite database connection."""
    ensure_db_path()
    ensure_schema()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_schema():
    """Initialize database schema (create tables if they don't exist)."""
    from .schema import get_schema_ddl
    
    conn = get_connection()
    cursor = conn.cursor()
    
    for ddl in get_schema_ddl():
        cursor.execute(ddl)
    
    conn.commit()
    conn.close()


def db_exists():
    """Check if database file exists."""
    return Path(SQLITE_DB_PATH).exists()


def get_or_create_user(username: str, email: Optional[str] = None) -> int:
    """Get or create a user. Returns user_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Try to get existing user
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if user:
        conn.close()
        return user[0]
    
    # Create new user
    cursor.execute(
        "INSERT INTO users (username, email) VALUES (?, ?)",
        (username, email)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    
    return user_id


def get_or_create_session(user_id: int, session_key: str, title: Optional[str] = None) -> int:
    """Get or create a session. Returns session_id.

    If the session is newly created and a title is provided, it is stored.
    An already-existing session's title is left untouched.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM sessions WHERE session_key = ?",
        (session_key,)
    )
    session = cursor.fetchone()
    
    if session:
        conn.close()
        return session[0]
    
    cursor.execute(
        "INSERT INTO sessions (user_id, session_key, title) VALUES (?, ?, ?)",
        (user_id, session_key, title)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    
    return session_id


def get_session_title(session_key: str) -> Optional[str]:
    """Return the title for a session, or None if it has none / doesn't exist."""
    ensure_schema()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT title FROM sessions WHERE session_key = ?",
        (session_key,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return None
    title = row["title"] if isinstance(row, sqlite3.Row) else row[0]
    return title


def update_session_title(session_key: str, title: Optional[str]) -> bool:
    """Set the session title, but only if no title is set yet.

    This preserves the *initial* chat title: subsequent calls won't overwrite
    a title that was already persisted. Returns True if the title was set.
    """
    if title is None or title == "":
        return False
    ensure_schema()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE sessions SET title = ?, last_activity = CURRENT_TIMESTAMP "
        "WHERE session_key = ? AND (title IS NULL OR title = '')",
        (title, session_key)
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def list_sessions_with_counts() -> List[Dict[str, Any]]:
    """Return all sessions with title, message count, and last activity."""
    ensure_schema()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            s.session_key,
            s.title,
            COUNT(ch.id) as message_count,
            MAX(ch.created_at) as last_message_at
        FROM sessions s
        LEFT JOIN chat_history ch ON s.id = ch.session_id
        GROUP BY s.id, s.session_key, s.title
        ORDER BY MAX(ch.created_at) DESC
    """)
    
    sessions = []
    for row in cursor.fetchall():
        sessions.append({
            "session_id": row["session_key"],
            "title": row["title"] or None,
            "message_count": row["message_count"],
            "last_message_at": row["last_message_at"],
        })
    
    conn.close()
    return sessions


def add_chat_message(session_id: int, user_id: int, role: str, content: str) -> int:
    """Add a message to chat history. Returns message_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO chat_history (session_id, user_id, message_role, message_content)
           VALUES (?, ?, ?, ?)""",
        (session_id, user_id, role, content)
    )
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    
    return message_id


def get_session_history(session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
    """Get chat history for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, message_role, message_content, created_at 
           FROM chat_history 
           WHERE session_id = ? 
           ORDER BY created_at DESC 
           LIMIT ?""",
        (session_id, limit)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in reversed(rows)]


def add_document(
    user_id: int,
    title: str,
    filename: str,
    content_hash: str,
    file_size: int,
    description: Optional[str] = None,
    tags: Optional[str] = None,
    source: str = "manual",
    file_type: str = "txt"
) -> int:
    """Add document metadata. Returns document_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO documents 
           (user_id, filename, original_filename, title, description, tags, source, content_hash, file_size, file_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, filename, filename, title, description, tags, source, content_hash, file_size, file_type)
    )
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    
    return doc_id


def add_document_chunk(doc_id: int, chunk_index: int, chunk_text: str, chroma_id: Optional[str] = None) -> int:
    """Add a document chunk. Returns chunk_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO document_chunks (document_id, chunk_index, chunk_text, chunk_length, chroma_id)
           VALUES (?, ?, ?, ?, ?)""",
        (doc_id, chunk_index, chunk_text, len(chunk_text), chroma_id)
    )
    conn.commit()
    chunk_id = cursor.lastrowid
    conn.close()
    
    return chunk_id


def update_document_chunk_chroma_id(chunk_id: int, chroma_id: str) -> None:
    """Update ChromaDB ID for a chunk."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE document_chunks SET chroma_id = ? WHERE id = ?",
        (chroma_id, chunk_id)
    )
    conn.commit()
    conn.close()


def get_document_chunks(doc_id: int) -> List[Dict[str, Any]]:
    """Get all chunks for a document."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, chunk_index, chunk_text, chroma_id 
           FROM document_chunks 
           WHERE document_id = ? 
           ORDER BY chunk_index""",
        (doc_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_document_chunk_count(doc_id: int, count: int) -> None:
    """Update chunk count for a document."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE documents SET chunk_count = ? WHERE id = ?",
        (count, doc_id)
    )
    conn.commit()
    conn.close()


def get_documents(user_id: int) -> List[Dict[str, Any]]:
    """Get all documents for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, title, filename, file_size, chunk_count, created_at 
           FROM documents 
           WHERE user_id = ? 
           ORDER BY created_at DESC""",
        (user_id,)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def delete_document(doc_id: int) -> None:
    """Delete document and its chunks (cascaded)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get chunks before deleting (for ChromaDB cleanup)
    cursor.execute(
        "SELECT chroma_id FROM document_chunks WHERE document_id = ?",
        (doc_id,)
    )
    chunks = cursor.fetchall()
    
    # Delete document (chunks deleted by CASCADE)
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    
    return [row[0] for row in chunks if row[0]]


def clear_all_data() -> None:
    """Clear all data from tables (keep schema)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    tables = [
        "chat_history",
        "document_chunks",
        "documents",
        "agent_logs",
        "tasks",
        "agent_memory",
        "sessions",
        "users"
    ]
    
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
    
    conn.commit()
    conn.close()


# Agent Memory Functions
def add_memory(user_id: int, memory_type: str, key_concept: str, content: str, category: Optional[str] = None, relevance_score: float = 1.0) -> int:
    """Add or update an agent memory entry. Returns memory_id."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Try to update existing memory
    cursor.execute(
        "SELECT id FROM agent_memory WHERE user_id = ? AND memory_type = ? AND key_concept = ?",
        (user_id, memory_type, key_concept)
    )
    existing = cursor.fetchone()
    
    if existing:
        memory_id = existing[0]
        cursor.execute(
            """UPDATE agent_memory 
               SET content = ?, category = ?, relevance_score = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (content, category, relevance_score, memory_id)
        )
    else:
        cursor.execute(
            """INSERT INTO agent_memory (user_id, memory_type, key_concept, content, category, relevance_score)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, memory_type, key_concept, content, category, relevance_score)
        )
        memory_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    return memory_id


def get_memory(user_id: int, memory_type: Optional[str] = None, category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get agent memory entries filtered by type and category."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT id, memory_type, key_concept, content, category, relevance_score, usage_count, last_used FROM agent_memory WHERE user_id = ?"
    params = [user_id]
    
    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type)
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    query += " ORDER BY relevance_score DESC, usage_count DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_memory_by_key(user_id: int, memory_type: str, key_concept: str) -> Optional[Dict[str, Any]]:
    """Get a specific memory entry by key."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, memory_type, key_concept, content, category, relevance_score, usage_count, last_used 
           FROM agent_memory 
           WHERE user_id = ? AND memory_type = ? AND key_concept = ?""",
        (user_id, memory_type, key_concept)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def update_memory_usage(memory_id: int) -> None:
    """Increment usage count and update last_used timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """UPDATE agent_memory 
           SET usage_count = usage_count + 1, last_used = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (memory_id,)
    )
    conn.commit()
    conn.close()


def delete_memory(memory_id: int) -> None:
    """Delete a memory entry."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM agent_memory WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()


def search_memory(user_id: int, query_text: str, memory_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search memory entries by content and key_concept."""
    conn = get_connection()
    cursor = conn.cursor()
    
    sql = """SELECT id, memory_type, key_concept, content, category, relevance_score, usage_count 
             FROM agent_memory 
             WHERE user_id = ? AND (key_concept LIKE ? OR content LIKE ?)"""
    params = [user_id, f"%{query_text}%", f"%{query_text}%"]
    
    if memory_type:
        sql += " AND memory_type = ?"
        params.append(memory_type)
    
    sql += " ORDER BY relevance_score DESC, usage_count DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def delete_session(session_key: str) -> bool:
    """Delete a session by session_key, including all its chat history messages. Returns True if deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # First get the session ID
        cursor.execute("SELECT id FROM sessions WHERE session_key = ?", (session_key,))
        session = cursor.fetchone()
        
        if not session:
            conn.close()
            return False
        
        session_id = session[0]
        
        # Delete all chat history messages for this session
        cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (session_id,))
        
        # Delete the session itself
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting session {session_key}: {e}")
        conn.close()
        return False
