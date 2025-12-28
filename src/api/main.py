from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import datetime
import requests
import logging

from src.db.sql_db import init_db, get_db, UserPaper, Conversation, Message, SessionLocal
from src.db.vector_store import vector_store
from src.core.rag import rag_pipeline
from src.agents.metrics_agent import MetricsAgent
from src.agents.idea_generation_agent import IdeaGenerationAgent
from src.agents.visualization_agent import VisualizationAgent
from src.agents.ingestion_agent import IngestionAgent

# Lazy import for ingestion pipeline (heavy dependencies)
def get_pdf_downloader():
    from src.ingestion.pdf_downloader import PDFDownloader
    return PDFDownloader()

def get_docling_parser():
    from src.ingestion.docling_parser import DoclingParser
    return DoclingParser()

def get_ingestion_pipeline():
    from src.ingestion.pipeline import IngestionPipeline
    return IngestionPipeline()

logger = logging.getLogger(__name__)

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

class ChatRequest(BaseModel):
    paper_id: str
    message: str
    conversation_id: Optional[int] = None  # If None, creates new conversation
    history: List[Dict[str, str]] = []  # Optional chat history (for backward compat)
    use_agent: bool = False  # If True, use Agentic RAG; else use fast Contextual RAG


class ConversationCreate(BaseModel):
    paper_id: str
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    paper_id: str
    title: Optional[str]
    created_at: str
    message_count: int = 0

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

def background_ingest_paper(paper_id: str):
    """
    Background task for PDF ingestion pipeline:
    1. Download PDF from arXiv
    2. Parse with Docling
    3. Index with LlamaIndex into ChromaDB
    """
    logger.info(f"Starting PDF ingestion for: {paper_id}")
    
    # Get a new DB session for background task
    db = SessionLocal()
    
    try:
        # Update status to processing
        paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
        if paper:
            paper.ingestion_status = "downloading"
            db.commit()
        
        # Step 1: Download PDF
        downloader = get_pdf_downloader()
        pdf_path = downloader.download(paper_id)
        logger.info(f"Downloaded PDF: {pdf_path}")
        
        if paper:
            paper.pdf_path = str(pdf_path)
            paper.ingestion_status = "parsing"
            db.commit()
        
        # Step 2: Parse with Docling
        parser = get_docling_parser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        logger.info(f"Parsed: {len(parsed_doc.sections)} sections.")
        
        if paper:
            paper.ingestion_status = "indexing"
            db.commit()
        
        # Step 3: Index with LlamaIndex
        pipeline = get_ingestion_pipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        logger.info(f"Indexed {chunk_count} chunks for {paper_id}")
        
        # Update final status
        if paper:
            paper.ingestion_status = "completed"
            paper.chunk_count = chunk_count
            paper.ingested_at = datetime.datetime.utcnow()
            db.commit()
        
        logger.info(f"Ingestion completed for {paper_id}")
        
    except Exception as e:
        logger.error(f"Ingestion failed for {paper_id}: {e}")
        if paper:
            paper.ingestion_status = "failed"
            db.commit()
    finally:
        db.close()

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
        # Set initial ingestion status
        paper.ingestion_status = "pending"
        db.commit()
        background_tasks.add_task(background_ingest_paper, action.paper_id)
        
    return {
        "status": "success", 
        "is_saved": paper.is_saved,
        "ingestion_status": paper.ingestion_status
    }

@app.get("/api/ingestion-status/{paper_id}")
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


# === Conversation Endpoints ===

@app.get("/api/conversations/{paper_id}")
def list_conversations(paper_id: str, db: Session = Depends(get_db)):
    """List all conversations for a paper."""
    conversations = db.query(Conversation).filter(
        Conversation.paper_id == paper_id
    ).order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append({
            "id": conv.id,
            "paper_id": conv.paper_id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "message_count": msg_count
        })
    return result


