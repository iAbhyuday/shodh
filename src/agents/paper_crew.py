"""
Paper Crew module for agentic paper analysis.

This module provides the CrewAI implementation for multi-step reasoning
over research papers.
"""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool

from src.core.config import get_settings
from src.core.llm_factory import LLMFactory
from src.core.retriever import get_retriever

logger = logging.getLogger(__name__)

class PaperSearchTool(BaseTool):
    name: str = "Search Papers"
    description: str = (
        "Search for relevant information across the provided research papers. "
        "Useful for gathering evidence, finding specific details, or exploring topics. "
        "Input should be a specific search query."
    )
    paper_ids: List[str] = Field(default_factory=list)

    def _run(self, query: str) -> str:
        try:
            retriever = get_retriever()
            # Determine top_k based on number of papers to balance context window
            top_k = 8 if len(self.paper_ids) > 1 else 5
            
            # Query the retriever
            results = retriever.query(
                query_text=query,
                paper_id=self.paper_ids if len(self.paper_ids) > 1 else self.paper_ids[0],
                top_k=top_k
            )
            
            if not results:
                return "No relevant information found in the papers."
            
            # Format results
            formatted_results = []
            for i, res in enumerate(results):
                # Only include results with decent score
                if res.get('score', 0) < 0.3:
                    continue
                    
                meta = res.get('metadata', {})
                paper_id = meta.get('paper_id', 'unknown')
                section = meta.get('section', 'excerpt')
                content = res.get('content', '').strip()
                
                figures = meta.get('figures', '')
                fig_note = f" (References: {figures})" if figures and figures.strip() else ""
                
                formatted_results.append(
                    f"Result {i+1} [Paper: {paper_id}, Section: {section}]{fig_note}:\n{content}"
                )
            
            if not formatted_results:
                return "Found some results but they were below relevance threshold. Try rephrasing."
                
            return "\n\n".join(formatted_results)
            
        except Exception as e:
            logger.error(f"Error in PaperSearchTool: {e}")
            return f"Error occurred during search: {str(e)}"

def run_paper_crew(
    paper_ids: str | list[str],
    paper_title: str,
    user_query: str,
    small_model: Optional[str] = None,
    large_model: Optional[str] = None,
    chat_history: Optional[str] = None,
    available_figures: Optional[List[str]] = None,
    enable_recovery: bool = False,
    enable_thinking: bool = False
) -> Dict[str, Any]:
    """
    Run the CrewAI pipeline for paper analysis.
    
    Args:
        paper_ids: Paper identifier(s)
        paper_title: Title of the paper or project context
        user_query: User's question
        small_model: Name of model for faster tasks (optional)
        large_model: Name of model for reasoning tasks (optional)
        chat_history: Previous conversation context
        available_figures: List of figure IDs (unused in text agent)
        enable_recovery: Enable automatic recovery (unused)
        enable_thinking: Enable extended thinking (unused)
    
    Returns:
        Result dictionary with status and answer
    """
    settings = get_settings()
    
    # Normalize paper_ids
    if isinstance(paper_ids, str):
        paper_ids = [paper_ids]
    
    try:
        # 1. Setup Tools
        search_tool = PaperSearchTool(paper_ids=paper_ids)
        
        # 2. Setup LLM
        # Use configured agent model or fallback to main LLM
        agent_model = large_model or settings.CREW_LLM_LARGE or settings.OPENAI_MODEL
        llm = LLMFactory.get_crew_llm(agent_model)
        
        # 3. Create Agent
        researcher = Agent(
            role='Senior Research Assistant',
            goal=f'Provide accurate, evidence-based answers about: {paper_title}',
            backstory=(
                "You are an expert academic researcher assistant. "
                "Your goal is to answer the user's questions by synthesizing information "
                "from the provided research papers. "
                "You must verify your claims by searching the papers."
            ),
            tools=[search_tool],
            llm=llm,
            verbose=True,
            allow_delegation=False
        )
        
        # 4. Create Task
        # Include chat history in the task description if available
        task_description = f"User Question: {user_query}\n\n"
        
        if chat_history:
            task_description += f"Context/History:\n{chat_history}\n\n"
            
        task_description += (
            "Steps:\n"
            "1. Search the papers to find relevant information about the user's question.\n"
            "2. If the initial search is insufficient, perform ONE follow-up search with different keywords.\n"
            "3. Synthesize the findings into a clear, direct answer.\n"
            "4. If the papers do not contain the answer, explicitly state that.\n"
            "5. Do not make up information.\n"
            "6. FORMATTING RULES:\n"
            "   - Math: MUST use \\( ... \\) for inline and \\[ ... \\] for block equations. NEVER use bare LaTeX.\n"
            "   - Figures: Reference figures mentioned in context as [Figure X].\n"
            "   - Citations: Always cite using [1], [2], etc. matching the Result numbers."
        )

        answer_task = Task(
            description=task_description,
            expected_output=(
                "A comprehensive answer to the user's question, citing specific findings from the text. "
                "The tone should be professional and academic."
            ),
            agent=researcher
        )
        
        # 5. Run Crew
        crew = Crew(
            agents=[researcher],
            tasks=[answer_task],
            process=Process.sequential,
            verbose=True
        )
        
        result = crew.kickoff()
        
        # CrewAI returns a CrewOutput object. The raw string is in .raw
        # If it returns a string directly (older versions), handle that.
        final_answer = getattr(result, "raw", str(result))
        
        return {
            'status': 'success',
            'answer': final_answer,
            'model_info': {'model': agent_model}
        }
        
    except Exception as e:
        logger.exception("Error running paper crew")
        return {
            'status': 'error',
            'answer': f"I encountered an error while analyzing the papers: {str(e)}",
            'error': str(e)
        }
