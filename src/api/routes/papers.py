from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import datetime
import requests
import logging

from src.db.sql_db import get_db, UserPaper, SessionLocal
from src.api.schemas import PaperActionRequest

router = APIRouter()
logger = logging.getLogger(__name__)

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

def fetch_daily_papers(date: str = None, limit: int = 100):
    # Fetch from huggingface daily papers or arxiv directly if needed
    # For now, using huggingface daily papers API via requests
    today = datetime.date.today()
    url = "https://huggingface.co/api/daily_papers"
    if date:
        url = f"{url}?date={date}"
    try:
        resp = requests.get(url)
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
                "abstract": paper_info.get('ai_summary', 'No summary available.'),
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
    today = datetime.date.today()
    url = f"https://huggingface.co/api/papers/search?q={query}&limit={limit}"
    try:
        resp = requests.get(url)
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



def _update_status(paper_id: str, status: str, chunk_count: int = None, pdf_path: str = None):
    """Helper to safely update paper status in new transaction"""
    db = SessionLocal()
    try:
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper:
            paper.ingestion_status = status
            if chunk_count is not None:
                paper.chunk_count = chunk_count
            if pdf_path:
                paper.pdf_path = pdf_path
            
            if status == "completed":
                paper.ingested_at = datetime.datetime.utcnow()
                
            db.commit()
            logger.info(f"Updated status for {paper_id} to {status}")
        else:
            logger.warning(f"Could not find paper {paper_id} to update status to {status}")
    except Exception as e:
        logger.error(f"Failed to update status for {paper_id}: {e}")
    finally:
        db.close()

def background_ingest_paper(paper_id: str):
    """
    Background task for PDF ingestion pipeline:
    1. Download PDF from arXiv
    2. Parse with Docling
    3. Index with LlamaIndex into ChromaDB
    """
    logger.info(f"Starting PDF ingestion for: {paper_id}")
    
    # Check if already done
    db = SessionLocal()
    try:
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper and paper.ingestion_status == "completed":
            logger.info(f"Paper {paper_id} already ingested. Skipping.")
            return
    finally:
        db.close()

    try:
        # Update status to processing
        _update_status(paper_id, "downloading")
        
        # Step 1: Download PDF
        downloader = get_pdf_downloader()
        pdf_path = downloader.download(paper_id)
        logger.info(f"Downloaded PDF: {pdf_path}")
        
        # Update status
        _update_status(paper_id, "parsing", pdf_path=str(pdf_path))
        
        # Step 2: Parse with Docling
        parser = get_docling_parser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        logger.info(f"Parsed: {len(parsed_doc.sections)} sections.")
        
        # Update status
        _update_status(paper_id, "indexing")
        
        # Step 3: Index with LlamaIndex
        pipeline = get_ingestion_pipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        logger.info(f"Indexed {chunk_count} chunks for {paper_id}")
        
        # Update final status
        _update_status(paper_id, "completed", chunk_count=chunk_count)
        
        logger.info(f"Ingestion completed for {paper_id}")
        
    except Exception as e:
        logger.error(f"Ingestion failed for {paper_id}: {e}")
        _update_status(paper_id, "failed")

# --- Endpoints ---

@router.get("/feed")
def get_feed(
    date: str = None,
    q: str = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get daily papers feed. 
    Enriches with user state (is_saved, is_favorited) from SQL.
    Supports filtering by date (YYYY-MM-DD) and keyword (q).
    Supports pagination via page parameter (1-indexed).
    """
    # Filter by keyword if provided
    if q:
        query = q.lower()
        # Use the search API for better results if keyword search is requested
        papers = search_papers(q, limit=limit * 5)
        
        # Optionally perform extra local filtering if needed, 
        # though search_papers should already handle it.
        filtered = []
        for p in papers:
            # Search title, abstract, authors, and tags
            text = (p['title'] + " " + p['abstract'] + " " + p['authors']).lower()
            tags = [t.lower() for t in p['metrics'].get('tags', [])]
            if query in text or any(query in t for t in tags):
                filtered.append(p)
        papers = filtered
    else:
        papers = fetch_daily_papers(date=date, limit=200)


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
            authors=action.authors,
            url=action.url,
            published_date=action.published_date,
            github_url=action.github_url,
            project_page=action.project_page,
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
            paper.authors = action.authors or paper.authors
            paper.url = action.url or paper.url
            paper.published_date = action.published_date or paper.published_date
            paper.github_url = action.github_url or paper.github_url
            paper.project_page = action.project_page or paper.project_page
            if action.mindmap_json:
                paper.mindmap_json = action.mindmap_json
        
    db.commit()
    
    # Trigger ingestion if saving (and strictly if newly saved or re-saved)
    if paper.is_saved:
        # Check if already ingested to avoid re-running
        if paper.ingestion_status != "completed":
            # Set initial ingestion status
            paper.ingestion_status = "pending"
            db.commit()
            background_tasks.add_task(background_ingest_paper, action.paper_id)
        else:
            print(f"Paper {action.paper_id} already ingested. Skipping background task.")
        
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
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": [] # We don't store tags in SQL currently
            }
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
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": []
            },
            "ingestion_status": p.ingestion_status
        })
    return result

@router.get("/ingestion-status/{paper_id}")
def get_ingestion_status(paper_id: str, db: Session = Depends(get_db)):
    """Get the ingestion status for a paper."""
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {
        "paper_id": paper_id,
        "ingestion_status": paper.ingestion_status,
        "chunk_count": paper.chunk_count,
        "pdf_path": paper.pdf_path,
        "ingested_at": paper.ingested_at.isoformat() if paper.ingested_at else None
    }
@router.get("/insights/{paper_id}")
async def get_paper_insights(paper_id: str, db: Session = Depends(get_db)):
    """
    Generate quick insights from the paper's abstract (summary).
    This provides instant value without waiting for PDF ingestion.
    """
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    
    if not paper:
        # If not in DB, try to fetch from ArXiv
        logger.info(f"Paper {paper_id} not found in DB. Fetching from ArXiv...")
        try:
            import xml.etree.ElementTree as ET
            arxiv_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
            response = requests.get(arxiv_url)
            response.raise_for_status()
            
            # Parse ArXiv XML
            root = ET.fromstring(response.text)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', namespace)
            
            if entry:
                title = entry.find('atom:title', namespace).text.strip()
                summary = entry.find('atom:summary', namespace).text.strip()
                authors = ", ".join([a.find('atom:name', namespace).text for a in entry.findall('atom:author', namespace)])
                published = entry.find('atom:published', namespace).text
                
                # Save to DB
                paper = UserPaper(
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    summary=summary,
                    url=f"https://arxiv.org/abs/{paper_id}",
                    published_date=published[:10],
                    ingestion_status="pending"
                )
                db.add(paper)
                db.commit()
                db.refresh(paper)
            else:
                raise HTTPException(status_code=404, detail="Paper not found on ArXiv.")
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id} from ArXiv: {e}")
            raise HTTPException(status_code=404, detail=f"Paper not found and ArXiv fetch failed: {str(e)}")

    # Return cached insights if available
    if paper.notes:
        return {"insights": paper.notes}

    # Generate insights using LLM from abstract
    if not paper.summary or paper.summary == "No summary available.":
        raise HTTPException(status_code=400, detail="Abstract not available for this paper.")

    try:
        from src.core.llm_factory import LLMFactory
        llm = LLMFactory.get_llama_index_llm()
        
        prompt = f"""
        Paper Title: {paper.title}
        Abstract: {paper.summary}
        
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
        
        # Save to DB
        paper.notes = insights
        db.commit()
        
        return {"insights": insights}
    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")
