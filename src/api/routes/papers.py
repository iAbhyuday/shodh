from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
import os
from sqlalchemy.orm import Session
from datetime import datetime, date
import requests
import logging

from src.db.sql_db import get_db, UserPaper, SessionLocal
from src.api.schemas import PaperActionRequest
from src.jobs.queue import get_queue, is_redis_available
from rq import Retry

router = APIRouter()
logger = logging.getLogger(__name__)


def enqueue_ingestion(paper_id: str, background_tasks=None) -> dict:
    """
    Enqueue a paper ingestion job via RQ.
    Falls back to BackgroundTasks if Redis is unavailable.
    
    Returns dict with status and job_id if applicable.
    """
    from src.jobs.ingestion import ingest_paper_task
    
    queue = get_queue()
    
    if queue is not None:
        # Use RQ with proper retry configuration
        job = queue.enqueue(
            ingest_paper_task,
            paper_id,
            job_timeout="30m",  # 30 min timeout for large PDFs
            retry=Retry(max=3, interval=[60, 120, 240]),  # Retry with backoff
        )
        logger.info(f"Enqueued ingestion job {job.id} for paper {paper_id}")
        return {"queued": True, "job_id": job.id, "method": "rq"}
    elif background_tasks is not None:
        # Fallback to FastAPI BackgroundTasks - use the same task function
        logger.warning("Redis unavailable, falling back to BackgroundTasks")
        background_tasks.add_task(ingest_paper_task, paper_id)
        return {"queued": True, "job_id": None, "method": "background_tasks"}
    else:
        # No queue available, run synchronously (not recommended)
        logger.warning("No queue available, running ingestion synchronously")
        ingest_paper_task(paper_id)
        return {"queued": False, "job_id": None, "method": "sync"}

# --- Lazy Imports / Helper Functions ---

def get_pdf_downloader():
    from src.ingestion.pdf_downloader import PDFDownloader
    return PDFDownloader()

def get_docling_parser():
    from src.ingestion.docling_parser import DoclingParser
    return DoclingParser()

def get_ingestion_pipeline():
    from src.ingestion.pipeline import IngestionPipeline
    return IngestionPipeline()

