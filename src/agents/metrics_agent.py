from typing import Dict, Any, List
from pathlib import Path
from src.core.config import get_settings
from src.api.schemas import PaperMetrics
from llama_index.core.program import LLMTextCompletionProgram

settings = get_settings()

class MetricsAgent:
    def __init__(self):
        self.llm = self._get_llm()
        
        # Load prompt from external file
        prompt_path = Path(__file__).parent / "prompts" / "metrics_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()

    def _get_llm(self):
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_llm()

    def extract_metrics(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics and structured data from a paper.
        """
        if not self.llm:
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
            print(f"Error extracting metrics for {paper.get('title')}: {e}")
            return {}

    def run(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of papers and enrich them with metrics.
        """
        enriched_papers = []
        for paper in papers:
            metrics = self.extract_metrics(paper)
            paper["metrics"] = metrics
            enriched_papers.append(paper)
        return enriched_papers