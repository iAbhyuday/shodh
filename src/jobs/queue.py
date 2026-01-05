"""Redis connection and job queue setup."""
import logging
from redis import Redis
from rq import Queue
from src.core.config import get_settings

logger = logging.getLogger(__name__)

_redis_connection = None


def get_redis_connection() -> Redis:
    """
    Get or create Redis connection.
    Uses a module-level singleton for efficiency.
    """
    global _redis_connection
    if _redis_connection is None:
        settings = get_settings()
        try:
            _redis_connection = Redis.from_url(settings.REDIS_URL)
            # Test connection
            _redis_connection.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_URL}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Jobs will run synchronously.")
            return None
    return _redis_connection


def get_queue(name: str = "default") -> Queue | None:
    """
    Get RQ queue for enqueueing jobs.
    Returns None if Redis is unavailable.
    """
    conn = get_redis_connection()
    if conn is None:
        return None
    return Queue(name, connection=conn)


def is_redis_available() -> bool:
    """Check if Redis is available."""
    return get_redis_connection() is not None

