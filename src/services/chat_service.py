import logging
import json
import datetime
from typing import AsyncGenerator, List, Dict, Any, Optional

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.core.config import get_settings
from src.core.retriever import PaperRetriever
from src.core.llm_factory import LLMFactory
from src.db.sql_db import SessionLocal, Message, Project
from src.api.schemas import ChatRequest, ProjectChatRequest

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service to handle retrieval, prompt construction, and LLM streaming for chats.
    """



    @staticmethod
    async def _stage1_analyze_query(chat_history: str, last_message: str) -> str:
        """Stage 1: Figure out what user wants (Condense/Rewrite)."""
        if not chat_history.strip():
             return last_message
            
        llm = LLMFactory.get_llama_index_llm()
        prompt = f"""Given the conversation history and the user's latest query, formulate a standalone search query that fully captures the user's intent.
If the user is asking a follow-up (e.g. "in table", "explain that equation"), replace pronouns with specific subjects from history.
HISTORY:
{chat_history}
USER: {last_message}
STANDALONE SEARCH QUERY:"""
        
        try:
            response = await llm.acomplete(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Stage 1 analysis failed: {e}")
            return last_message

    @staticmethod
    async def _stage2_draft_response(query: str, context: str, dimensions: str = "") -> str:
        """Stage 2: Find info and form comprehensive draft response."""
        llm = LLMFactory.get_llama_index_llm()
        prompt = f"""You are a Deep Learning Researcher. Draft a comprehensive answer to the query based *only* on the provided context.
QUERY: {query}
{dimensions}

CONTEXT:
{context}

INSTRUCTIONS:
1. Answer accurately and comprehensively.
2. Include all necessary technical details and math.
3. If a comparison is asked, outline the points of comparison.
4. **CRITICAL**: You MUST cite your sources. Use inline citation markers [1], [2] corresponding to the provided context chunks.
5. Do not worry about perfect formatting yet. Focus on Content.

DRAFT ANSWER:"""
        
        response = await llm.acomplete(prompt)
        return response.text

    @staticmethod
    async def _stage3_format_response_stream(draft: str, context: str) -> AsyncGenerator[str, None]:
        """Stage 3: Follow rules and format the final answer (Streaming)."""
        llm = LLMFactory.get_llama_index_llm()
        prompt = fr"""You are a Technical Editor and LaTeX Expert. Rewrite the following DRAFT ANSWER into a perfect, production-ready response.

