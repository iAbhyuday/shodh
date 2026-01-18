"""
AgentChat - Agentic chat with multi-step reasoning.

This module provides an agentic chat experience with:
- Multi-step planning and execution
- Integration with CrewAI paper_crew
- Complex reasoning tasks

Note: Currently uses a placeholder implementation while the full
agent pipeline is being reimplemented.
"""

import logging
import json
from typing import AsyncGenerator, List, Dict, Optional

from starlette.concurrency import run_in_threadpool

from src.core.retriever import get_retriever
from src.db.sql_db import SessionLocal, Message

logger = logging.getLogger(__name__)


class AgentChat:
    """
    Agentic chat service with multi-step reasoning.
    
    This class provides a higher-level chat experience that uses
    multi-agent collaboration for complex research tasks like:
    - Cross-paper synthesis
    - Research gap identification
    - Methodology comparison
    
    Usage:
        async for token in AgentChat.run(
            paper_ids=["2301.12345", "2302.54321"],
            message="Compare the approaches in these papers",
            conversation_id="conv-123",
            context_name="My Research Project"
        ):
            print(token, end="")
    """
    
    @classmethod
    async def run(
        cls,
        paper_ids: List[str],
        message: str,
        conversation_id: str,
        context_name: str,
        history: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Run the agent pipeline.
        
        Args:
            paper_ids: List of paper IDs to analyze
            message: User's query
            conversation_id: Conversation ID for persistence
            context_name: Name of the paper or project
            history: Optional formatted chat history string
            
        Yields:
            First line: JSON metadata (conversation_id, citations, mode)
            Subsequent: Response text (non-streaming for agent mode)
        """
        from src.agents.paper_crew import run_paper_crew
        
        retriever = get_retriever()
        citations = []
        
        try:
            # Run the agent pipeline
            logger.info(f"AgentChat: Running agent for query: {message}")
            
            result = await run_in_threadpool(
                run_paper_crew,
                paper_ids=paper_ids,
                paper_title=context_name,
                user_query=message,
                chat_history=history
            )
            
            # Handle both dict and string responses
            if isinstance(result, dict):
                response_text = result.get('answer', str(result))
                warnings = result.get('warnings', [])
                if warnings:
                    logger.warning(f"Agent warnings: {warnings}")
            else:
                response_text = str(result)
            
            # Retrieve citations for the response
            retrieved = await retriever.aquery(
                query_text=message,
                paper_id=paper_ids,
                top_k=5
            )
            
            for i, chunk in enumerate(retrieved):
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
            
            # Yield metadata
            metadata = {
                "conversation_id": conversation_id,
                "citations": citations,
                "mode": "agent"
            }
            yield json.dumps(metadata) + "\n"
            
            # Yield response (non-streaming for agent mode)
            yield response_text
            
            # Save to database
            cls._save_message(
                conversation_id=conversation_id,
                content=response_text,
                citations=citations
            )
            
            logger.info(f"AgentChat: Complete ({len(response_text)} chars)")
            
        except Exception as e:
            logger.exception(f"AgentChat error: {e}")
            yield json.dumps({
                "conversation_id": conversation_id,
                "citations": [],
                "mode": "agent"
            }) + "\n"
            yield f"[Error in agent pipeline: {str(e)}]"
    
    @staticmethod
    def _save_message(conversation_id: str, content: str, citations: List[Dict]):
        """Save the assistant message to the database."""
        db = SessionLocal()
        try:
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                citations_json=json.dumps(citations) if citations else None,
                mode="agent"
            )
            db.add(msg)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
        finally:
            db.close()
