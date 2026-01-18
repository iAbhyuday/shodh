"""
Background jobs for chat functionality.
"""
import logging
import asyncio
import json
from typing import List, Optional

from src.db.sql_db import SessionLocal, Message, Conversation
from src.agents.paper_crew import run_paper_crew
from src.services.agent_chat import AgentChat

logger = logging.getLogger(__name__)

async def process_agent_message_job(
    paper_ids: List[str],
    message: str,
    conversation_id: str,
    context_name: str,
    history: Optional[str] = None
):
    """
    Background job to run the agent pipeline and save the result.
    This function is intended to be run by an RQ worker.
    """
    logger.info(f"Starting background agent job for conversation {conversation_id}")
    
    try:
        # Since run_paper_crew is synchronous (mostly) but we might want to verify async behavior
        # In the context of RQ, we are in a separate process, so blocking is fine.
        
        # 1. Run the agent logic
        # We reuse the logic from AgentChat.run, but we need to extract the core non-streaming parts
        # Or just call run_paper_crew directly and handle citations manually like AgentChat does.
        
        # NOTE: run_paper_crew is designed to be synchronous compatible?
        # Let's look at AgentChat.run implementation. 
        # It calls `run_in_threadpool(run_paper_crew...)`
        # In an RQ worker, we can just call it directly.
        
        logger.info(f"Running CrewAI for query: {message}")
        result = run_paper_crew(
            paper_ids=paper_ids,
            paper_title=context_name,
            user_query=message,
            chat_history=history
        )
        
        # 2. Process result
        response_text = ""
        warnings = []
        
        if isinstance(result, dict):
            response_text = result.get('answer', str(result))
            warnings = result.get('warnings', [])
            if warnings:
                logger.warning(f"Agent warnings: {warnings}")
        else:
            response_text = str(result)
            
        # 3. Retrieve Citations (using retrieval logic from AgentChat)
        # We need to run the async retrieval in this sync worker context
        # We can use asyncio.run() since we are at the top level of the job
        from src.core.retriever import get_retriever
        
        from src.core.retriever import get_retriever
        
        retriever = get_retriever()
        retrieved_chunks = retriever.query(
            query_text=message,
            paper_id=paper_ids,
            top_k=5
        )
        
        citations = []
        for i, chunk in enumerate(retrieved_chunks):
            section = chunk['metadata'].get('section', 'Excerpt')
            if isinstance(section, str):
                section = section.title()
            
            citations.append({
                "id": i + 1,
                "content": chunk['content'][:500],
                "section": section,
                "paper_id": chunk['metadata'].get('paper_id', ''),
                "section_title": chunk['metadata'].get('section_title', ''),
                "page_number": chunk['metadata'].get('page_number'),
                "score": round(chunk.get('score', 0), 3)
            })
            
        # 4. Save to Database
        db = SessionLocal()
        try:
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_text,
                citations_json=json.dumps(citations) if citations else None,
                mode="agent_job"
            )
            db.add(msg)
            
            # Also update conversation timestamp
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if conv:
                from datetime import datetime
                conv.updated_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Job complete. Saved message to conversation {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save job result to DB: {e}")
        finally:
            db.close()
            
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "response_length": len(response_text)
        }

    except Exception as e:
        logger.exception(f"Agent job failed: {e}")
        # Save error message to DB so user sees it
        db = SessionLocal()
        try:
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=f"**Error during background processing:** {str(e)}",
                mode="agent_job_error"
            )
            db.add(msg)
            db.commit()
        finally:
            db.close()
        
        return {"status": "error", "error": str(e)}
