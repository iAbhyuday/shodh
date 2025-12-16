from typing import Dict, Any, List
from pathlib import Path
from src.core.config import get_settings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

settings = get_settings()

class MetricsAgent:
    def __init__(self):
        self.llm = self._get_llm()
        self.parser = JsonOutputParser()
        
        # Load prompt from external file
        prompt_path = Path(__file__).parent / "prompts" / "metrics_prompt.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_template = f.read().strip()
            
        self.prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["title", "abstract"],
        )

    def _get_llm(self):
        if settings.OPENAI_API_KEY:
            return ChatOpenAI(api_key=settings.OPENAI_API_KEY, model="gpt-4o")
        elif settings.GEMINI_API_KEY:
            return ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model="gemini-1.5-pro")
        elif settings.OLLAMA_BASE_URL:
            return ChatOllama(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        else:
            print("Warning: No LLM API key found. Metrics Agent will not work correctly.")
            return None

    def extract_metrics(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics and structured data from a paper.
        """
        if not self.llm:
            return {"error": "No LLM configured"}
            
        try:
            chain = self.prompt | self.llm | self.parser
            result = chain.invoke({"title": paper.get("title"), "abstract": paper.get("abstract")})
            return result
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