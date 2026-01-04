"""
Paper ingestion task for RQ job queue.

This module contains the background task for PDF ingestion that can be
executed by RQ workers. It extracts the logic from papers.py for better
separation of concerns and retry support.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _update_status(paper_id: str, status: str, chunk_count: int = None, pdf_path: str = None, error_message: str = None):
    """Helper to safely update paper status in a new transaction."""
    from src.db.sql_db import SessionLocal, UserPaper
    
    db = SessionLocal()
    try:
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper:
            paper.ingestion_status = status
            if chunk_count is not None:
                paper.chunk_count = chunk_count
            if pdf_path:
                paper.pdf_path = pdf_path
            if error_message:
                paper.error_message = error_message
            
            if status == "completed":
                paper.ingested_at = datetime.utcnow()
                
            db.commit()
            logger.info(f"Updated status for {paper_id} to {status}")
        else:
            logger.warning(f"Could not find paper {paper_id} to update status to {status}")
    except Exception as e:
        logger.error(f"Failed to update status for {paper_id}: {e}")
    finally:
        db.close()


def ingest_paper_task(paper_id: str):
    """
    RQ task for PDF ingestion pipeline.
    
    Steps:
    1. Download PDF from arXiv
    2. Parse with Docling
    3. Index with LlamaIndex into ChromaDB
    
    This function is designed to be run by an RQ worker.
    """
    import time
    from src.db.sql_db import SessionLocal, UserPaper
    from src.api.deps import get_job_manager
    from src.ingestion.pdf_downloader import PDFDownloader
    from src.ingestion.docling_parser import DoclingParser
    from src.ingestion.pipeline import IngestionPipeline
    
    logger.info(f"Starting PDF ingestion for: {paper_id}")
    
    # Check if already done
    db = SessionLocal()
    try:
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper and paper.ingestion_status == "completed":
            logger.info(f"Paper {paper_id} already ingested. Skipping.")
            return {"status": "skipped", "reason": "already_completed"}
    finally:
        db.close()

    # Get job manager for progress tracking
    job_manager = get_job_manager()

    # Fetch title for better UX
    db = SessionLocal()
    paper_title = None
    try:
        p = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if p:
            paper_title = p.title
    finally:
        db.close()
    
    init_status = job_manager.add_job(paper_id, title=paper_title or f"Paper {paper_id}")
    
    # Wait if queued (for in-memory job manager concurrency control)
    while init_status == "queued":
        time.sleep(2)
        current_status = job_manager.get_job_status(paper_id)
        if current_status != "queued":
            break
        
    if job_manager.get_job_status(paper_id) == "unknown":
        logger.warning(f"Job {paper_id} disappeared from manager while queuing. Aborting.")
        return {"status": "aborted", "reason": "job_disappeared"}

    try:
        # Step 1: Download PDF
        _update_status(paper_id, "downloading")
        job_manager.update_job(paper_id, "processing", step="downloading", progress=10)
        
        downloader = PDFDownloader()
        pdf_path = downloader.download(paper_id)
        logger.info(f"Downloaded PDF: {pdf_path}")
        
        # Step 2: Parse with Docling
        _update_status(paper_id, "parsing", pdf_path=str(pdf_path))
        job_manager.update_job(paper_id, "processing", step="parsing", progress=40)
        
        parser = DoclingParser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        logger.info(f"Parsed: {len(parsed_doc.sections)} sections.")
        
        # Step 3: Index with LlamaIndex
        _update_status(paper_id, "indexing")
        job_manager.update_job(paper_id, "processing", step="indexing", progress=70)
        
        pipeline = IngestionPipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        logger.info(f"Indexed {chunk_count} chunks for {paper_id}")
        
        # Update final status
        _update_status(paper_id, "completed", chunk_count=chunk_count)
        job_manager.update_job(paper_id, "completed", step="done", progress=100)
        
        logger.info(f"Ingestion completed for {paper_id}")
        return {"status": "completed", "chunk_count": chunk_count}
        
    except Exception as e:
        import traceback
        logger.error(f"Ingestion failed for {paper_id}: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        
        job_manager.update_job(paper_id, "failed", error=str(e))
        _update_status(paper_id, "failed", error_message=str(e))
        
        # Re-raise to let RQ handle retries
        raise
