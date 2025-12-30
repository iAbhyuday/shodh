from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from src.db.sql_db import get_db, UserPaper, Project
from src.api.schemas import ProjectCreate, ProjectResponse, ProjectAddPaperRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/projects", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all research projects."""
    projects = db.query(Project).all()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            research_dimensions=p.research_dimensions,
            created_at=p.created_at.isoformat(),
            paper_count=len(p.papers)
        ) for p in projects
    ]

@router.post("/projects", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new research project."""
    existing = db.query(Project).filter(Project.name == project.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name already exists.")
    
    new_project = Project(
        name=project.name,
        description=project.description,
        research_dimensions=project.research_dimensions
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return ProjectResponse(
        id=new_project.id,
        name=new_project.name,
        description=new_project.description,
        research_dimensions=new_project.research_dimensions,
        created_at=new_project.created_at.isoformat(),
        paper_count=0
    )

@router.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project details and paper list."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "research_dimensions": project.research_dimensions,
        "created_at": project.created_at.isoformat(),
        "papers": [{
            "id": p.paper_id,
            "title": p.title,
            "abstract": p.summary,
            "source": "ArXiv",
            "url": p.url,
            "published_date": p.published_date,
            "authors": p.authors,
            "is_favorited": p.is_favorited,
            "is_saved": p.is_saved,
            "github_url": p.github_url,
            "project_page": p.project_page,
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": []
            },
            "ingestion_status": p.ingestion_status
        } for p in project.papers]
    }

@router.post("/projects/{project_id}/add-paper")
def add_paper_to_project(
    project_id: int, 
    request: ProjectAddPaperRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Link a paper to a project using its paper_id (arxiv id)."""
    from src.api.routes.papers import background_ingest_paper
    
    paper_id = request.paper_id
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    if not paper:
        # Create paper record with provided details or fetch from ArXiv
        if request.title:
            logger.info(f"Creating new paper record for {paper_id} with provided title.")
            paper = UserPaper(
                paper_id=paper_id,
                title=request.title,
                authors=request.authors or "Unknown",
                summary=request.summary or "",
                url=request.url or f"https://arxiv.org/abs/{paper_id}",
                published_date=request.published_date or "",
                ingestion_status="pending"
            )
            db.add(paper)
            db.commit()
            db.refresh(paper)
        else:
            # Fallback to ArXiv fetch
            logger.info(f"Paper {paper_id} not found in DB and no title provided. Fetching from ArXiv...")

        try:
            import requests
            import xml.etree.ElementTree as ET
            arxiv_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
            response = requests.get(arxiv_url)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', namespace)
            
            if entry:
                title = entry.find('atom:title', namespace).text.strip()
                summary = entry.find('atom:summary', namespace).text.strip()
                authors = ", ".join([a.find('atom:name', namespace).text for a in entry.findall('atom:author', namespace)])
                published = entry.find('atom:published', namespace).text
                
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
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id} from ArXiv: {e}")
            raise HTTPException(status_code=404, detail=f"Paper not found and ArXiv fetch failed: {str(e)}")
    
    if paper not in project.papers:
        project.papers.append(paper)
        db.commit()
        
    # Trigger ingestion automatically if not completed
    if paper.ingestion_status != "completed":
        paper.ingestion_status = "pending"
        db.commit()
        background_tasks.add_task(background_ingest_paper, paper_id)
        logger.info(f"Triggered background ingestion for {paper_id} via project {project_id}")
    
    return {"message": f"Added paper '{paper.title}' to project '{project.name}' and triggered ingestion."}

@router.delete("/projects/{project_id}/remove-paper/{paper_db_id}")
def remove_paper_from_project(project_id: int, paper_db_id: int, db: Session = Depends(get_db)):
    """Unlink a paper from a project using its DB primary key."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    paper = db.query(UserPaper).filter(UserPaper.id == paper_db_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    
    if paper in project.papers:
        project.papers.remove(paper)
        db.commit()
        return {"message": "Paper removed from project."}
    
    return {"message": "Paper was not in project."}

@router.delete("/projects/{project_id}/paper/{paper_id}")
def remove_paper_by_id(project_id: int, paper_id: str, db: Session = Depends(get_db)):
    """Unlink a paper from a project using its ArXiv ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")
    
    if paper in project.papers:
        project.papers.remove(paper)
        db.commit()
        return {"message": "Paper removed from project."}
    
    return {"message": "Paper was not in project."}

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project entirely."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    # Clear paper associations (papers are NOT deleted, just unlinked)
    project.papers.clear()
    db.delete(project)
    db.commit()
    
    return {"message": f"Project '{project.name}' deleted successfully."}

