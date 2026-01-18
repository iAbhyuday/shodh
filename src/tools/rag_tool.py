from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from src.core.retriever import get_retriever


class PaperSearchInput(BaseModel):
    """Input schema for PaperRAGTool."""
    query: str = Field(..., description="""The search query to find
                       relevant information from the paper.""")
    section: Optional[str] = Field(
        None, 
        description="""Optional section filter: 'abstract', 'introduction', 
                      'methods', 'results', 'discussion', 'references'"""
    )


class PaperRAGTool(BaseTool):
    """Tool to search a specific paper for relevant information."""
    name: str = "paper_search"
    description: str = """Search the research paper for specific information.
      Use this to find facts, data, methods, or results from the paper.
      You can optionally filter by section (abstract, methods, results, etc.)."""
    args_schema: Type[BaseModel] = PaperSearchInput

    # Paper-specific config (set at runtime)
    paper_ids: list[str] = []

    def __init__(self, paper_ids: str | list[str], **kwargs):
        super().__init__(**kwargs)
        if isinstance(paper_ids, str):
            self.paper_ids = [paper_ids]
        else:
            self.paper_ids = paper_ids

    def _run(self, query: str, section: Optional[str] = None) -> str:
        """
        Execute the search across provided papers.
        
        Args:
            query: Search query
            section: Optional section filter (e.g., "abstract", "methods")
            
        Returns:
            Formatted context chunks from the collection of papers.
        """
        retriever = get_retriever()
        results = retriever.query(
            query_text=query,
            paper_id=self.paper_ids,
            section=section,
            top_k=8 if len(self.paper_ids) > 1 else 5
        )
        if not results:
            return "No relevant information found in the paper for this query."
        
        # Format results as context
        context_parts = []
        for chunk in results:
            metadata = chunk['metadata']
            paper_id = metadata.get('paper_id', 'Unknown Paper')
            section_title = metadata.get('section', 'General')
            figures = metadata.get('figures', 'None')
            content = chunk['content']
            
            # Structured Markdown Block
            formatted_chunk = (
                f"### Source: {paper_id}\n"
                f"**Section:** {section_title}\n"
                f"**Relevant Figures:** {figures}\n"
                f"\n{content}"
            )
            context_parts.append(formatted_chunk)
            
        return "\n\n---\n\n".join(context_parts)

