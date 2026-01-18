from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json

from src.db.sql_db import get_db, UserPaper
from src.api.schemas import IdeaRequest

from src.agents.idea_generation_agent import IdeaGenerationAgent
from src.agents.visualization_agent import VisualizationAgent

import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Agents
idea_agent = IdeaGenerationAgent()
vis_agent = VisualizationAgent()


def _get_paper_content(paper_id: str, db: Session) -> Tuple[Dict[str, Any], Optional[UserPaper]]:
    """
    Get paper content from DB or ArXiv.
    
    Returns:
        Tuple of (paper_content_dict, db_paper_object_or_None)
    """
    # Try Database first
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    if paper:
        return {
            "title": paper.title,
            "abstract": paper.summary or "",
        }, paper
    
    # Fallback to ArXiv
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(id_list=[paper_id])
        res = next(client.results(search))
        return {
            "title": res.title,
            "abstract": res.summary,
        }, None
    except Exception as e:
        logger.warning(f"Failed to fetch paper {paper_id} from ArXiv: {e}")
        raise HTTPException(status_code=404, detail=f"Paper not found: {paper_id}")


@router.post("/generate_ideas")
def generate_ideas(request: IdeaRequest, db: Session = Depends(get_db)):
    """Generate research ideas from paper content."""
    try:
        paper_content, _ = _get_paper_content(request.paper_id, db)
        paper_content["metrics"] = {}  # Add empty metrics for agent compatibility
        ideas = idea_agent.generate_ideas(paper_content)
        return {"paper_id": request.paper_id, "ideas": ideas}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating ideas for {request.paper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating ideas: {e}")


@router.post("/visualize")
def visualize_paper(request: IdeaRequest, db: Session = Depends(get_db)):
    """Generate mindmap visualization from paper content."""
    try:
        paper_content, db_paper = _get_paper_content(request.paper_id, db)
        
        # Check for cached mindmap (only if from DB)
        if db_paper and db_paper.mindmap_json:
            return {"paper_id": request.paper_id, "mindmap": json.loads(db_paper.mindmap_json)}
        
        # Generate mindmap
        mindmap_data = vis_agent.generate_mindmap(paper_content)
        
        # Cache if we have a DB record
        if db_paper:
            db_paper.mindmap_json = json.dumps(mindmap_data)
            db.commit()
        
        return {"paper_id": request.paper_id, "mindmap": mindmap_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error visualizing paper {request.paper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating visualization: {e}")

