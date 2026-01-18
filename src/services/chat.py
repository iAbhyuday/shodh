"""
ChatRAG - Unified RAG-based chat service for papers and projects.

This module provides retrieval-augmented generation chat for:
- Single paper queries
- Multi-paper project synthesis

Features:
- Query rewriting for follow-up questions
- Quality-filtered retrieval with scoring
- Streaming responses with citations
- Conversation history support
"""

import logging
import json
from typing import AsyncGenerator, List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

from src.core.config import get_settings
from src.core.retriever import get_retriever
from src.core.llm_factory import LLMFactory
from src.db.sql_db import SessionLocal, Message

logger = logging.getLogger(__name__)


class RetrieverAdapter:
    """
    Adapts QdrantRetriever for use with LangChain chains.
    Supports both single papers and multi-paper queries.
    """
    
    def __init__(
        self, 
        paper_ids: List[str], 
        top_k: int = 8, 
        min_score: float = 0.3
    ):
        self.retriever = get_retriever()
        self.paper_ids = paper_ids if isinstance(paper_ids, list) else [paper_ids]
        self.top_k = top_k
        self.min_score = min_score
        self._last_results: List[Dict] = []
    
    def invoke(self, query: str) -> str:
        """
        Retrieve relevant chunks with quality filtering.
        
        Args:
            query: The search query
            
        Returns:
            Formatted context string with numbered citations
        """
        # Query across all paper IDs
        results = self.retriever.query(
            query_text=query,
            paper_id=self.paper_ids[0] if len(self.paper_ids) == 1 else self.paper_ids,
            top_k=self.top_k
        )
        
        # Filter by minimum score (quality control)
        filtered = [r for r in results if r.get('score', 0) >= self.min_score]
        
        # If too few results after filtering, take top results anyway
        if len(filtered) < 3:
            filtered = results[:5]
        
        self._last_results = filtered
        
        # Format as numbered context for the LLM
        context_parts = []
        for i, chunk in enumerate(filtered):
            section = chunk['metadata'].get('section', 'Excerpt')
            if isinstance(section, str):
                section = section.title()
            
            paper_id = chunk['metadata'].get('paper_id', 'unknown')
            score = chunk.get('score', 0)
            figures = chunk['metadata'].get('figures', '')  # Figure references extracted during ingestion
            
            # Build figure reference note if figures are present
            fig_note = f" (References: {figures})" if figures and figures.strip() else ""
            
            # Include paper_id for multi-paper context
            if len(self.paper_ids) > 1:
                context_parts.append(
                    f"[{i+1}] [Paper: {paper_id}] [{section}]{fig_note} (relevance: {score:.2f}):\n{chunk['content']}"
                )
            else:
                context_parts.append(
                    f"[{i+1}] [{section}]{fig_note} (relevance: {score:.2f}):\n{chunk['content']}"
                )
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_citations(self) -> List[Dict]:
        """Get structured citations from the last retrieval."""
        citations = []
        for i, chunk in enumerate(self._last_results):
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
                "figures": chunk['metadata'].get('figures', ''),  # Figure references for frontend
                "score": round(chunk.get('score', 0), 3)
            })
        return citations


class ChatRAG:
    """
    RAG-based chat service for papers and projects.
    
    Usage:
        async for token in ChatRAG.stream(
            paper_ids=["2301.12345"],
            message="What is the main contribution?",
            conversation_id="conv-123"
        ):
            print(token, end="")
    """
    
    # Prompt for rewriting follow-up questions
    REWRITE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """You are a query rewriting assistant. Given a conversation history and a follow-up question, 
rewrite the question to be a standalone question that captures the full context.

Rules:
1. If the question references "it", "this", "that", etc., replace with the specific subject from history
2. If the question is already standalone, return it unchanged
3. Keep the rewritten question concise but complete
4. Output ONLY the rewritten question, nothing else"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Follow-up question: {question}\n\nRewritten standalone question:")
    ])
    
    # Main RAG prompt with few-shot examples
    RAG_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """You are a research assistant. Answer based ONLY on the context below.

## Output Format Examples

**Example 1 (with citations and math):**
The paper introduces a novel approach using transformers [1]. The loss function is defined as $L = -\\sum_i y_i \\log(p_i)$ [2]. For vectors in $\\mathbb{{R}}^3$, the distance is computed as:

$$d(x, y) = \\|x - y\\|_2$$

**Example 2 (with figure reference):**
As shown in [Figure 1], the model architecture consists of three main components [1][2].

## Rules
1. Add citations [1], [2] after each fact
2. Math: inline $x^2$, block $$E=mc^2$$
3. Figures: [Figure 1], [Figure 2]
4. Use markdown, no HTML
{dimensions}

