#!/usr/bin/env python3
"""
RQ Worker startup script.

Run this to start processing background jobs:
    python -m src.worker

For production, run multiple workers:
    python -m src.worker &
    python -m src.worker &
"""
import logging
from rq import Worker, Queue, SimpleWorker
from src.jobs.queue import get_redis_connection, is_redis_available

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    if not is_redis_available():
        logger.error("Redis is not available. Make sure Redis is running:")
        logger.error("  docker-compose up -d redis")
        return 1
    
    conn = get_redis_connection()
    
    # Listen on default queue
    queues = [Queue("default", connection=conn)]
    
    logger.info("Starting RQ worker...")
    logger.info("Listening on queues: default")
    logger.info("Press Ctrl+C to stop")
    
    worker = SimpleWorker(queues, connection=conn)
    worker.work(with_scheduler=True)
    return 0


if __name__ == "__main__":
    exit(main())
