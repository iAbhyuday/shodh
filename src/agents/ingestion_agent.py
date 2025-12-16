import requests
import arxiv
from datetime import datetime, timedelta
from typing import List, Dict, Any

class IngestionAgent:
    def __init__(self):
        self.arxiv_client = arxiv.Client()

    def fetch_arxiv_papers(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch papers from ArXiv based on a query.
        """
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        
        papers = []
        for result in self.arxiv_client.results(search):
            papers.append({
                "source": "arxiv",
                "id": result.entry_id,
                "title": result.title,
                "abstract": result.summary,
                "authors": [a.name for a in result.authors],
                "published_date": result.published.isoformat(),
                "url": result.pdf_url
            })
        return papers

    def fetch_hf_daily_papers(self, date: str = None) -> List[Dict[str, Any]]:
        """
        Fetch papers from HuggingFace Daily Papers.
        Date format: YYYY-MM-DD. Defaults to today.
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"https://huggingface.co/api/daily_papers?date={date}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for item in data:
                # HF API structure might vary, adapting to common fields
                paper_info = item.get("paper", {})
                papers.append({
                    "source": "huggingface",
                    "id": paper_info.get("id"),
                    "title": paper_info.get("title"),
                    "abstract": paper_info.get("summary", "No summary available"), # HF might not ensure summary in listing
                    "authors": [], # HF listing might not have authors
                    "published_date": date,
                    "url": f"https://huggingface.co/papers/{paper_info.get('id')}"
                })
            return papers
        except Exception as e:
            print(f"Error fetching HF papers: {e}")
            return []

    def run(self, topics: List[str]) -> List[Dict[str, Any]]:
        """
        Main execution method to fetch papers for given topics.
        """
        all_papers = []
        
        # Fetch from ArXiv
        for topic in topics:
            print(f"Fetching ArXiv papers for topic: {topic}")
            all_papers.extend(self.fetch_arxiv_papers(topic))
            
        # Fetch from HF (Last 1 day)
        print("Fetching HuggingFace Daily Papers")
        all_papers.extend(self.fetch_hf_daily_papers())
        
        return all_papers
