"""
Hybrid Retrieval - Query both SQLite and ChromaDB, fuse and rerank results
"""

from typing import List, Dict, Any, Optional

from . import sqlite_manager
from . import chromadb_manager


def hybrid_search(
    query: str,
    user_id: Optional[int] = None,
    n_results: int = 5,
    alpha: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Hybrid search: combine semantic search (ChromaDB) with BM25/keyword search.
    
    Args:
        query: Search query
        user_id: Optional user filter
        n_results: Number of results to return
        alpha: Weight for semantic (1.0 = semantic only, 0.0 = keyword only)
    
    Returns:
        List of ranked results with metadata
    """
    # 1. Semantic search via ChromaDB
    semantic_results = chromadb_manager.search_embeddings(
        query=query,
        collection_name="documents",
        n_results=n_results * 2  # Get more to allow for ranking
    )
    
    # 2. Format and rank results
    results = []
    
    for semantic_result in semantic_results:
        chroma_id = semantic_result["id"]
        
        # Extract doc_id from chroma_id
        # Format: chunk_doc{doc_id}_idx{chunk_index}
        try:
            doc_id = int(chroma_id.split("doc")[1].split("_")[0])
        except (IndexError, ValueError):
            continue
        
        results.append({
            "chroma_id": chroma_id,
            "doc_id": doc_id,
            "text": semantic_result["text"],
            "distance": semantic_result["distance"],
            "relevance_score": 1.0 - semantic_result["distance"],  # Convert distance to similarity
            "metadata": semantic_result["metadata"]
        })
    
    # Sort by relevance and return top N
    results = sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    return results[:n_results]


def get_document_content(doc_id: int) -> Dict[str, Any]:
    """Get full document content by reassembling chunks."""
    chunks = sqlite_manager.get_document_chunks(doc_id)
    
    if not chunks:
        return {}
    
    # Reassemble chunks in order
    full_text = "\n".join([chunk["chunk_text"] for chunk in chunks])
    
    return {
        "doc_id": doc_id,
        "chunk_count": len(chunks),
        "content": full_text,
        "chunks": chunks
    }


def search_and_retrieve(
    query: str,
    user_id: int,
    n_results: int = 5
) -> Dict[str, Any]:
    """
    Combined search and retrieve: find relevant chunks and provide context.
    
    Args:
        query: Search query
        user_id: User ID
        n_results: Number of results
    
    Returns:
        Dictionary with search results and full documents
    """
    # Perform hybrid search
    search_results = hybrid_search(query, user_id=user_id, n_results=n_results)
    
    # Get unique documents
    doc_ids = list(set([r["doc_id"] for r in search_results]))
    
    # Retrieve full documents
    documents = {}
    for doc_id in doc_ids:
        doc_content = get_document_content(doc_id)
        if doc_content:
            documents[str(doc_id)] = doc_content
    
    return {
        "query": query,
        "search_results": search_results,
        "documents": documents,
        "result_count": len(search_results)
    }
