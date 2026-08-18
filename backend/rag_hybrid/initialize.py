"""
RAG System Initialization
Clean setup: creates schema and initializes databases with no sample data.
"""

import os
import sys
from pathlib import Path

from . import sqlite_manager
from . import chromadb_manager


def initialize_clean():
    """
    Initialize RAG system with clean databases.
    Creates SQLite schema and ChromaDB collection.
    """
    print("RAG System Initialization - Clean Setup")
    print("=" * 70)
    
    # 1. Initialize SQLite schema
    print("\n[1/3] Initializing SQLite database...")
    try:
        sqlite_manager.ensure_db_path()
        sqlite_manager.init_schema()
        print("  ✓ SQLite schema created")
        print(f"  Location: data/rag_hybrid.db")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    
    # 2. Initialize ChromaDB
    print("\n[2/3] Initializing ChromaDB...")
    try:
        chromadb_manager.ensure_chroma_path()
        collection = chromadb_manager.get_or_create_collection("documents")
        print("  ✓ ChromaDB collection created")
        print(f"  Location: {chromadb_manager.CHROMA_DB_PATH}")
        print(f"  Collection: documents")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    
    # 3. Verify setup
    print("\n[3/3] Verifying setup...")
    try:
        # Check SQLite
        if not sqlite_manager.db_exists():
            print("  ✗ SQLite database not found")
            return False
        print("  ✓ SQLite database ready")
        
        # Check ChromaDB
        chroma_path = Path(chromadb_manager.CHROMA_DB_PATH)
        if not chroma_path.exists():
            print("  ✗ ChromaDB directory not found")
            return False
        print("  ✓ ChromaDB ready")
        
        # Check collection stats
        stats = chromadb_manager.collection_stats("documents")
        print(f"  ✓ Collection stats: {stats['count']} embeddings")
        
    except Exception as e:
        print(f"  ✗ Verification failed: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ RAG System Ready!")
    print("\nYour databases are initialized and ready for data ingestion.")
    print("\nNext steps:")
    print("  1. Use rag_document_manager.py to add documents")
    print("  2. Query documents using the RAG API")
    print("\nDatabase locations:")
    print(f"  • SQLite: {sqlite_manager.SQLITE_DB_PATH}")
    print(f"  • ChromaDB: {chromadb_manager.CHROMA_DB_PATH}")
    
    return True


def reset_clean():
    """
    Reset RAG system to clean state.
    Clears all data while keeping schema intact.
    """
    print("RAG System Reset - Clean Data")
    print("=" * 70)
    print("\nThis will clear all data but keep the database schema.")
    
    confirm = input("\nContinue? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return False
    
    print("\n[1/2] Clearing SQLite data...")
    try:
        sqlite_manager.clear_all_data()
        print("  ✓ SQLite data cleared")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    
    print("\n[2/2] Clearing ChromaDB embeddings...")
    try:
        chromadb_manager.clear_collection("documents")
        print("  ✓ ChromaDB cleared")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ RAG System Reset!")
    print("\nDatabases cleared and ready for new data.")
    
    return True


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("RAG Hybrid System Initialization")
        print("=" * 70)
        print("\nUsage:")
        print("  python -m rag_hybrid.initialize init   # Initialize clean databases")
        print("  python -m rag_hybrid.initialize reset  # Reset and clear data")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "init":
        success = initialize_clean()
        sys.exit(0 if success else 1)
    elif command == "reset":
        success = reset_clean()
        sys.exit(0 if success else 1)
    else:
        print(f"Unknown command: {command}")
        print("Use 'init' or 'reset'")
        sys.exit(1)


if __name__ == "__main__":
    main()
