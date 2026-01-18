"""
Figures API routes - Fetch figure data for display in chat.
"""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.sql_db import SessionLocal, Figures

router = APIRouter(prefix="/api/figures", tags=["figures"])


class FigureResponse(BaseModel):
    figure_id: str
    paper_id: str
    section: str
    caption: str
    data: str  # base64 PNG


class FigureListItem(BaseModel):
    figure_id: str
    caption: str
    section: str


@router.get("/{paper_id}/{figure_id}", response_model=FigureResponse)
async def get_figure(paper_id: str, figure_id: str):
    """
    Fetch a specific figure by paper_id and figure_id.
    Returns the figure data as base64 PNG.
    """
    with SessionLocal() as db:
        fig = db.query(Figures).filter(
            Figures.paper_id == paper_id,
            Figures.figure_id == figure_id
        ).first()
        
        if not fig:
            raise HTTPException(status_code=404, detail="Figure not found")
        
        return FigureResponse(
            figure_id=fig.figure_id,
            paper_id=fig.paper_id,
            section=fig.section,
            caption=fig.caption,
            data=fig.data
        )


@router.get("/{paper_id}", response_model=List[FigureListItem])
async def list_figures(paper_id: str):
    """
    List all figures for a given paper.
    Returns metadata only (no image data) for efficient listing.
    """
    with SessionLocal() as db:
        figs = db.query(Figures).filter(Figures.paper_id == paper_id).all()
        
        return [
            FigureListItem(
                figure_id=f.figure_id,
                caption=f.caption,
                section=f.section
            )
            for f in figs
        ]
