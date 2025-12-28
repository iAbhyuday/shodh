"""
Custom RAG Tool for CrewAI that wraps the paper ingestion pipeline.
Allows agents to search specific papers using semantic retrieval.
"""
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class PaperSearchInput(BaseModel):
    """Input schema for PaperRAGTool."""
    query: str = Field(..., description="The search query to find relevant information from the paper.")


class PaperRAGTool(BaseTool):
    """Tool to search a specific paper for relevant information."""
    name: str = "paper_search"
    description: str = "Search the research paper for specific information. Use this to find facts, data, methods, or results from the paper."
    args_schema: Type[BaseModel] = PaperSearchInput
    
    # Paper-specific config (set at runtime)
    paper_id: str = ""
    
    def __init__(self, paper_id: str, **kwargs):
        super().__init__(**kwargs)
        self.paper_id = paper_id
    
    def _run(self, query: str) -> str:
        """
        Execute the paper search.
        Returns formatted context chunks from the paper.
        """
        from src.ingestion.pipeline import IngestionPipeline
        
        pipeline = IngestionPipeline()
        results = pipeline.query(
            query_text=query,
            paper_id=self.paper_id,
            top_k=5
        )
        
        if not results:
            return "No relevant information found in the paper for this query."
        
        # Format results as context
        context_parts = []
        for chunk in results:
            section = chunk['metadata'].get('section_type', 'unknown').upper()
            section_title = chunk['metadata'].get('section_title', '')
            page = chunk['metadata'].get('page_number', '')
            content = chunk['content']
            
            header = f"[{section}]"
            if section_title:
                header += f" {section_title}"
            if page:
                header += f" (Page {page})"
            
            context_parts.append(f"{header}:\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
