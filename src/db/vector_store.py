"""
Vector store utilities for ChromaDB.

This module provides the ChromaDB client factory function.
The actual vector store operations are handled by LlamaIndex's ChromaVectorStore
in retriever.py and pipeline.py.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from src.core.config import get_settings


def get_chroma_client(settings=None):
    """
    Get ChromaDB client based on configuration.
    
    Returns HttpClient if VECTOR_DB_HOST is set, otherwise PersistentClient.
    
    Args:
        settings: Optional settings object. If None, fetches from config.
        
    Returns:
        ChromaDB client instance
    """
    if settings is None:
        settings = get_settings()
        
    if settings.VECTOR_DB_HOST:
        return chromadb.HttpClient(
            host=settings.VECTOR_DB_HOST,
            port=settings.VECTOR_DB_PORT,
            settings=ChromaSettings()
        )
    return chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
