"""
FastAPI dependencies for dependency injection.

This module provides centralized dependency functions that replace
module-level singletons for better testability and thread safety.
"""
from functools import lru_cache
from typing import Generator

from sqlalchemy.orm import Session

from src.db.sql_db import SessionLocal
from src.jobs.queue import get_redis_connection, get_queue


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Note: This is also defined in sql_db.py. This re-export provides
    a single import location for all dependencies.
    """
    from src.db.sql_db import get_db as _get_db
    yield from _get_db()


@lru_cache()
def get_redis():
    """Get Redis connection as a FastAPI dependency."""
    return get_redis_connection()


def get_rq_queue(name: str = "default"):
    """Get RQ queue as a FastAPI dependency."""
    return get_queue(name)
