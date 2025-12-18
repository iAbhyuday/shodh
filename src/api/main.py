from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import datetime
import requests

from src.db.sql_db import init_db, get_db, UserPaper
from src.db.vector_store import vector_store
from src.core.rag import rag_pipeline
from src.agents.metrics_agent import MetricsAgent
from src.agents.idea_generation_agent import IdeaGenerationAgent
from src.agents.visualization_agent import VisualizationAgent
from src.agents.ingestion_agent import IngestionAgent

# Initialize DB
init_db()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agents
ingestion_agent = IngestionAgent()
metrics_agent = MetricsAgent()
idea_agent = IdeaGenerationAgent()
vis_agent = VisualizationAgent()

# Models
class IdeaRequest(BaseModel):
    paper_id: str

class PaperActionRequest(BaseModel):
    paper_id: str
    title: str = ""
    summary: str = ""
    notes: str = ""  # Formatted summary (bullet points)
    authors: str = ""
    url: str = ""
    published_date: str = ""
    github_url: Optional[str] = None  # Fixed: Use Optional
    project_page: Optional[str] = None  # Fixed: Use Optional
    mindmap_json: Optional[str] = None  # Fixed: Use Optional

# --- Helper Functions ---


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

def background_ingest_paper(arxiv_id: str):
    print(f"Background ingesting paper: {arxiv_id}")
    # reusing ingestion agent logic but for single ID
    try:
        # 1. Fetch from Arxiv
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(client.results(search))
        
        # 2. Process
        paper_data = {
            "id": paper.get_short_id(),
            "title": paper.title,
            "abstract": paper.summary,
            "source": "arxiv",
            "url": paper.entry_id,
            "published_date": paper.published.isoformat(),
            "authors": ", ".join([a.name for a in paper.authors])
        }
        
        # 3. Embedding & Ingest
        # (This remains as is)
        from src.db.vector_store import store_paper_embedding
        store_paper_embedding(paper_data)
        
    except Exception as e:
        print(f"Failed background ingest: {e}")

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Shodh"}

@app.get("/api/feed")
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
    papers = []
    query = None
    if q:
        query = q.lower()
    papers = fetch_daily_papers(date=date, limit=200)
        # for p in papers:
        #     # Search title, abstract, authors, and tags
        #     text = (p['title'] + " " + p['abstract'] + " " + p['authors']).lower()
        #     tags = [t.lower() for t in p['metrics']['tags']]
        #     if query in text or any(query in t for t in tags):
        #         filtered.append(p)
        # papers = filtered

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
        
    return {
        "papers": paginated_papers,
        "total": total_papers,
        "page": page,
        "limit": limit,
        "total_pages": (total_papers + limit - 1) // limit  # Ceiling division
    }

@app.post("/api/favorite")
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

@app.post("/api/save")
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
        background_tasks.add_task(background_ingest_paper, action.paper_id)
        
    return {"status": "success", "is_saved": paper.is_saved}

@app.post("/api/generate_ideas")
def generate_ideas(request: IdeaRequest, db: Session = Depends(get_db)):
    # Check if we have it in Chroma first (must be saved/ingested)
    # If not, we can try to fetch on-the-fly or demand save first.
    # For UX, let's fetch on the fly if not in DB, but better to check Chroma.
    
    try:
        data = rag_pipeline.vector_store.collection.get(ids=[request.paper_id])
        if data['ids']:
             paper_content = {
                "title": data['metadatas'][0].get('title'),
                "abstract": data['documents'][0],
                "metrics": {}
            }
             return {"paper_id": request.paper_id, "ideas": idea_agent.generate_ideas(paper_content)}
    except:
        pass
        
    # Fallback: Fetch directly from Arxiv for generation (if not saved/ingested yet)
    # This allows generating ideas on non-saved papers too!
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(id_list=[request.paper_id])
        res = next(client.results(search))
        paper_content = {
            "title": res.title,
            "abstract": res.summary,
            "metrics": {}
        }
        return {"paper_id": request.paper_id, "ideas": idea_agent.generate_ideas(paper_content)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Paper not found or error generating: {e}")

@app.post("/api/visualize")
def visualize_paper(request: IdeaRequest):
    # Same logic as ideas: check Chroma, if not, fetch live.
    # Note: Visualization expects JSON structure.
    
    # 1. Try Cache/Chroma
    try:
        data = rag_pipeline.vector_store.collection.get(ids=[request.paper_id])
        if data['ids']:
            metadata = data['metadatas'][0]
            if metadata.get("mindmap_json"):
                import json
                return {"paper_id": request.paper_id, "mindmap": json.loads(metadata.get("mindmap_json"))}
            
            # Generate from content
            paper = {"title": metadata.get('title'), "abstract": data['documents'][0]}
            mindmap_data = vis_agent.generate_mindmap(paper)
            
            # Cache it
            import json
            metadata["mindmap_json"] = json.dumps(mindmap_data)
            rag_pipeline.vector_store.collection.update(ids=[request.paper_id], metadatas=[metadata])
            return {"paper_id": request.paper_id, "mindmap": mindmap_data}
    except:
        pass

    # 2. Live Generation (if not in DB or error)
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(id_list=[request.paper_id])
        res = next(client.results(search))
        paper = {"title": res.title, "abstract": res.summary}
        mindmap_data = vis_agent.generate_mindmap(paper)
        return {"paper_id": request.paper_id, "mindmap": mindmap_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))