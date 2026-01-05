from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json

from src.db.sql_db import get_db
from src.api.schemas import IdeaRequest

from src.agents.idea_generation_agent import IdeaGenerationAgent
from src.agents.visualization_agent import VisualizationAgent

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Agents
idea_agent = IdeaGenerationAgent()
vis_agent = VisualizationAgent()

@router.post("/generate_ideas")
def generate_ideas(request: IdeaRequest, db: Session = Depends(get_db)):
    # Check if we have it in Chroma first (must be saved/ingested)
    # If not, we can try to fetch on-the-fly or demand save first.
    # For UX, let's fetch on the fly if not in DB, but better to check Chroma.
    
    try:
        from src.core.retriever import PaperRetriever
        retriever = PaperRetriever()
        data = retriever._get_vector_store().collection.get(ids=[request.paper_id])
        if data['ids']:
             paper_content = {
                "title": data['metadatas'][0].get('title'),
                "abstract": data['documents'][0],
                "metrics": {}
            }
             return {"paper_id": request.paper_id, "ideas": idea_agent.generate_ideas(paper_content)}
    except Exception as e:
        logger.debug(f"Paper {request.paper_id} not in vector store, falling back to ArXiv: {e}")
        
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

@router.post("/visualize")
def visualize_paper(request: IdeaRequest):
    # Same logic as ideas: check Chroma, if not, fetch live.
    # Note: Visualization expects JSON structure.
    
    # 1. Try Cache/Chroma
    try:
        from src.core.retriever import PaperRetriever
        retriever = PaperRetriever()
        store = retriever._get_vector_store()
        
        data = store.collection.get(ids=[request.paper_id])
        if data['ids']:
            metadata = data['metadatas'][0]
            if metadata.get("mindmap_json"):
                return {"paper_id": request.paper_id, "mindmap": json.loads(metadata.get("mindmap_json"))}
            
            # Generate from content
            paper = {"title": metadata.get('title'), "abstract": data['documents'][0]}
            mindmap_data = vis_agent.generate_mindmap(paper)
            
            # Cache it
            metadata["mindmap_json"] = json.dumps(mindmap_data)
            store.collection.update(ids=[request.paper_id], metadatas=[metadata])
            return {"paper_id": request.paper_id, "mindmap": mindmap_data}
    except Exception as e:
        logger.debug(f"Paper {request.paper_id} not in vector store for visualization, falling back to ArXiv: {e}")

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
