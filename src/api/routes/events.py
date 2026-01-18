"""
SSE (Server-Sent Events) endpoint for real-time updates.

Provides push-based event streaming for ingestion status and other real-time events.
"""
import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src.events.publisher import get_publisher

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/events/ingestion")
async def sse_ingestion_events(request: Request):
    """
    SSE endpoint for real-time ingestion status updates.
    
    Clients connect via EventSource and receive events when:
    - Paper ingestion starts
    - Status changes (downloading, parsing, indexing)
    - Ingestion completes or fails
    
    Returns:
        StreamingResponse with text/event-stream media type
    """
    
    async def event_generator():
        publisher = get_publisher()
        
        try:
            async for event in publisher.subscribe():
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break
                yield event
        except asyncio.CancelledError:
            logger.info("SSE stream cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            # Send error event before closing
            yield f"event: error\ndata: {str(e)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/events/health")
async def sse_health():
    """Health check for SSE service."""
    from src.jobs.queue import is_redis_available
    
    return {
        "status": "ok",
        "redis_available": is_redis_available(),
        "message": "SSE endpoint ready" if is_redis_available() else "SSE degraded (no Redis)"
    }
