"""
Paper ingestion task for RQ job queue.

This module contains the background task for PDF ingestion that can be
executed by RQ workers. It extracts the logic from papers.py for better
separation of concerns and retry support.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _update_status(paper_id: str, status: str, chunk_count: int = None, pdf_path: str = None, error_message: str = None, title: str = None):
    """Helper to safely update paper status in a new transaction."""
    from src.db.sql_db import SessionLocal, UserPaper
    
    db = SessionLocal()
    paper_title = title
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
            
            # Capture title for SSE event
            paper_title = paper.title or paper_title
                
            db.commit()
            logger.info("Status updated", extra={"paper_id": paper_id, "status": status})
            
            # Emit SSE Event via Redis Pub/Sub
            try:
                from src.events.publisher import publish_ingestion_event
                
                # Calculate progress for event
                progress_map = {
                    "pending": 0,
                    "queued": 5,
                    "downloading": 15,
                    "parsing": 45,
                    "indexing": 75,
                    "completed": 100,
                    "failed": 100
                }
                progress = progress_map.get(status, 50)
                
                publish_ingestion_event(
                    paper_id=paper_id,
                    status=status,
                    progress=progress,
                    step=status,
                    title=paper_title or "",
                    error=error_message
                )
            except Exception as sse_err:
                # Don't fail the ingestion if SSE fails
                logger.warning(f"Failed to publish SSE event: {sse_err}")
        else:
            logger.warning("Paper not found for status update", extra={"paper_id": paper_id, "status": status})
    except Exception as e:
        logger.error("Failed to update status", extra={"paper_id": paper_id, "error": str(e)})
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
    from src.db.sql_db import SessionLocal, UserPaper
    from src.ingestion.pdf_downloader import PDFDownloader
    from src.ingestion.docling_parser import DoclingParser
    from src.ingestion.pipeline import IngestionPipeline
    
    logger.info("Starting PDF ingestion", extra={"paper_id": paper_id})
    
    # Check if already done
    db = SessionLocal()
    try:
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper and paper.ingestion_status == "completed":
            logger.info("Paper already ingested, skipping", extra={"paper_id": paper_id})
            return {"status": "skipped", "reason": "already_completed"}
    finally:
        db.close()
    
    try:
        # Step 1: Download PDF
        _update_status(paper_id, "downloading")
        
        downloader = PDFDownloader()
        pdf_path = downloader.download(paper_id)
        logger.info("PDF downloaded", extra={"paper_id": paper_id, "pdf_path": str(pdf_path)})
        
        # Step 2: Parse with Docling
        _update_status(paper_id, "parsing", pdf_path=str(pdf_path))
        
        parser = DoclingParser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        logger.info("PDF parsed", extra={"paper_id": paper_id, "sections": len(parsed_doc.sections)})
        
        # Step 3: Index with LlamaIndex
        _update_status(paper_id, "indexing")
        
        pipeline = IngestionPipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        logger.info("Indexed into vector store", extra={"paper_id": paper_id, "chunk_count": chunk_count})
        
        # Update final status
        _update_status(paper_id, "completed", chunk_count=chunk_count)
        
        logger.info("Ingestion completed", extra={"paper_id": paper_id, "chunk_count": chunk_count})
        return {"status": "completed", "chunk_count": chunk_count}
        
    except Exception as e:
        logger.exception("Ingestion failed", extra={"paper_id": paper_id, "error_type": type(e).__name__})
        
        _update_status(paper_id, "failed", error_message=str(e))
        
        # Re-raise to let RQ handle retries
        raise
