"""
Metrics agent for extracting structured data from papers.
"""
from typing import Dict, Any, List
import logging

from src.agents.base_agent import BaseAgent
from src.api.schemas import PaperMetrics
from llama_index.core.program import LLMTextCompletionProgram

logger = logging.getLogger(__name__)


class MetricsAgent(BaseAgent):
    """Agent that extracts metrics and structured data from papers."""
    
    prompt_file = "metrics_prompt.txt"

    def extract_metrics(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics and structured data from a paper.
        
        Args:
            paper: Dictionary with 'title' and 'abstract'
            
        Returns:
            Dictionary of extracted metrics
        """
        if not self.is_configured:
            return {"error": "No LLM configured"}
            
        try:
            program = LLMTextCompletionProgram.from_defaults(
                output_cls=PaperMetrics,
                prompt_template_str=self.prompt_template,
                llm=self.llm,
                verbose=True
            )
            
            result: PaperMetrics = program(
                title=paper.get("title", ""), 
                abstract=paper.get("abstract", "")
            )
            return result.dict()
        except Exception as e:
            logger.error(f"Error extracting metrics for {paper.get('title')}: {e}")
            return {}

    def run(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of papers and enrich them with metrics.
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            List of papers enriched with metrics
        """
        enriched_papers = []
        for paper in papers:
            metrics = self.extract_metrics(paper)
            paper["metrics"] = metrics
            enriched_papers.append(paper)
        return enriched_papers