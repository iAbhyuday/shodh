"""
Server-Sent Events (SSE) Publisher using Redis Pub/Sub.

This module provides real-time event streaming for ingestion status updates.
Uses Redis Pub/Sub to support multi-worker deployments.
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Channel name for ingestion events
INGESTION_CHANNEL = "shodh:ingestion:events"


class SSEEventPublisher:
    """
    Redis-backed SSE event publisher.
    
    - publish(): Sync method called from RQ workers to push events
    - subscribe(): Async generator for SSE endpoint to yield events
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        from src.core.config import get_settings
        self.redis_url = redis_url or get_settings().REDIS_URL
        self._sync_redis = None
    
    def _get_sync_redis(self):
        """Get synchronous Redis connection for publishing."""
        if self._sync_redis is None:
            from redis import Redis
            try:
                self._sync_redis = Redis.from_url(self.redis_url)
                self._sync_redis.ping()
            except Exception as e:
                logger.warning(f"Redis Pub/Sub unavailable: {e}")
                return None
        return self._sync_redis
    
    def publish(self, event_type: str, data: dict) -> bool:
        """
        Publish an event to Redis Pub/Sub (synchronous).
        
        Called from RQ workers or background tasks.
        
        Args:
            event_type: Type of event (e.g., "ingestion_status")
            data: Event payload
            
        Returns:
            True if published successfully, False otherwise
        """
        redis = self._get_sync_redis()
        if redis is None:
            logger.debug("Redis unavailable, event not published")
            return False
        
        try:
            message = json.dumps({
                "event": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
            redis.publish(INGESTION_CHANNEL, message)
            logger.debug(f"Published event: {event_type} for {data.get('paper_id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    async def subscribe(self) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE-formatted events.
        
        Used by the SSE endpoint to stream events to clients.
        
        Yields:
            SSE-formatted strings (data: {...}\n\n)
        """
        # Use redis.asyncio instead of deprecated aioredis (Python 3.11+ compatible)
        from redis.asyncio import Redis as AsyncRedis
        
        redis = None
        pubsub = None
        try:
            redis = AsyncRedis.from_url(self.redis_url)
            pubsub = redis.pubsub()
            await pubsub.subscribe(INGESTION_CHANNEL)
            
            logger.info("SSE client subscribed to ingestion events")
            
            while True:
                try:
                    # Wait for message with timeout for keepalive
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=30.0
                    )
                    
                    if message is not None and message["type"] == "message":
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        yield f"data: {data}\n\n"
                        
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
                    
        except asyncio.CancelledError:
            logger.info("SSE subscription cancelled")
            raise
        except Exception as e:
            logger.error(f"SSE subscription error: {e}")
            raise
        finally:
            try:
                if pubsub:
                    await pubsub.unsubscribe(INGESTION_CHANNEL)
                if redis:
                    await redis.close()
            except Exception:
                pass


# Singleton instance
_publisher: Optional[SSEEventPublisher] = None


def get_publisher() -> SSEEventPublisher:
    """Get the singleton SSE event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = SSEEventPublisher()
    return _publisher


def publish_ingestion_event(
    paper_id: str,
    status: str,
    progress: int = 0,
    step: str = "",
    title: str = "",
    error: Optional[str] = None
) -> bool:
    """
    Convenience function to publish ingestion status events.
    
    Args:
        paper_id: ID of the paper being ingested
        status: Current status (downloading, parsing, indexing, completed, failed)
        progress: Progress percentage (0-100)
        step: Current step description
        title: Paper title for display
        error: Error message if failed
        
    Returns:
        True if published successfully
    """
    return get_publisher().publish("ingestion_status", {
        "paper_id": paper_id,
        "status": status,
        "progress": progress,
        "step": step,
        "title": title,
        "error": error
    })