@app.post("/api/conversations")
def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation for a paper."""
    conv = Conversation(
        paper_id=request.paper_id,
        title=request.title or "New Chat"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "paper_id": conv.paper_id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None
    }


@app.get("/api/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: int, db: Session = Depends(get_db)):
    """Get all messages in a conversation."""
    import json
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "citations": json.loads(msg.citations_json) if msg.citations_json else [],
            "mode": msg.mode,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }
        for msg in messages
    ]

@app.post("/api/chat")
def chat_with_paper(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with a paper using RAG retrieval.
    Retrieves relevant chunks from the indexed paper and generates a response.
    """
    # Check paper exists and is ingested
    paper = db.query(UserPaper).filter(UserPaper.paper_id == request.paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.ingestion_status != "completed":
        raise HTTPException(status_code=400, detail="Paper is not fully ingested yet")
    
    try:
        from src.core.config import get_settings
        settings = get_settings()
        pipeline = get_ingestion_pipeline()
        
        # Build chat history text
        history_text = ""
        if request.history:
            for msg in request.history[-5:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_text += f"{role.upper()}: {content}\n"
        
        if request.use_agent:
            # === AGENTIC RAG (CrewAI) ===
            from src.agents.paper_crew import run_paper_crew
            
            response_text = run_paper_crew(
                paper_id=request.paper_id,
                paper_title=paper.title,
                user_query=request.message,
                # ollama_model=settings.OLLAMA_MODEL,
                # ollama_base_url=settings.OLLAMA_BASE_URL,
                chat_history=history_text if history_text else None
            )
            
            # Get citations from a separate retrieval (for display)
            retrieved = pipeline.query(
                query_text=request.message,
                paper_id=request.paper_id,
                top_k=5
            )
            
            citations = []
            for chunk in retrieved:
                citations.append({
                    "content": chunk['content'],
                    "section": chunk['metadata'].get('section_type', 'unknown'),
                    "section_title": chunk['metadata'].get('section_title', ''),
                    "page_number": chunk['metadata'].get('page_number', None),
                    "score": chunk.get('score', 0)
                })
        else:
            # === CONTEXTUAL RAG (Fast) ===
            from langchain_ollama import ChatOllama
            
            retrieved = pipeline.query(
                query_text=request.message,
                paper_id=request.paper_id,
                top_k=5
            )
            
            context_parts = []
            for chunk in retrieved:
                section = chunk['metadata'].get('section_type', 'unknown')
                context_parts.append(f"[{section.upper()}]: {chunk['content']}")
            
            context = "\n\n".join(context_parts)
            
            llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.7
            )
            
            prompt = f"""You are a precise research assistant labeled 'Shodh AI'.
You are analyzing the paper "{paper.title}".

GOAL: Answer the user's question using the provided context.
FORMAT: Use clear, structured Markdown.
- Use **bold** for key concepts.
- Use bullet points for lists.
- Keep responses concise and note-like.

CONTEXT FROM PAPER:
{context}

{history_text}
USER: {request.message}

A:"""
            
            response = llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            citations = []
            for chunk in retrieved:
                citations.append({
                    "content": chunk['content'],
                    "section": chunk['metadata'].get('section_type', 'unknown'),
                    "section_title": chunk['metadata'].get('section_title', ''),
                    "page_number": chunk['metadata'].get('page_number', None),
                    "score": chunk.get('score', 0)
                })
        
        # === SAVE TO DATABASE ===
        import json
        
        # Get or create conversation
        conversation_id = request.conversation_id
        if not conversation_id:
            # Create new conversation
            conv = Conversation(
                paper_id=request.paper_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            db.add(conv)
            db.commit()
            db.refresh(conv)
            conversation_id = conv.id
        else:
            # Update existing conversation's updated_at
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                conv.updated_at = datetime.datetime.utcnow()
                db.commit()
        
        # Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        db.add(user_msg)
        
        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            citations_json=json.dumps(citations) if citations else None,
            mode="agent" if request.use_agent else "contextual"
        )
        db.add(assistant_msg)
        db.commit()
        
        return {
            "paper_id": request.paper_id,
            "conversation_id": conversation_id,
            "response": response_text,
            "citations": citations,
            "context_chunks": len(citations),
            "mode": "agent" if request.use_agent else "contextual"
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))