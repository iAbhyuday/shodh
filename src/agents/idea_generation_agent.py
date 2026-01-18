"""
Idea generation agent for creating research ideas from paper content.
"""
from typing import List, Dict, Any
import logging

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class IdeaGenerationAgent(BaseAgent):
    """Agent that generates research ideas from paper abstracts."""
    
    prompt_file = "idea_generation_prompt.txt"

    def generate_ideas(self, paper: Dict[str, Any]) -> List[str]:
        """
        Generate research ideas from a paper.
        
        Args:
            paper: Dictionary with 'title', 'abstract', and optional 'metrics'
            
        Returns:
            List of idea strings
        """
        if not self.is_configured:
            return ["LLM not configured"]
            
        try:
            metrics_str = str(paper.get("metrics", {}))
            prompt = self.prompt_template.format(
                title=paper.get("title", ""),
                abstract=paper.get("abstract", ""),
                metrics=metrics_str
            )
            
            response = self.llm.complete(prompt)
            result = response.text
            return [line.strip() for line in result.split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return []

