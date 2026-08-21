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


def get_connection():
    """Get SQLite database connection."""
    ensure_db_path()
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


def get_or_create_session(user_id: int, session_key: str) -> int:
    """Get or create a session. Returns session_id."""
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
        "INSERT INTO sessions (user_id, session_key) VALUES (?, ?)",
        (user_id, session_key)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    
    return session_id


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
        "sessions",
        "users"
    ]
    
    for table in tables:
        cursor.execute(f"DELETE FROM {table}")
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = '{table}'")
    
    conn.commit()
    conn.close()
