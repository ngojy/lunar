"""
ChromaDB Client Manager and Collection Helpers
"""

import os
from typing import Optional, List, Dict, Any

CHROMA_DB_PATH = "data/chroma_db"


def ensure_chroma_path():
    """Ensure ChromaDB directory exists."""
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)


def get_chroma_client():
    """Get ChromaDB persistent client."""
    try:
        import chromadb
        ensure_chroma_path()
        return chromadb.PersistentClient(path=CHROMA_DB_PATH)
    except ImportError:
        raise ImportError(
            "ChromaDB not installed. Install with: pip install chromadb"
        )


def get_or_create_collection(collection_name: str = "documents"):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def add_embeddings(
    collection_name: str,
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict[str, Any]]
) -> None:
    """Add documents with embeddings to ChromaDB."""
    collection = get_or_create_collection(collection_name)
    collection.add(ids=ids, documents=documents, metadatas=metadatas)


def search_embeddings(
    query: str,
    collection_name: str = "documents",
    n_results: int = 5
) -> List[Dict[str, Any]]:
    """Search ChromaDB by semantic similarity."""
    collection = get_or_create_collection(collection_name)
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    # Format results
    formatted = []
    if results and results.get("ids") and len(results["ids"]) > 0:
        for i, doc_id in enumerate(results["ids"][0]):
            formatted.append({
                "id": doc_id,
                "text": results["documents"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else 0,
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {}
            })
    
    return formatted


def delete_embeddings(ids: List[str], collection_name: str = "documents") -> None:
    """Delete embeddings from ChromaDB."""
    collection = get_or_create_collection(collection_name)
    collection.delete(ids=ids)


def clear_collection(collection_name: str = "documents") -> None:
    """Clear all embeddings from a collection."""
    try:
        client = get_chroma_client()
        # Delete and recreate collection
        client.delete_collection(name=collection_name)
        get_or_create_collection(collection_name)
    except Exception as e:
        # Collection might not exist, that's okay
        pass


def collection_stats(collection_name: str = "documents") -> Dict[str, Any]:
    """Get collection statistics."""
    collection = get_or_create_collection(collection_name)
    
    try:
        result = collection.get()
        return {
            "count": len(result.get("ids", [])) if result else 0,
            "has_data": bool(result and result.get("ids"))
        }
    except Exception as e:
        return {"count": 0, "has_data": False, "error": str(e)}
