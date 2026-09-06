import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

# Import RAG modules
try:
    from rag_hybrid import ingest
except ImportError:
    ingest = None

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "uploads")
METADATA_FILE = os.path.join(UPLOAD_FOLDER, ".metadata.json")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

router = APIRouter(prefix="/api/storage", tags=["storage"])


class StorageFile(BaseModel):
    name: str
    size: int
    uploadedAt: str
    type: str
    path: str
    doc_id: Optional[int] = None  # RAG document ID


class FileListResponse(BaseModel):
    files: List[StorageFile]


class DeleteRequest(BaseModel):
    path: str
    doc_id: Optional[int] = None  # RAG document ID to delete


def load_metadata() -> Dict[str, str]:
    """Load metadata mapping filenames to document IDs."""
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_metadata(metadata: Dict[str, str]) -> None:
    """Save metadata mapping."""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)


def get_doc_id(filename: str) -> Optional[int]:
    """Get RAG doc_id for a file."""
    metadata = load_metadata()
    doc_id_str = metadata.get(filename)
    return int(doc_id_str) if doc_id_str else None


def set_doc_id(filename: str, doc_id: int) -> None:
    """Store RAG doc_id for a file."""
    metadata = load_metadata()
    metadata[filename] = str(doc_id)
    save_metadata(metadata)


def remove_doc_id(filename: str) -> None:
    """Remove doc_id mapping for a file."""
    metadata = load_metadata()
    metadata.pop(filename, None)
    save_metadata(metadata)


@router.get("/files", response_model=FileListResponse)
async def get_files():
    """Get list of all uploaded files with metadata"""
    try:
        files = []
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                # Skip metadata files
                if filename.startswith("."):
                    continue
                    
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    # Get file extension
                    _, ext = os.path.splitext(filename)
                    doc_id = get_doc_id(filename)
                    
                    files.append(StorageFile(
                        name=filename,
                        size=stat.st_size,
                        uploadedAt=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        type=ext.lstrip(".") if ext else "",
                        path=filepath,
                        doc_id=doc_id
                    ))
        
        # Sort by upload date descending
        files.sort(key=lambda f: f.uploadedAt, reverse=True)
        return FileListResponse(files=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file to the storage and ingest into RAG"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Sanitize filename
        filename = os.path.basename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Read file content
        content = await file.read()
        
        # Decode content if binary
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")
        
        # Save file
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Ingest into RAG if available
        doc_id = None
        if ingest:
            try:
                title = Path(filename).stem.replace("_", " ").title()
                doc_id = ingest.ingest_document(
                    user_id=1,  # Default user ID
                    title=title,
                    content=text_content,
                    description=f"Uploaded file: {filename}",
                    source="upload"
                )
                # Store doc_id mapping
                set_doc_id(filename, doc_id)
            except Exception as e:
                print(f"Warning: RAG ingestion failed for {filename}: {e}")
        
        return {
            "status": "success",
            "filename": filename,
            "size": len(content),
            "path": filepath,
            "doc_id": doc_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files")
async def delete_file(request: DeleteRequest):
    """Delete a file from storage and RAG"""
    try:
        filepath = request.path
        filename = os.path.basename(filepath)
        
        # Security: Ensure path is within upload folder
        if not os.path.abspath(filepath).startswith(os.path.abspath(UPLOAD_FOLDER)):
            raise HTTPException(status_code=403, detail="Invalid file path")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get doc_id from request or metadata
        doc_id = request.doc_id
        if not doc_id:
            doc_id = get_doc_id(filename)
        
        # Delete from RAG if available
        if doc_id and ingest:
            try:
                # Import RAG managers
                from rag_hybrid import sqlite_manager, chromadb_manager
                
                # Get chroma_ids from SQLite
                chroma_ids = sqlite_manager.delete_document(doc_id)
                
                # Delete from ChromaDB
                if chroma_ids:
                    chromadb_manager.delete_embeddings(chroma_ids)
            except Exception as e:
                print(f"Warning: RAG deletion failed for doc_id {doc_id}: {e}")
        
        # Delete file from disk
        os.remove(filepath)
        
        # Remove doc_id mapping
        remove_doc_id(filename)
        
        return {"status": "success", "message": "File and RAG data deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
