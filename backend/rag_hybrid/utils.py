"""
Utility Functions for RAG System
- Text chunking, ID generation, content hashing, text cleaning
"""

import hashlib
import re
from typing import List


def generate_content_hash(content: str) -> str:
    """Generate MD5 hash of content for deduplication."""
    return hashlib.md5(content.encode()).hexdigest()


def generate_chunk_id(doc_id: int, chunk_index: int) -> str:
    """Generate unique chunk ID."""
    return f"chunk_doc{doc_id}_idx{chunk_index}"


def chunk_text_by_sentences(
    text: str,
    chunk_size: int = 300,
    overlap: int = 50
) -> List[str]:
    """
    Split text into chunks by sentences with optional overlap.
    
    Args:
        text: Full text to chunk
        chunk_size: Target chunk size in characters
        overlap: Overlap size between chunks
    
    Returns:
        List of chunk strings
    """
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # Add sentence to current chunk
        test_chunk = current_chunk + " " + sentence if current_chunk else sentence
        
        if len(test_chunk) > chunk_size and current_chunk:
            # Current chunk is full, save it
            chunks.append(current_chunk.strip())
            
            # Start new chunk with overlap
            if overlap > 0 and chunks:
                # Rewind to create overlap
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            # Add to current chunk
            current_chunk = test_chunk
    
    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def clean_text(text: str) -> str:
    """
    Clean text: remove extra whitespace, normalize line breaks.
    
    Args:
        text: Text to clean
    
    Returns:
        Cleaned text
    """
    # Normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    
    # Remove extra whitespace
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n\n+', '\n', text)
    
    return text.strip()


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max length while preserving meaning."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1].rstrip() + "…"


def extract_summary(text: str, max_length: int = 200) -> str:
    """Extract first sentence or truncated summary from text."""
    # Try to get first sentence
    match = re.search(r'^[^.!?]*[.!?]', text)
    if match:
        summary = match.group(0)
    else:
        summary = text
    
    return truncate_text(summary, max_length)
