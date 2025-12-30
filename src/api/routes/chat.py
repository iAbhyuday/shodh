from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import datetime
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
    Protocol:
    - Line 1: JSON Metadata (conversation_id, citations, mode)
    - Line 2+: Content tokens
    """
    from src.db.sql_db import Project
    
    # Identify retrieval context
    paper_ids = []
    context_meta = {} # To hold paper info for prompt
    
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
            conv.updated_at = datetime.datetime.utcnow()
            db.commit()

    # Save User Message immediately
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    async def chat_generator():
        from src.core.config import get_settings
        from src.core.retriever import PaperRetriever
        from starlette.concurrency import run_in_threadpool
        from src.core.llm_factory import LLMFactory
        
        settings = get_settings()
        retriever = PaperRetriever()
        
        try:
            # History
            history_text = ""
            if request.history:
                for msg in request.history[-5:]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    history_text += f"{role.upper()}: {content}\n"

            final_response_text = ""
            citations = []
            mode = "contextual"

            if request.use_agent:
                # === AGENTIC RAG (Non-streaming for Project Synthesis) ===
                mode = "agent"
                from src.agents.paper_crew import run_paper_crew
                
                # Use first paper for Agent if deep-dive, else generic synthesis
                target_paper_id = request.paper_id if request.paper_id else paper_ids[0]
                
                response_text = await run_in_threadpool(
                    run_paper_crew,
                    paper_id=target_paper_id,
                    paper_title=context_meta["name"],
                    user_query=request.message,
                    chat_history=history_text if history_text else None
                )
                final_response_text = response_text

                # Retrieve citations from PROJECT context (multi-paper)
                retrieved = await retriever.aquery(
                    query_text=request.message,
                    paper_id=paper_ids,
                    top_k=5
                )
                for chunk in retrieved:
                    citations.append({
                        "content": chunk['content'],
                        "section": chunk['metadata'].get('section_type', 'unknown'),
                        "section_title": chunk['metadata'].get('section_title', ''),
                        "page_number": chunk['metadata'].get('page_number', None),
                        "score": chunk.get('score', 0)
                    })

                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                yield response_text

            else:
                # === CONTEXTUAL RAG (Streaming) ===
                mode = "contextual"
                
                # Multi-paper retrieval
                retrieved = await retriever.aquery(
                    query_text=request.message,
                    paper_id=paper_ids,
                    top_k=8 if request.project_id else 5 # More context for projects
                )
                
                context_parts = []
                for chunk in retrieved:
                    section = chunk['metadata'].get('section_type', 'unknown')
                    source = chunk['metadata'].get('paper_id', 'unknown')
                    context_parts.append(f"[SOURCE: {source}, SECTION: {section.upper()}]: {chunk['content']}")
                    citations.append({
                        "content": chunk['content'],
                        "section": section,
                        "paper_id": source,
                        "section_title": chunk['metadata'].get('section_title', ''),
                        "page_number": chunk['metadata'].get('page_number', None),
                        "score": chunk.get('score', 0)
                    })
                
                context = "\n\n".join(context_parts)
                llm = LLMFactory.get_llama_index_llm()
                
                dimensions_context = ""
                if request.project_id and project.research_dimensions:
                    dimensions_context = f"\nRESEARCH DIMENSIONS & GOALS FOR THIS PROJECT:\n{project.research_dimensions}\n"

                prompt = f"""You are a precise research assistant labeled 'Shodh AI'.
You are analyzing the {context_meta['type']} "{context_meta['name']}".
{dimensions_context}
GOAL: Answer the user's question using the provided context and respect the research dimensions if provided.
If it's a PROJECT, synthesize info across multiple papers.
FORMAT: Use clear, structured Markdown.
- Use **bold** for key concepts.
- Use bullet points for lists.
- Keep responses concise and note-like.
 
CONTEXT FROM PAPERS:
{context}
 
{history_text}
USER: {request.message}
 