RULES:
1. **Tone**: Educational, expert, and helpful.
2. **Math**: Use LaTeX formatting strictly.
   - Inline: $ E = mc^2 $
   - Block: $$ E = mc^2 $$
   - No \(` or `\[`.
3. **Tables**: Use standard Markdown tables. **DO NOT** wrap tables in code blocks (```).
4. **Citations**: Ensure every distinct claim has an inline citation `[1]`, `[2]` matching the context.
   - If the draft mentions (Source 1), convert to `[1]`.
5. **Layout**: Use bold headers, bullet points, and clear structure.

CONTEXT (For Reference):
{context}

DRAFT ANSWER:
{draft}

FINAL POLISHED RESPONSE:"""
        from llama_index.core.llms import ChatMessage
        messages = [ChatMessage(role="user", content=prompt)]
        
        response_gen = await llm.astream_chat(messages)
        async for chunk in response_gen:
            if chunk.delta:
                yield chunk.delta

    @staticmethod
    async def chat_with_paper_generator(
        request: ChatRequest,
        conversation_id: int,
        paper_ids: List[str],
        context_meta: Dict[str, Any],
        project: Optional[Project] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates variables stream for single paper (or focused project paper) chat.
        """
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
                
                # Use first paper for Agent if deep-dive
                target_paper_id = request.paper_id if request.paper_id else paper_ids[0]
                
                response_text = await run_in_threadpool(
                    run_paper_crew,
                    paper_ids=paper_ids,
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
                for i, chunk in enumerate(retrieved):
                    # FIX: Use 'section' instead of 'section_type'
                    section = chunk['metadata'].get('section', 'Excerpt')
                    if isinstance(section, str):
                        section = section.title()
                    citations.append({
                        "content": chunk['content'],
                        "section": section,
                        "section_title": chunk['metadata'].get('section_title', ''),
                        "page_number": chunk['metadata'].get('page_number', None),
                        "summary": chunk['metadata'].get('section_summary', ''),
                        "score": chunk.get('score', 0)
                    })

                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                yield response_text

            else:
                # === CONTEXTUAL RAG (Multi-Stage) ===
                mode = "contextual"
                
                # Stage 1: Analyze Intent
                query_to_use = await ChatService._stage1_analyze_query(history_text, request.message)
                logger.info(f"Stage 1: {request.message} -> {query_to_use}")
                
                # Retrieval
                retrieved = await retriever.aquery(
                    query_text=query_to_use,
                    paper_id=paper_ids,
                    top_k=8 if request.project_id else 5
                )
                
                citations = []
                context_parts = []
                for i, chunk in enumerate(retrieved):
                    # FIX: Use 'section' instead of 'section_type'
                    section = chunk['metadata'].get('section', 'Excerpt')
                    if isinstance(section, str):
                         section = section.title()
                    source = chunk['metadata'].get('paper_id', 'unknown')
                    context_parts.append(f"[{i+1}] [SOURCE: {source}, SECTION: {section.upper()}]: {chunk['content']}")
                    citations.append({
                        "content": chunk['content'],
                        "section": section,
                        "paper_id": source,
                        "section_title": chunk['metadata'].get('section_title', ''),
                        "page_number": chunk['metadata'].get('page_number', None),
                        "section_title": chunk['metadata'].get('section_title', ''),
                        "page_number": chunk['metadata'].get('page_number', None),
                        "summary": chunk['metadata'].get('section_summary', ''),
                        "score": chunk.get('score', 0)
                    })
                
                context = "\n\n".join(context_parts)
                
                # Send Citations to Frontend immediately
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"

                dimensions_context = ""
                if request.project_id and project and project.research_dimensions:
                    dimensions_context = f"\nRESEARCH DIMENSIONS: {project.research_dimensions}\n"

                # Stage 2: Draft Content
                draft = await ChatService._stage2_draft_response(query_to_use, context, dimensions_context)
                logger.debug(f"Stage 2 Draft: {draft[:100]}...")

                # Stage 3: Format & Stream
                async for token in ChatService._stage3_format_response_stream(draft, context):
                    final_response_text += token
                    yield token

            # Post-stream save (DB ops in separate session to be safe)

            # Post-stream save (DB ops in separate session to be safe)
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

    @staticmethod
    async def project_chat_generator(
        request: ProjectChatRequest,
        conversation_id: int,
        project: Project,
        paper_ids: List[str]
    ) -> AsyncGenerator[str, None]:
        """
        Generates stream for project synthesis chat.
        """
        retriever = PaperRetriever()
        
        # Prepare paper info str
        paper_info = [f"- {p.title} (ArXiv: {p.paper_id})" for p in project.papers]
        paper_list_str = "\n".join(paper_info)
        
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
                # === AGENTIC MODE ===
                from src.agents.paper_crew import run_paper_crew
                response_text = await run_in_threadpool(
                    run_paper_crew,
                    paper_ids=paper_ids,
                    paper_title=project.name,
                    user_query=f"Analyze across these papers: {request.message}",
                    chat_history=history_text if history_text else None
                )
                final_response_text = response_text
                
                # Retrieval for citations
                retrieved = await retriever.aquery(request.message, paper_id=paper_ids, top_k=5)
                for i, chunk in enumerate(retrieved):
                     # FIX: Use 'section' instead of 'section_type'
                    section = chunk['metadata'].get('section', 'Excerpt')
                    if isinstance(section, str):
                        section = section.title()
                    citations.append({
                        "content": chunk['content'],
                        "section": section,
                        "paper_id": chunk['metadata'].get('paper_id', 'unknown'),
                        "paper_id": chunk['metadata'].get('paper_id', 'unknown'),
                        "summary": chunk['metadata'].get('section_summary', ''),
                        "score": chunk.get('score', 0)
                    })
                
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                yield response_text
            else:
                # === CONTEXTUAL MODE (Multi-Stage) ===
                
                # Stage 1
                query_to_use = await ChatService._stage1_analyze_query(history_text, request.message)
                logger.info(f"Project Stage 1: {request.message} -> {query_to_use}")

                retrieved = await retriever.aquery(query_to_use, paper_id=paper_ids, top_k=10)
                context_parts = []
                citations = []
                for i, chunk in enumerate(retrieved):
                    source = chunk['metadata'].get('paper_id', 'unknown')
                    # FIX: Use 'section'
                    section = chunk['metadata'].get('section', 'Excerpt')
                    if isinstance(section, str):
                        section = section.title()
                    context_parts.append(f"[{i+1}] [PAPER: {source}]: {chunk['content']}")
                    citations.append({
                        "content": chunk['content'],
                        "paper_id": source,
                        "section": section,
                        "section": section,
                        "summary": chunk['metadata'].get('section_summary', ''),
                        "score": chunk.get('score', 0)
                    })
                
                context = "\n\n".join(context_parts)
                dimensions = f"\nPROJECT GOALS & DIMENSIONS:\n{project.research_dimensions}\n" if project.research_dimensions else ""
                
                # Yield Header
                yield json.dumps({"conversation_id": conversation_id, "citations": citations, "mode": mode}) + "\n"
                
                # Stage 2
                draft = await ChatService._stage2_draft_response(
                    query=f"Synthesize info from these papers: {paper_list_str}\nQUESTION: {query_to_use}", 
                    context=context, 
                    dimensions=dimensions
                )
                
                # Stage 3
                async for token in ChatService._stage3_format_response_stream(draft, context):
                    final_response_text += token
                    yield token

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
            except Exception as e:
                logger.error(f"Failed to save assistant for project chat: {e}")
            finally:
                db_save.close()

        except Exception as e:
            logger.exception(f"Project chat error: {e}")
            yield f"\n\n[Error: {str(e)}]"
