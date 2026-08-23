from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import datetime
import logging
import json

from src.db.sql_db import get_db, Conversation, Message, UserPaper, SessionLocal
from src.api.schemas import ChatRequest, ProjectChatRequest, ConversationCreate, ConversationResponse
from src.core import session_log

router = APIRouter()
logger = logging.getLogger(__name__)


def _log_event(fn, *args, **kwargs):
    """Best-effort session-log append. Never breaks the chat flow if it fails.

    Transitional dual-write: events are logged alongside the existing Message
    rows. Phase 4 makes the log authoritative for model-visible history.
    """
    try:
        fn(*args, **kwargs)
    except Exception as exc:  # logging must not fail a live chat response
        logger.warning(f"session_log append failed: {exc}")



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


@router.get("/conversations/{conversation_id}/events")
def get_conversation_events(conversation_id: int, db: Session = Depends(get_db)):
    """The append-only session-event log for a conversation (provenance/audit)."""
    events = session_log.get_events(db, conversation_id)
    return [session_log.event_to_dict(e) for e in events]


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
        # Materialize project metadata now: the streaming generator may outlive
        # the request-scoped session, so lazy relationship loads there are unsafe.
        context_meta["paper_titles"] = [p.title for p in project.papers]
        context_meta["research_dimensions"] = project.research_dimensions
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
    _log_event(session_log.append_user_message, db, conversation_id, request.message)

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

            # Project synthesis is ALWAYS agentic (relating findings across papers
            # needs the search-then-synthesize loop); single-paper chat honors the
            # client's fast-mode opt-out.
            is_project = bool(request.project_id)
            wants_agent = is_project or request.use_agent

            if wants_agent and settings.AGENT_ENGINE == "loop":
                # === AGENTIC RAG via the streaming turn/step loop ===
                mode = "agent"
                from src.core.tools import ToolRegistry, PaperSearchTool
                from src.core.agent_loop import (
                    run_agent_turn,
                    RetrieveThenAnswerClient,
                    build_project_preamble,
                )
                from src.core.async_bridge import stream_sync_generator

                # Citations (for the metadata line) from a multi-paper retrieval.
                retrieved = await retriever.aquery(query_text=request.message, paper_id=paper_ids, top_k=5)
                for chunk in retrieved:
                    citations.append({
                        "content": chunk['content'],
                        "section": chunk['metadata'].get('section_type', 'unknown'),
                        "paper_id": chunk['metadata'].get('paper_id', 'unknown'),
                        "score": chunk.get('score', 0),
                    })
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"

                # Model-visible history is DERIVED FROM THE SESSION LOG.
                messages = session_log.derive_messages(session_log.get_events(db, conversation_id)) \
                    or [{"role": "user", "content": request.message}]

                registry = ToolRegistry()
                # Project chat searches across every ingested paper in the project.
                registry.register(PaperSearchTool(paper_ids, top_k=8 if is_project else 5))

                preamble = None
                if is_project:
                    preamble = build_project_preamble(
                        project_name=context_meta["name"],
                        paper_titles=context_meta.get("paper_titles", []),
                        research_dimensions=context_meta.get("research_dimensions"),
                    )
                client = RetrieveThenAnswerClient(
                    LLMFactory.get_llama_index_llm(), context_preamble=preamble
                )

                tool_events = []  # collected in the worker thread; persisted after streaming

                def _make_gen():
                    return run_agent_turn(
                        client, registry, messages,
                        on_event=lambda t, p: tool_events.append((t, p)),
                        max_steps=3,
                    )

                async for token in stream_sync_generator(_make_gen):
                    final_response_text += token
                    yield token

                # Persist the tool_call/tool_result events to the log.
                if tool_events:
                    ev_db = SessionLocal()
                    try:
                        for _t, _p in tool_events:
                            _log_event(session_log.append_event, ev_db, conversation_id, _t, _p)
                    finally:
                        ev_db.close()

            elif wants_agent:
                # === LEGACY: CrewAI crew (non-streaming, single-paper anchored) ===
                # Only reachable with AGENT_ENGINE=crew.
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
                _log_event(session_log.append_assistant_message, db_save, conversation_id, final_response_text, citations, mode)
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
    """Deprecated: project synthesis now runs through the unified /chat endpoint.

    Kept as a thin delegation so existing clients keep working. Project chat is
    always agentic, so the request maps directly onto ChatRequest.
    """
    logger.info("/project-chat is deprecated; delegating to /chat")
    return await chat_with_paper(
        ChatRequest(
            project_id=request.project_id,
            message=request.message,
            conversation_id=request.conversation_id,
            history=request.history,
            use_agent=True,  # project synthesis is always agentic
        ),
        db,
    )
