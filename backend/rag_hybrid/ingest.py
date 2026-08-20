"""
Document Ingestion - Load documents into both SQLite and ChromaDB
"""

import json
from typing import Optional, List

from . import sqlite_manager
from . import chromadb_manager
from . import utils


def ingest_document(
    user_id: int,
    title: str,
    content: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: str = "manual",
    chunk_size: int = 300
) -> int:
    """
    Ingest a document into both SQLite and ChromaDB.
    
    Args:
        user_id: User ID
        title: Document title
        content: Full document content
        description: Optional description
        tags: Optional list of tags
        source: Source of document (manual, upload, web, etc)
        chunk_size: Target chunk size in characters
    
    Returns:
        Document ID
    """
    # Clean content
    content = utils.clean_text(content)
    
    # Generate hash for deduplication
    content_hash = utils.generate_content_hash(content)
    
    # Create document in SQLite
    filename = title.lower().replace(" ", "_") + ".txt"
    doc_id = sqlite_manager.add_document(
        user_id=user_id,
        title=title,
        filename=filename,
        content_hash=content_hash,
        file_size=len(content),
        description=description,
        tags=json.dumps(tags or []) if tags else None,
        source=source
    )
    
    # Chunk the document
    chunks = utils.chunk_text_by_sentences(content, chunk_size=chunk_size)
    
    # Add chunks to both stores
    chroma_ids = []
    for chunk_index, chunk_text in enumerate(chunks):
        # Add to SQLite
        chunk_id = sqlite_manager.add_document_chunk(
            doc_id=doc_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text
        )
        
        # Generate ChromaDB ID
        chroma_id = utils.generate_chunk_id(doc_id, chunk_index)
        chroma_ids.append(chroma_id)
        
        # Update SQLite with ChromaDB ID
        sqlite_manager.update_document_chunk_chroma_id(chunk_id, chroma_id)
    
    # Add chunks to ChromaDB
    try:
        metadatas = [
            {
                "doc_id": str(doc_id),
                "title": title,
                "tags": json.dumps(tags or []),
                "chunk_index": str(i),
                "source": source
            }
            for i in range(len(chunks))
        ]
        
        chromadb_manager.add_embeddings(
            collection_name="documents",
            ids=chroma_ids,
            documents=chunks,
            metadatas=metadatas
        )
    except Exception as e:
        print(f"Warning: ChromaDB ingestion failed: {e}")
    
    # Update chunk count
    sqlite_manager.update_document_chunk_count(doc_id, len(chunks))
    
    return doc_id


def ingest_file(
    user_id: int,
    file_path: str,
    title: Optional[str] = None,
    tags: Optional[List[str]] = None,
    source: str = "upload"
) -> int:
    """
    Ingest a text file into both stores.
    
    Args:
        user_id: User ID
        file_path: Path to text file
        title: Optional title (defaults to filename)
        tags: Optional tags
        source: Source identifier
    
    Returns:
        Document ID
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if not title:
        import os
        title = os.path.splitext(os.path.basename(file_path))[0]
    
    return ingest_document(
        user_id=user_id,
        title=title,
        content=content,
        tags=tags,
        source=source
    )
