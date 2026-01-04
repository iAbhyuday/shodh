import logging
from typing import Dict, Optional, List
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

class IngestionJobManager:
    _instance = None
    _lock = Lock()

    def __init__(self):
        # Map paper_id -> job_info
        self.active_jobs: Dict[str, Dict] = {}
        # Queue for jobs waiting for a slot
        self.queued_jobs: Dict[str, Dict] = {}
        self.queue_order: List[str] = []
        self.MAX_JOBS = 10

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def add_job(self, paper_id: str, title: str = None) -> str:
        """
        Register a new ingestion job.
        Returns initial status: 'pending' (can run) or 'queued' (must wait).
        """
        with self._lock:
            # Check if already exists
            if paper_id in self.active_jobs:
                return self.active_jobs[paper_id]["status"]
            if paper_id in self.queued_jobs:
                return "queued"

            new_job = {
                "paper_id": paper_id,
                "title": title or paper_id,
                "status": "pending",
                "progress": 0,
                "start_time": datetime.utcnow().isoformat(),
                "step": "queued"
            }

            # Logic:
            # 1. Count running jobs
            running_jobs = [j for j in self.active_jobs.values() if j["status"] not in ("completed", "failed")]
            
            if len(running_jobs) < self.MAX_JOBS:
                # We have a slot for execution.
                # Must ensure `active_jobs` total size <= 10 (evict completed if needed)
                if len(self.active_jobs) >= self.MAX_JOBS:
                    # Evict oldest completed/failed
                    candidates = [j for j in self.active_jobs.values() if j["status"] in ("completed", "failed")]
                    if candidates:
                        # Sort by start_time ascending (oldest first)
                        candidates.sort(key=lambda x: x["start_time"])
                        to_remove = candidates[0]
                        del self.active_jobs[to_remove["paper_id"]]
                        logger.info(f"JobManager: Evicted old job {to_remove['paper_id']} to make room.")
                    else:
                        # Should unlikely happen if running < MAX but len >= MAX
                        # Means all are running? Contradiction.
                        # Unless MAX changed.
                        pass
                
                self.active_jobs[paper_id] = new_job
                logger.info(f"JobManager: Added job {paper_id} to active (Running: {len(running_jobs)+1}/{self.MAX_JOBS})")
                return "pending"
            else:
                # No execution slots. Queue it.
                new_job["status"] = "queued"
                self.queued_jobs[paper_id] = new_job
                self.queue_order.append(paper_id)
                logger.info(f"JobManager: Queued job {paper_id}. Queue size: {len(self.queue_order)}")
                return "queued"

    def update_job(self, paper_id: str, status: str, step: str = None, progress: int = None, error: str = None):
        """Update an existing job's status."""
        with self._lock:
            if paper_id in self.active_jobs:
                job = self.active_jobs[paper_id]
                job["status"] = status
                if step:
                    job["step"] = step
                if progress is not None:
                    job["progress"] = progress
                if error:
                    job["error"] = error
                
                logger.info(f"JobManager: Updated {paper_id} -> {status}")

                # If job finished, check queue for promotions
                if status in ("completed", "failed"):
                    self._process_queue_unsafe()

            elif paper_id in self.queued_jobs:
                 # Should not happen typically unless updated while queued?
                 pass
            else:
                logger.warning(f"JobManager: Update failed, job {paper_id} not found")

    def _process_queue_unsafe(self):
        """Check if we can move a queued job to active. (Must be called within lock)"""
        if not self.queue_order:
            return

        # Check running count
        running_jobs = [j for j in self.active_jobs.values() if j["status"] not in ("completed", "failed")]
        
        if len(running_jobs) < self.MAX_JOBS:
            # We have a slot!
            next_id = self.queue_order.pop(0)
            job = self.queued_jobs.pop(next_id)
            
            # Make room in active_jobs if needed (evict completed)
            if len(self.active_jobs) >= self.MAX_JOBS:
                candidates = [j for j in self.active_jobs.values() if j["status"] in ("completed", "failed")]
                if candidates:
                    candidates.sort(key=lambda x: x["start_time"])
                    to_remove = candidates[0]
                    del self.active_jobs[to_remove["paper_id"]]
            
            job["status"] = "pending" # Ready to run
            self.active_jobs[next_id] = job
            logger.info(f"JobManager: Promoted {next_id} from queue to active.")

    def get_job_status(self, paper_id: str) -> str:
        with self._lock:
            if paper_id in self.active_jobs:
                return self.active_jobs[paper_id]["status"]
            if paper_id in self.queued_jobs:
                return "queued"
            return "unknown"

    def get_all_jobs(self) -> List[Dict]:
        """Return all tracked jobs + queued jobs."""
        with self._lock:
            # Combine active and queued
            all_j = list(self.active_jobs.values()) + list(self.queued_jobs.values())
            return sorted(all_j, key=lambda x: x['start_time'], reverse=True)

    def get_job(self, paper_id: str) -> Optional[Dict]:
        with self._lock:
            return self.active_jobs.get(paper_id)

    def get_all_jobs(self) -> List[Dict]:
        """Return all tracked jobs (active and recently completed)."""
        with self._lock:
            # Sort by start time desc
            return sorted(self.active_jobs.values(), key=lambda x: x['start_time'], reverse=True)

    def clear_job(self, paper_id: str):
        """Remove a job from tracking (e.g. after user dismisses notification)."""
        with self._lock:
            if paper_id in self.active_jobs:
                del self.active_jobs[paper_id]

# Singleton accessor
job_manager = IngestionJobManager.get_instance()
