"""
Visualization agent for generating mindmaps from paper content.
"""
from typing import Dict, Any
import logging

from src.agents.base_agent import BaseAgent
from src.api.schemas import MindMapNode
from llama_index.core.program import LLMTextCompletionProgram

logger = logging.getLogger(__name__)


class VisualizationAgent(BaseAgent):
    """Agent that generates mindmap visualizations from papers."""
    
    prompt_file = "visualization_prompt.txt"

    def generate_mindmap(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a mindmap visualization from a paper.
        
        Args:
            paper: Dictionary with 'title' and 'abstract'
            
        Returns:
            Mindmap dictionary with id, label, and children
        """
        if not self.is_configured:
            return {"id": "root", "label": "LLM Not Configured", "children": []}

        try:
            program = LLMTextCompletionProgram.from_defaults(
                output_cls=MindMapNode,
                prompt_template_str=self.prompt_template,
                llm=self.llm,
                verbose=True
            )
            
            result: MindMapNode = program(
                title=paper.get("title", ""), 
                abstract=paper.get("abstract", "")
            )
            
            return result.dict()
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            return {"id": "root", "label": "Error Generating Map", "children": []}

