"""
FastAPI dependencies for dependency injection.

This module provides centralized dependency functions that replace
module-level singletons for better testability and thread safety.
"""
from functools import lru_cache
from src.services.ingestion_manager import IngestionJobManager


@lru_cache
def get_job_manager() -> IngestionJobManager:
    """
    Get the singleton IngestionJobManager instance.
    
    Uses lru_cache to ensure a single instance per worker process.
    For multi-worker deployments with shared state, consider Redis.
    """
    return IngestionJobManager.get_instance()
