from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
import logging
import json

from src.db.sql_db import get_db, Conversation, Message, UserPaper, SessionLocal
from src.api.schemas import ChatRequest, ConversationCreate, ConversationResponse

router = APIRouter()
logger = logging.getLogger(__name__)



# --- Endpoints ---

@router.get("/conversations")
def list_conversations(
    paper_id: Optional[str] = None, 
    project_id: Optional[str] = None, 
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
def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db)):
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
    Chat with a paper or project using RAG or Agent mode.
    
    Routes to:
    - ChatRAG: Standard RAG for single/multi-paper queries (use_agent=False)
    - AgentChat: Multi-step agentic reasoning (use_agent=True)
    """
    from src.db.sql_db import Project
    
    # Identify retrieval context
    paper_ids = []
    context_name = ""
    project_dimensions = None
    is_ingested = True  # Default: assume ingested (projects filter by status)
    
    if request.project_id:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        paper_ids = [p.paper_id for p in project.papers if p.ingestion_status == "completed"]
        if not paper_ids:
            raise HTTPException(status_code=400, detail="No ingested papers in this project yet.")
        context_name = project.name
        project_dimensions = project.research_dimensions
    else:
        if not request.paper_id:
            raise HTTPException(status_code=400, detail="Either paper_id or project_id must be provided.")
        paper = db.query(UserPaper).filter(UserPaper.paper_id == request.paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Check if paper is ingested - if not, use abstract-only mode
        is_ingested = paper.ingestion_status == "completed"
        paper_ids = [paper.paper_id]
        context_name = paper.title

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

    # Save User Message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    # Route to appropriate service
    if request.use_job and request.use_agent:
        # Offload to Redis background job
        from src.jobs.queue import get_queue
        from src.jobs.chat_jobs import process_agent_message_job
        
        queue = get_queue()
        if not queue:
            raise HTTPException(status_code=503, detail="Background job service unavailable")
            
        # Format history for agent
        history_text = ""
        if request.history:
            for msg in request.history[-5:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_text += f"{role.upper()}: {content}\n"
        
        job = queue.enqueue(
            process_agent_message_job,
            paper_ids=paper_ids,
            message=request.message,
            conversation_id=conversation_id,
            context_name=context_name,
            history=history_text if history_text else None,
            job_timeout="10m"
        )
        
        return {
            "conversation_id": conversation_id,
            "job_id": job.id,
            "status": "queued",
            "message": "Agent task started in background"
        }

    # Standard Streaming Response
    elif request.use_agent:
        # Agentic mode - multi-step reasoning (Synchronous Stream)
        from src.services.agent_chat import AgentChat
        
        # Format history for agent
        history_text = ""
        if request.history:
            for msg in request.history[-5:]:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_text += f"{role.upper()}: {content}\n"
        
        return StreamingResponse(
            AgentChat.run(
                paper_ids=paper_ids,
                message=request.message,
                conversation_id=conversation_id,
                context_name=context_name,
                history=history_text if history_text else None
            ),
            media_type="text/plain"
        )
    else:
        # RAG mode - standard retrieval augmented generation
        from src.services.chat import ChatRAG
        
        # For single papers: check if ingested, otherwise use abstract mode
        if not request.project_id and not is_ingested:
            # Abstract-only mode for non-ingested papers
            return StreamingResponse(
                ChatRAG.abstract_stream(
                    paper_id=paper.paper_id,
                    paper_title=paper.title or f"Paper {paper.paper_id}",
                    paper_abstract=paper.summary or "",
                    message=request.message,
                    conversation_id=conversation_id,
                    history=request.history
                ),
                media_type="text/plain"
            )
        
        # Full RAG mode for ingested papers/projects
        return StreamingResponse(
            ChatRAG.stream(
                paper_ids=paper_ids,
                message=request.message,
                conversation_id=conversation_id,
                history=request.history,
                project_dimensions=project_dimensions
            ),
            media_type="text/plain"
        )