A:"""
                
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"

                response_gen = await llm.astream_complete(prompt)
                async for chunk in response_gen:
                    token = chunk.delta
                    if token:
                        final_response_text += token
                        yield token

            # Post-stream save
            db_save = SessionLocal()
            try:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_response_text,
                    citations_json=json.dumps(citations) if citations else None,
                    mode=mode
                )
                db_save.add(assistant_msg)
                db_save.commit()
            except Exception as e:
                logger.error(f"Failed to save assistant message: {e}")
            finally:
                db_save.close()

        except Exception as e:
            logger.exception(f"Chat stream error: {e}")
            yield f"\n\n[Error processing request: {str(e)}]"

    return StreamingResponse(chat_generator(), media_type="text/plain")
@router.post("/project-chat")
async def project_chat(request: ProjectChatRequest, db: Session = Depends(get_db)):
    """
    Dedicated endpoint for project-level chat/synthesis.
    Fetches project details, papers, and uses research dimensions to guide the response.
    """
    from src.db.sql_db import Project
    
    project = db.query(Project).filter(Project.id == request.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    paper_ids = [p.paper_id for p in project.papers if p.ingestion_status == "completed"]
    if not paper_ids:
        raise HTTPException(status_code=400, detail="No ingested papers in this project yet.")
        
    paper_info = [f"- {p.title} (ArXiv: {p.paper_id})" for p in project.papers]
    paper_list_str = "\n".join(paper_info)
    
    # Get or create conversation
    conversation_id = request.conversation_id
    if not conversation_id:
        conv = Conversation(
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
            conv.updated_at = datetime.datetime.utcnow()
            db.commit()

    # Save User Message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=request.message
    )
    db.add(user_msg)
    db.commit()

    async def project_chat_generator():
        from src.core.config import get_settings
        from src.core.retriever import PaperRetriever
        from starlette.concurrency import run_in_threadpool
        from src.core.llm_factory import LLMFactory
        
        settings = get_settings()
        retriever = PaperRetriever()
        
        try:
            history_text = ""
            if request.history:
                for msg in request.history[-5:]:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    history_text += f"{role.upper()}: {content}\n"

            final_response_text = ""
            citations = []
            mode = "agent" if request.use_agent else "contextual"

            if request.use_agent:
                from src.agents.paper_crew import run_paper_crew
                # For project synthesis agent, use a generic multi-paper approach
                response_text = await run_in_threadpool(
                    run_paper_crew,
                    paper_id=paper_ids[0], # Using first paper as anchor for now
                    paper_title=project.name,
                    user_query=f"Analyze across these papers: {request.message}",
                    chat_history=history_text if history_text else None
                )
                final_response_text = response_text
                
                # Retrieval for citations
                retrieved = await retriever.aquery(request.message, paper_id=paper_ids, top_k=5)
                for chunk in retrieved:
                    citations.append({
                        "content": chunk['content'],
                        "section": chunk['metadata'].get('section_type', 'unknown'),
                        "paper_id": chunk['metadata'].get('paper_id', 'unknown'),
                        "score": chunk.get('score', 0)
                    })
                
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                yield response_text
            else:
                retrieved = await retriever.aquery(request.message, paper_id=paper_ids, top_k=10)
                context_parts = []
                for chunk in retrieved:
                    source = chunk['metadata'].get('paper_id', 'unknown')
                    context_parts.append(f"[PAPER: {source}]: {chunk['content']}")
                    citations.append({
                        "content": chunk['content'],
                        "paper_id": source,
                        "section": chunk['metadata'].get('section_type', 'unknown'),
                        "score": chunk.get('score', 0)
                    })
                
                context = "\n\n".join(context_parts)
                dimensions = f"\nPROJECT GOALS & DIMENSIONS:\n{project.research_dimensions}\n" if project.research_dimensions else ""
                
                prompt = f"""You are 'Shodh AI', a research architect synthesizing multiple papers for the project "{project.name}".

{dimensions}

PAPERS IN THIS PROJECT:
{paper_list_str}

GOAL: Synthesize the provided context to answer the user's query thoughtfully. 
Relate findings across different papers where applicable.

CONTEXT:
{context}

{history_text}
USER: {request.message}
A:"""
                
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                llm = LLMFactory.get_llama_index_llm()
                response_gen = await llm.astream_complete(prompt)
                async for chunk in response_gen:
                    if chunk.delta:
                        final_response_text += chunk.delta
                        yield chunk.delta

            # Save assistant message
            db_save = SessionLocal()
            try:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=final_response_text,
                    citations_json=json.dumps(citations) if citations else None,
                    mode=mode
                )
                db_save.add(assistant_msg)
                db_save.commit()
            finally:
                db_save.close()

        except Exception as e:
            logger.exception(f"Project chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    return StreamingResponse(project_chat_generator(), media_type="text/plain")
