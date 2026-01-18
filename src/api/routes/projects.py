from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from src.db.sql_db import get_db, UserPaper, Project
from src.api.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectAddPaperRequest

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

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """Update an existing research project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    # Check name uniqueness if name is being updated
    if project_update.name is not None and project_update.name != project.name:
        existing = db.query(Project).filter(Project.name == project_update.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Project with this name already exists.")
        project.name = project_update.name
        
    if project_update.description is not None:
        project.description = project_update.description
        
    if project_update.research_dimensions is not None:
        project.research_dimensions = project_update.research_dimensions
        
    db.commit()
    db.refresh(project)
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        research_dimensions=project.research_dimensions,
        created_at=project.created_at.isoformat(),
        paper_count=len(project.papers)
    )

@router.get("/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
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
            "thumbnail": p.thumbnail,
            "project_ids": [proj.id for proj in p.projects],
            "metrics": {
                 "tags": []
            },
            "ingestion_status": p.ingestion_status
        } for p in project.papers]
    }

@router.post("/projects/{project_id}/add-paper")
def add_paper_to_project(
    project_id: str, 
    request: ProjectAddPaperRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Link a paper to a project using its paper_id (arxiv id)."""
    from src.api.routes.papers import enqueue_ingestion
    logger.info(f"Paper details: {request}")
    
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
                thumbnail=request.thumbnail,
                github_url=request.github_url,
                project_page=request.project_page,
                # ingestion_status set after successful enqueue
            )
            db.add(paper)
            db.commit()
            db.refresh(paper)
        else:
            # Fallback to ArXiv fetch using ArxivService
            logger.info(f"Paper {paper_id} not found in DB. Fetching from ArXiv...")
            from src.services.arxiv_service import ArxivService
            
            metadata = ArxivService.fetch_paper(paper_id)
            if metadata is None:
                raise HTTPException(status_code=404, detail="Paper not found on ArXiv.")
            
            try:
                paper = UserPaper(
                    paper_id=paper_id,
                    title=metadata.title,
                    authors=metadata.authors,
                    summary=metadata.summary,
                    url=metadata.url,
                    published_date=metadata.published_date,
                    # We can still try to use request data if available for these extra fields
                    thumbnail=request.thumbnail,
                    github_url=request.github_url,
                    project_page=request.project_page,
                    # ingestion_status set after successful enqueue
                )
                db.add(paper)
                db.commit()
                db.refresh(paper)
            except Exception as e:
                db.rollback()
                logger.warning(f"Race condition adding paper {paper_id}, trying to fetch existing: {e}")
                paper = db.query(UserPaper).filter(UserPaper.paper_id == paper_id).first()
                if not paper:
                    raise HTTPException(status_code=500, detail=f"Failed to create or retrieve paper {paper_id}")
                
                # Update metadata if missing or if request has new info
                updated = False
                if not paper.authors or paper.authors == "Unknown":
                    paper.authors = metadata.authors
                    updated = True
                if not paper.summary:
                    paper.summary = metadata.summary
                    updated = True
                if not paper.published_date:
                    paper.published_date = metadata.published_date
                    updated = True
                if not paper.title or paper.title == paper_id:
                    paper.title = metadata.title
                    updated = True
                
                # Update extra fields from request if they are present and missing/different in DB
                if request.thumbnail and paper.thumbnail != request.thumbnail:
                    paper.thumbnail = request.thumbnail
                    updated = True
                if request.github_url and paper.github_url != request.github_url:
                    paper.github_url = request.github_url
                    updated = True
                if request.project_page and paper.project_page != request.project_page:
                    paper.project_page = request.project_page
                    updated = True
                     
                if updated:
                    db.commit()
                    logger.info(f"Updated metadata for existing paper {paper_id}")
    
    if paper not in project.papers:
        project.papers.append(paper)
        db.commit()
        
    # Trigger ingestion automatically if not completed
    if paper.ingestion_status != "completed":
        result = enqueue_ingestion(paper_id, background_tasks)
        # Only set pending status if job was successfully queued
        if result.get("queued"):
            paper.ingestion_status = "pending"
            db.commit()
            logger.info(f"Triggered background ingestion for {paper_id} via project {project_id} (method: {result.get('method')})")
        else:
            logger.warning(f"Failed to enqueue ingestion for {paper_id}, status not updated")
    
    return {"message": f"Added paper '{paper.title}' to project '{project.name}' and triggered ingestion."}

@router.delete("/projects/{project_id}/paper/{paper_id}")
def remove_paper_from_project(project_id: str, paper_id: str, db: Session = Depends(get_db)):
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
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project entirely."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    
    # Clear paper associations (papers are NOT deleted, just unlinked)
    project.papers.clear()
    db.delete(project)
    db.commit()
    
    return {"message": f"Project '{project.name}' deleted successfully."}
