from typing import Dict, Any
from pathlib import Path
from src.core.config import get_settings
from src.api.schemas import MindMapNode
from llama_index.core.program import LLMTextCompletionProgram

settings = get_settings()

class VisualizationAgent:
    def __init__(self):
        self.llm = self._get_llm()
        
        # Load prompt from external file
        prompt_path = Path(__file__).parent / "prompts" / "visualization_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read().strip()

    def _get_llm(self):
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_llm()

    def generate_mindmap(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        if not self.llm:
            return {"id": "root", "label": "LLM Not Configured", "children": []}

        try:
            program = LLMTextCompletionProgram.from_defaults(
                output_cls=MindMapNode,
                prompt_template_str=self.prompt_template,
                llm=self.llm,
                verbose=True
            )
            
            # The prompt expects {title} and {abstract}
            result: MindMapNode = program(
                title=paper.get("title", ""), 
                abstract=paper.get("abstract", "")
            )
            
            return result.dict()
        except Exception as e:
            print(f"Error generating visualization: {e}")
            return {"id": "root", "label": "Error Generating Map", "children": []}