## Context
{context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    @classmethod
    def _format_history(cls, history: List[Dict], max_turns: int = 5) -> List:
        """Convert history dicts to LangChain messages, limiting to recent turns."""
        messages = []
        recent = history[-(max_turns * 2):] if len(history) > max_turns * 2 else history
        
        for msg in recent:
            content = msg.get('content', '')
            # Truncate very long messages to save context
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            if msg.get('role') == 'user':
                messages.append(HumanMessage(content=content))
            elif msg.get('role') == 'assistant':
                messages.append(AIMessage(content=content))
        return messages
    
    @classmethod
    async def _rewrite_query(cls, question: str, history: List[Dict]) -> str:
        """
        Rewrite follow-up questions to be standalone.
        Only rewrites if there's conversation history.
        """
        if not history:
            return question
        
        try:
            llm = LLMFactory.get_langchain_llm(streaming=False)
            chain = cls.REWRITE_PROMPT | llm | StrOutputParser()
            
            chat_history = cls._format_history(history, max_turns=3)
            
            rewritten = await chain.ainvoke({
                "chat_history": chat_history,
                "question": question
            })
            
            rewritten = rewritten.strip()
            if rewritten and len(rewritten) > 5:
                logger.info(f"Query rewritten: '{question}' -> '{rewritten}'")
                return rewritten
            return question
            
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return question
    
    @classmethod
    async def stream(
        cls,
        paper_ids: List[str],
        message: str,
        conversation_id: str,
        history: Optional[List[Dict]] = None,
        project_dimensions: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a RAG chat response.
        
        Args:
            paper_ids: List of paper IDs to search
            message: User's message
            conversation_id: Conversation ID for persistence
            history: Previous conversation messages
            project_dimensions: Optional research dimensions for project context
            
        Yields:
            First line: JSON metadata (conversation_id, citations, mode)
            Subsequent: Streamed response tokens
        """
        # Adjust retrieval based on number of papers
        top_k = 10 if len(paper_ids) > 1 else 8
        retriever = RetrieverAdapter(paper_ids=paper_ids, top_k=top_k, min_score=0.3)
        llm = LLMFactory.get_langchain_llm(streaming=True)
        
        try:
            # Step 1: Query Rewriting (for follow-up questions)
            history = history or []
            if history:
                query = await cls._rewrite_query(message, history)
            else:
                query = message
            
            # Step 2: Retrieve context with quality filtering
            logger.info(f"ChatRAG: Retrieving for '{query}' (papers: {paper_ids})")
            context = retriever.invoke(query)
            citations = retriever.get_citations()
            logger.info(f"ChatRAG: Retrieved {len(citations)} chunks")
            
            # Step 3: Send metadata first
            metadata = {
                "conversation_id": conversation_id,
                "citations": citations,
                "mode": "rag",
                "original_query": message,
                "rewritten_query": query if query != message else None
            }
            yield json.dumps(metadata) + "\n"
            
            # Step 4: Build and stream response
            dimensions_text = ""
            if project_dimensions:
                dimensions_text = f"\nRESEARCH DIMENSIONS: {project_dimensions}\n"
            
            chain = cls.RAG_PROMPT | llm | StrOutputParser()
            chat_history = cls._format_history(history, max_turns=5)
            
            full_response = ""
            async for token in chain.astream({
                "context": context,
                "chat_history": chat_history,
                "question": query,
                "dimensions": dimensions_text
            }):
                full_response += token
                yield token
            
            # Step 5: Save to database
            cls._save_message(
                conversation_id=conversation_id,
                content=full_response,
                citations=citations
            )
            
            logger.info(f"ChatRAG: Complete ({len(full_response)} chars)")
            
        except Exception as e:
            logger.exception(f"ChatRAG error: {e}")
            yield f"\n\n[Error: {str(e)}]"
    
    @staticmethod
    def _save_message(conversation_id: str, content: str, citations: List[Dict], mode: str = "rag"):
        """Save the assistant message to the database."""
        db = SessionLocal()
        try:
            msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=content,
                citations_json=json.dumps(citations) if citations else None,
                mode=mode
            )
            db.add(msg)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
        finally:
            db.close()
    
    @classmethod
    async def abstract_stream(
        cls,
        paper_id: str,
        paper_title: str,
        paper_abstract: str,
        message: str,
        conversation_id: str,
        history: Optional[List[Dict]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response using only the paper abstract (no RAG).
        
        Used when paper is not ingested yet. Provides limited but instant responses.
        
        Args:
            paper_id: Paper ID
            paper_title: Paper title
            paper_abstract: Paper abstract text
            message: User's message
            conversation_id: Conversation ID for persistence
            history: Previous conversation messages
            
        Yields:
            First line: JSON metadata with mode='abstract'
            Subsequent: Streamed response tokens
        """
        llm = LLMFactory.get_langchain_llm(streaming=True)
        
        # Simple prompt for abstract-only mode
        ABSTRACT_PROMPT = ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant helping users understand academic papers.
You only have access to the paper's title and abstract - NOT the full paper.

PAPER TITLE: {title}

PAPER ABSTRACT:
{abstract}

RULES:
1. Answer based ONLY on the abstract provided above.
2. Be clear when you cannot answer from the abstract alone.
3. Suggest that the user "add this paper to a project for deeper analysis" if they ask detailed questions.
4. Use markdown formatting for clarity.
5. Be concise but helpful."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}")
        ])
        
        try:
            # Send metadata first - mode='abstract' signals limited mode
            metadata = {
                "conversation_id": conversation_id,
                "citations": [],  # No citations in abstract mode
                "mode": "abstract",  # Critical: frontend uses this to show badge
                "paper_id": paper_id
            }
            yield json.dumps(metadata) + "\n"
            
            # Build and stream response
            chain = ABSTRACT_PROMPT | llm | StrOutputParser()
            chat_history = cls._format_history(history or [], max_turns=3)
            
            full_response = ""
            async for token in chain.astream({
                "title": paper_title,
                "abstract": paper_abstract,
                "chat_history": chat_history,
                "question": message
            }):
                full_response += token
                yield token
            
            # Save to database
            cls._save_message(
                conversation_id=conversation_id,
                content=full_response,
                citations=[],
                mode="abstract"
            )
            
            logger.info(f"ChatRAG (abstract mode): Complete ({len(full_response)} chars)")
            
        except Exception as e:
            logger.exception(f"ChatRAG abstract mode error: {e}")
            yield f"\n\n[Error: {str(e)}]"