def fetch_daily_papers(date_str: str = None, limit: int = 100):
    # Fetch from huggingface daily papers or arxiv directly if needed
    # For now, using huggingface daily papers API via requests
    today = date.today()
    url = "https://huggingface.co/api/daily_papers"
    if date_str:
        url = f"{url}?date={date_str}"
    try:
        # SSL verification is disabled in DEBUG_MODE for local development
        from src.core.config import get_settings
        resp = requests.get(url, verify=not get_settings().DEBUG_MODE, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # Data is list of papers. Flatten/Format.
        papers = []
        for p in data[:limit]:
            # HF API returns dict with 'paper' key usually
            paper_info = p.get('paper', p)
            papers.append({
                "id": paper_info['id'],
                "title": paper_info['title'],
                "abstract": paper_info.get('ai_summary', 'No summary available.') if 'ai_summary' in paper_info else paper_info.get('summary', 'No summary available.'),
                "source": "Hugging Face Daily",
                'thumbnail': p.get('thumbnail', ""),
                "url": f"https://arxiv.org/abs/{paper_info['id']}",
                "published_date": paper_info.get('publishedAt', str(today)),
                "authors": ", ".join(
                    [a['name'] for a in paper_info.get('authors', [])]),
                    "metrics": {
                        "tags": paper_info.get('ai_keywords', []),
                        "core_idea": paper_info.get('ai_summary', '')
                    },
                    "github_url": paper_info.get('githubRepo'),
                    "project_page": paper_info.get('projectPage')
                })
        return papers
    except Exception as e:
        print(f"Error fetching daily papers: {e}")
        return []

def search_papers(query: str, limit: int = 50):
    query = query.strip()
    if not query:
        return fetch_daily_papers(limit=limit)
    today = date.today()
    url = "https://huggingface.co/api/papers/search"
    try:
        # SSL verification is disabled in DEBUG_MODE for local development
        from src.core.config import get_settings
        resp = requests.get(url, params={"q": query, "limit": limit}, verify=not get_settings().DEBUG_MODE, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        papers = []
        for p in data[:limit]:
            # HF API returns dict with 'paper' key usually
            paper_info = p.get('paper', p)
            papers.append({
                "id": paper_info['id'], # Arxiv ID usually
                "title": paper_info['title'],
                "abstract": paper_info.get('summary', 'No summary available.'),
                "source": "Hugging Face Daily",
                "thumbnail": p.get('thumbnail', ''),
                "url": f"https://arxiv.org/abs/{paper_info['id']}",
                "published_date": paper_info.get('publishedAt', str(today)),
                "authors": ", ".join([a['name'] for a in paper_info.get('authors', [])]),
                "metrics": {"tags": paper_info.get('ai_keywords', []), "core_idea": paper_info.get('ai_summary', '')},
                "github_url": paper_info.get('githubRepo'),
                "project_page": paper_info.get('projectPage')
            })
        return papers
    except Exception as e:
        print(f"Error searching papers: {e}")
        return []


# --- Endpoints ---

@router.get("/feed")
def get_feed(
    date: str = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get daily papers feed from HuggingFace.
    Enriches with user state (is_saved, is_favorited) from SQL.
    Supports filtering by date (YYYY-MM-DD).
    Supports pagination via page parameter (1-indexed).
    """
    papers = fetch_daily_papers(date_str=date, limit=500)

    # Calculate pagination
    total_papers = len(papers)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_papers = papers[start_idx:end_idx]

    # Enrich with SQL state
    user_papers = db.query(UserPaper).filter(
        UserPaper.paper_id.in_([p['id'] for p in paginated_papers])).all()
    state_map = {up.paper_id: up for up in user_papers}
    
    for p in paginated_papers:
        up = state_map.get(p['id'])
        p['is_favorited'] = up.is_favorited if up else False
        p['is_saved'] = up.is_saved if up else False
        p['project_ids'] = [proj.id for proj in up.projects] if up else []
        
    return {
        "papers": paginated_papers,
        "total": total_papers,
        "page": page,
        "limit": limit,
        "total_pages": (total_papers + limit - 1) // limit  # Ceiling division
    }

@router.get("/search")
def search_papers_endpoint(
    q: str = Query(""),
    page: int = 1,
    limit: int = 50,
    sort: str = "date_desc",
    tags: List[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Search papers via Hugging Face API.
    Supports sorting (date_desc, date_asc, title_asc) and multi-tag filtering.
    If q is empty, returns latest/trending papers filtered by tags.
    """
    query = q.lower() if q else ""
    today = date.today()
    # Fetch papers. If q is empty, search_papers("") should return latest/trending.
    # We fetch more to allow for valid filtering intersection. 
    # HF limit is 120.
    papers = search_papers(q, limit=100)
    
    # 1. Collect all available tags (facets)
    all_tags = set()
    for p in papers:
        for t in (p['metrics'].get('tags') or []):
            all_tags.add(t)
    sorted_tags = sorted(list(all_tags))

    # 2. Filter by Tags (Intersection: Paper must have ALL selected tags)
    if tags:
        required_tags = {t.lower() for t in tags}
        filtered = []
        for p in papers:
             p_tags = {t.lower() for t in (p['metrics'].get('tags') or [])}
             if required_tags.issubset(p_tags):
                 filtered.append(p)
        papers = filtered

    # 3. Sort
    if sort == "date_asc":
        papers.sort(key=lambda x: x['published_date'])
    elif sort == "title_asc":
        papers.sort(key=lambda x: x['title'].lower())
    elif sort == "title_desc":
        papers.sort(key=lambda x: x['title'].lower(), reverse=True)
    else: # date_desc (default)
        papers.sort(key=lambda x: x['published_date'], reverse=True)

    # Calculate pagination
    total_papers = len(papers)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_papers = papers[start_idx:end_idx]

    # Enrich with SQL state
    user_papers = db.query(UserPaper).filter(
        UserPaper.paper_id.in_([p['id'] for p in paginated_papers])).all()
    state_map = {up.paper_id: up for up in user_papers}
    
    for p in paginated_papers:
        up = state_map.get(p['id'])
        p['is_favorited'] = up.is_favorited if up else False
        p['is_saved'] = up.is_saved if up else False
        p['project_ids'] = [proj.id for proj in up.projects] if up else []
        
    return {
        "papers": paginated_papers,
        "total": total_papers,
        "page": page,
        "limit": limit,
        "total_pages": (total_papers + limit - 1) // limit,
        "tags": sorted_tags # Return facets
    }

@router.post("/favorite")
def toggle_favorite(action: PaperActionRequest, db: Session = Depends(get_db)):
    paper = db.query(UserPaper).filter(UserPaper.paper_id == action.paper_id).first()
    if not paper:
        paper = UserPaper(
            paper_id=action.paper_id,
            title=action.title,
            summary=action.summary,
            authors=action.authors,
            is_favorited=True
        )
        db.add(paper)
    else:
        paper.is_favorited = not paper.is_favorited
    
    db.commit()
    return {"status": "success", "is_favorited": paper.is_favorited}

@router.post("/save")
def toggle_save(action: PaperActionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    paper = db.query(UserPaper).filter(UserPaper.paper_id == action.paper_id).first()
    if not paper:
        paper = UserPaper(
            paper_id=action.paper_id,
            title=action.title,
            summary=action.summary,
            notes=action.notes,
            user_notes=action.user_notes,
            authors=action.authors,
            url=action.url,
            published_date=action.published_date,
            github_url=action.github_url,
            project_page=action.project_page,
            thumbnail=action.thumbnail,
            mindmap_json=action.mindmap_json,
            is_saved=True
        )
        db.add(paper)
    else:
        # Update metadata if re-saving
        paper.is_saved = not paper.is_saved
        if paper.is_saved:
            # Update all fields when saving
            paper.title = action.title or paper.title
            paper.summary = action.summary or paper.summary
            paper.notes = action.notes or paper.notes
            paper.user_notes = action.user_notes or paper.user_notes
            paper.authors = action.authors or paper.authors
            paper.url = action.url or paper.url
            paper.published_date = action.published_date or paper.published_date
            paper.github_url = action.github_url or paper.github_url
            paper.project_page = action.project_page or paper.project_page
            paper.thumbnail = action.thumbnail or paper.thumbnail
            if action.mindmap_json:
                paper.mindmap_json = action.mindmap_json
        
    db.commit()
    
    # Note: Ingestion is only triggered when a paper is added to a project,
    # not when simply saving to library. See projects.py add_paper_to_project.
        
    return {
        "status": "success", 
        "is_saved": paper.is_saved,
        "ingestion_status": paper.ingestion_status
    }

@router.get("/library/saved")
def get_saved_papers(db: Session = Depends(get_db)):
    """Get all saved papers."""
    papers = db.query(UserPaper).filter(UserPaper.is_saved == True).order_by(UserPaper.updated_at.desc()).all()
    
    # Format response similar to feed
    result = []
    for p in papers:
        result.append({
            "id": p.paper_id,
            "title": p.title,
            "abstract": p.summary,
            "source": "ArXiv", # Defaulting to ArXiv for now as that's our primary source
            "url": p.url,
            "published_date": p.published_date,
            "authors": p.authors,
            "is_favorited": p.is_favorited,
            "is_saved": True,
            "github_url": p.github_url,
            "project_page": p.project_page,
            "thumbnail": p.thumbnail,
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": [] # We don't store tags in SQL currently
            },
            "ingestion_status": p.ingestion_status
        })
    return result

@router.get("/library/favorites")
def get_favorite_papers(db: Session = Depends(get_db)):
    """Get all favorited papers."""
    papers = db.query(UserPaper).filter(UserPaper.is_favorited == True).order_by(UserPaper.updated_at.desc()).all()
    
    # Format response similar to feed
    result = []
    for p in papers:
        result.append({
            "id": p.paper_id,
            "title": p.title,
            "abstract": p.summary,
            "source": "ArXiv",
            "url": p.url,
            "published_date": p.published_date,
            "authors": p.authors,
            "is_favorited": True,
            "is_saved": p.is_saved,
            "github_url": p.github_url,
            "project_page": p.project_page,
            "thumbnail": p.thumbnail,
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": []
            },
            "ingestion_status": p.ingestion_status
        })
    return result

def _calculate_progress(status: str) -> tuple[int, str, str]:
    """Helper to map ingestion status to progress details."""
    progress = 0
    step = "queued"
    display_status = status
    
    if status == "downloading":
         progress = 10
         step = "downloading"
         display_status = "processing"
    elif status == "parsing":
         progress = 40
         step = "parsing"
         display_status = "processing"
    elif status == "indexing":
         progress = 70
         step = "indexing"
         display_status = "processing"
    elif status == "pending":
         display_status = "queued"
    
    return progress, step, display_status

@router.get("/ingestion-status/{paper_id}")
def get_ingestion_status(paper_id: str, db: Session = Depends(get_db)):
    """Get the ingestion status for a paper."""
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    progress, step, _ = _calculate_progress(paper.ingestion_status)
    
    # Override for completed/failed
    if paper.ingestion_status == "completed":
        progress = 100
        step = "completed"
    elif paper.ingestion_status == "failed":
        progress = 100
        step = "failed"

    return {
        "paper_id": paper_id,
        "ingestion_status": paper.ingestion_status,
        "chunk_count": paper.chunk_count,
        "pdf_path": paper.pdf_path,
        "ingested_at": paper.ingested_at.isoformat() if paper.ingested_at else None,
        "error_message": paper.error_message,
        "progress": progress,
        "step": step
    }

@router.get("/ingestion/jobs")
def get_active_jobs(db: Session = Depends(get_db)):
    """
    Get all active ingestion jobs from the DB.
    Replaces old IngestionJobManager.
    """
    active_statuses = ["pending", "queued", "processing", "downloading", "parsing", "indexing"]
    papers = db.query(UserPaper).filter(UserPaper.ingestion_status.in_(active_statuses)).all()
    
    jobs = []
    for p in papers:
        progress, step, status = _calculate_progress(p.ingestion_status)
             
        jobs.append({
            "paper_id": p.paper_id,
            "title": p.title,
            "status": status,
            "progress": progress,
            "step": step,
            "start_time": p.updated_at.isoformat() if p.updated_at else datetime.utcnow().isoformat(),
            "error": p.error_message
        })
        
    return jobs


@router.get("/ingestion/rq-status")
def get_rq_status():
    """
    Get RQ job queue status.
    Returns info about Redis availability and queue stats.
    """
    from src.jobs.queue import is_redis_available, get_queue
    
    if not is_redis_available():
        return {
            "redis_available": False,
            "fallback_mode": "background_tasks",
            "message": "Redis unavailable, using FastAPI BackgroundTasks"
        }
    
    queue = get_queue()
    return {
        "redis_available": True,
        "queue_name": queue.name,
        "job_count": len(queue),
        "failed_count": len(queue.failed_job_registry),
    }


from src.api.schemas import InsightRequest

@router.post("/insights")
async def get_paper_insights(request: InsightRequest, db: Session = Depends(get_db)):
    """
    Generate quick insights from the paper's abstract (summary).
    This provides instant value without waiting for PDF ingestion.
    """
    paper_id = request.paper_id
    
    # 1. Check if paper exists in DB
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    
    # 3. Determine summary to use
    summary = request.summary
    
    if not summary:
        if paper and paper.summary:
            summary = paper.summary
        else:
            # Not in DB and no summary provided -> fetch from ArXiv
            from src.services.arxiv_service import ArxivService
            logger.info(f"Fetching metadata for {paper_id} from ArXiv for insights generation...")
            metadata = ArxivService.fetch_paper(paper_id)
            if metadata:
                summary = metadata.summary
                # Note: We do NOT save to DB here as per requirement
    
    # Generate insights using LLM from abstract
    if not summary or summary == "No summary available.":
        raise HTTPException(status_code=400, detail="Abstract not available for this paper.")

    try:
        from src.core.llm_factory import LLMFactory
        llm = LLMFactory.get_llama_index_llm()
        
        prompt = f"""
        Paper Title: {paper.title if paper else paper_id}
        Abstract: {summary}
        
        You are a research assistant for an AI scientist. Provide a comprehensive, high-level structured overview of this paper based on its abstract.
        
        Follow this strict Markdown format:

        ### 📋 Summary
        (A 2-3 sentence high-level summary of the paper's core contribution)

        ### 💡 Key Insights
        - (Insight 1)
        - (Insight 2)
        - (Insight 3)

        ### 🔬 Results & Methodology
        (Describe the main approach and performance gains mentioned)

        ### 📊 Figures & Architecture (Potential)
        (Infer what key figures or architectural components would be present based on the abstract)

        ### ⚠️ Limitations
        (Mention any constraints or future work noted)

        ### 🔗 Related Work
        (Briefly mention which sub-fields or prior methods this relates to)

        Focus on methodology, novel architecture, or performance gains. Keep it professional and technical.
        """
        
        response = await llm.acomplete(prompt)
        insights = str(response)
        
        # 4. Save to DB ONLY if paper already exists
        if paper:
            paper.notes = insights
            # Update summary if it was missing
            if (not paper.summary or paper.summary == "No summary available.") and summary:
                 paper.summary = summary
            db.commit()
        
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

async def get_or_fetch_paper_metadata(paper_id: str, db: Session) -> UserPaper:
    """Helper to get paper from DB or fetch metadata from ArXiv."""
    from src.services.arxiv_service import ArxivService
    
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    
    if not paper:
        # If not in DB, try to fetch from ArXiv
        logger.info(f"Paper {paper_id} not found in DB. Fetching from ArXiv...")
        
        metadata = ArxivService.fetch_paper(paper_id)
        if metadata is None:
            raise HTTPException(status_code=404, detail="Paper not found on ArXiv.")
        
        # Save to DB (no ingestion_status - set only after successful enqueue)
        paper = UserPaper(
            paper_id=paper_id,
            title=metadata.title,
            authors=metadata.authors,
            summary=metadata.summary,
            url=metadata.url,
            published_date=metadata.published_date
        )
        db.add(paper)
        db.commit()
        db.refresh(paper)
            
    return paper

@router.get("/paper/{paper_id}/metadata")
async def get_paper_metadata(paper_id: str, db: Session = Depends(get_db)):
    """
    Get full paper metadata. 
    Fetches from ArXiv if not in DB.
    """
    try:
        paper = await get_or_fetch_paper_metadata(paper_id, db)
        return {
            "id": paper.paper_id,
            "title": paper.title,
            "abstract": paper.summary,
            "authors": paper.authors,
            "published_date": paper.published_date,
            "url": paper.url,
            "ingestion_status": paper.ingestion_status,
            "user_notes": paper.user_notes,
            "notes": paper.notes
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting metadata for {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paper/{paper_id}/pdf")
def get_paper_pdf(paper_id: str):
    """
    Proxy endpoint to serve PDF.
    1. Tries to serve from local 'data/pdfs/{paper_id}.pdf' if successfully ingested/saved.
    2. If not found, streams directly from ArXiv 'https://arxiv.org/pdf/{paper_id}.pdf'.
    This solves CORS issues when using react-pdf.
    """
    # Check if we have a local copy from ingestion
    pdf_path = f"data/pdfs/{paper_id}.pdf"
    
    if os.path.exists(pdf_path):
        logger.info(f"Serving local PDF for {paper_id}")
        def iterfile():
            with open(pdf_path, mode="rb") as file_like:
                yield from file_like
        return StreamingResponse(iterfile(), media_type="application/pdf")
    
    # Fallback to ArXiv Proxy
    logger.info(f"Proxying PDF for {paper_id} from ArXiv")
    arxiv_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
    try:
        # Stream the request
        external_req = requests.get(arxiv_url, stream=True, timeout=10)
        external_req.raise_for_status()
        
        return StreamingResponse(
            external_req.iter_content(chunk_size=8192), 
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"Failed to fetch PDF for {paper_id} from ArXiv: {e}")
        raise HTTPException(status_code=404, detail=f"PDF not found on ArXiv: {str(e)}")
