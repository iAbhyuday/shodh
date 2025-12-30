from typing import List, Dict, Any
from pathlib import Path
from src.core.config import get_settings

settings = get_settings()

class IdeaGenerationAgent:
    def __init__(self):
        self.llm = self._get_llm()
        
        # Load prompt from external file
        prompt_path = Path(__file__).parent / "prompts" / "idea_generation_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()
            
    def _get_llm(self):
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_llm()

    def generate_ideas(self, paper: Dict[str, Any]) -> List[str]:
        if not self.llm:
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
            print(f"Error generating ideas: {e}")
            return []
