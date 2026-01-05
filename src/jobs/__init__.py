"""Jobs module for background task processing."""
from src.jobs.queue import get_queue, get_redis_connection, is_redis_available
from src.jobs.ingestion import ingest_paper_task

__all__ = ["get_queue", "get_redis_connection", "is_redis_available", "ingest_paper_task"]

