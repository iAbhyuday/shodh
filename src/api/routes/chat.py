from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import json

from src.db.sql_db import get_db, Conversation, Message, UserPaper, SessionLocal
from src.api.schemas import ChatRequest, ProjectChatRequest, ConversationCreate, ConversationResponse

router = APIRouter()
logger = logging.getLogger(__name__)



# --- Endpoints ---

@router.get("/conversations")
def list_conversations(
    paper_id: Optional[str] = None, 
    project_id: Optional[int] = None, 
    db: Session = Depends(get_db)
):
    """List all conversations for a paper or project."""
    query = db.query(Conversation)
    if paper_id:
        query = query.filter(Conversation.paper_id == paper_id)
    elif project_id:
        query = query.filter(Conversation.project_id == project_id)
    else:
        raise HTTPException(status_code=400, detail="Either paper_id or project_id must be provided.")
        
    conversations = query.order_by(Conversation.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        msg_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        result.append({
            "id": conv.id,
            "paper_id": conv.paper_id,
            "project_id": conv.project_id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "message_count": msg_count
        })
    return result


@router.post("/conversations")
def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation for a paper or project."""
    conv = Conversation(
        paper_id=request.paper_id,
        project_id=request.project_id,
        title=request.title or "New Chat"
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "paper_id": conv.paper_id,
        "project_id": conv.project_id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None
    }


@router.get("/conversations/{conversation_id}/messages")
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

@router.post("/chat")
async def chat_with_paper(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat with a paper or project using RAG retrieval with Streaming Response.
    Delegates logic to ChatService.
    """
    from src.db.sql_db import Project
    from src.services.chat_service import ChatService
    
    # Identify retrieval context
    paper_ids = []
    context_meta = {} 
    
    if request.project_id:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        paper_ids = [p.paper_id for p in project.papers if p.ingestion_status == "completed"]
        if not paper_ids:
            raise HTTPException(status_code=400, detail="No ingested papers in this project yet.")
        context_meta["name"] = project.name
        context_meta["type"] = "project"
    else:
        if not request.paper_id:
            raise HTTPException(status_code=400, detail="Either paper_id or project_id must be provided.")
        paper = db.query(UserPaper).filter(UserPaper.paper_id == request.paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        if paper.ingestion_status != "completed":
            raise HTTPException(status_code=400, detail="Paper is not fully ingested yet")
        paper_ids = [paper.paper_id]
        context_meta["name"] = paper.title
        context_meta["type"] = "paper"
        project = None

    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conv = Conversation(
            paper_id=request.paper_id,
            project_id=request.project_id,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conversation_id = conv.id
    else:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.updated_at = datetime.utcnow()
            db.commit()

    # Save User Message immediately
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    return StreamingResponse(
        ChatService.chat_with_paper_generator(
            request=request,
            conversation_id=conversation_id,
            paper_ids=paper_ids,
            context_meta=context_meta,
            project=project if request.project_id else None
        ),
        media_type="text/plain"
    )

@router.post("/project-chat")
async def project_chat(request: ProjectChatRequest, db: Session = Depends(get_db)):
    """
    DEPRECATED: Use /api/chat with project_id instead.
    This endpoint is kept for backward compatibility.
    """
    # Convert ProjectChatRequest to ChatRequest and delegate
    from src.api.schemas import ChatRequest as CR
    
    unified_request = CR(
        project_id=request.project_id,
        message=request.message,
        conversation_id=request.conversation_id,
        history=request.history,
        use_agent=request.use_agent
    )
    
    return await chat_with_paper(unified_request, db)
