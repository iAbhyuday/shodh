"""
ArXiv service for fetching paper metadata.

Consolidates all ArXiv API calls into a single service to avoid code duplication.
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"


@dataclass
class PaperMetadata:
    """Paper metadata from ArXiv."""
    paper_id: str
    title: str
    summary: str
    authors: str
    published_date: str
    url: str


class ArxivService:
    """
    Service for fetching paper metadata from ArXiv.
    
    Usage:
        paper = ArxivService.fetch_paper("2401.12345")
        papers = ArxivService.search("transformer attention", max_results=10)
    """
    
    @staticmethod
    def fetch_paper(paper_id: str) -> Optional[PaperMetadata]:
        """
        Fetch metadata for a single paper by ArXiv ID.
        
        Args:
            paper_id: ArXiv paper ID (e.g., "2401.12345")
            
        Returns:
            PaperMetadata if found, None otherwise
        """
        try:
            url = f"{ARXIV_API_URL}?id_list={paper_id}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.text)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entry = root.find('atom:entry', namespace)
            
            if entry is None:
                logger.warning(f"Paper {paper_id} not found on ArXiv")
                return None
            
            # Check for error response
            id_elem = entry.find('atom:id', namespace)
            if id_elem is not None and 'error' in id_elem.text.lower():
                logger.warning(f"ArXiv returned error for {paper_id}")
                return None
            
            title = entry.find('atom:title', namespace)
            summary = entry.find('atom:summary', namespace)
            published = entry.find('atom:published', namespace)
            authors = entry.findall('atom:author', namespace)
            
            return PaperMetadata(
                paper_id=paper_id,
                title=title.text.strip() if title is not None else paper_id,
                summary=summary.text.strip() if summary is not None else "",
                authors=", ".join([
                    a.find('atom:name', namespace).text 
                    for a in authors 
                    if a.find('atom:name', namespace) is not None
                ]),
                published_date=published.text[:10] if published is not None else "",
                url=f"https://arxiv.org/abs/{paper_id}"
            )
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch paper {paper_id} from ArXiv: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Failed to parse ArXiv response for {paper_id}: {e}")
            return None
    
    @staticmethod
    def search(query: str, max_results: int = 10) -> List[PaperMetadata]:
        """
        Search ArXiv for papers matching a query.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            List of PaperMetadata objects
        """
        try:
            import arxiv
            
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            papers = []
            for result in client.results(search):
                # Extract paper_id from entry_id URL
                paper_id = result.entry_id.split("/")[-1]
                
                papers.append(PaperMetadata(
                    paper_id=paper_id,
                    title=result.title,
                    summary=result.summary,
                    authors=", ".join([a.name for a in result.authors]),
                    published_date=result.published.strftime("%Y-%m-%d") if result.published else "",
                    url=result.pdf_url or f"https://arxiv.org/abs/{paper_id}"
                ))
            
            return papers
            
        except ImportError:
            logger.error("arxiv package not installed. Run: pip install arxiv")
            return []
        except Exception as e:
            logger.error(f"Failed to search ArXiv for '{query}': {e}")
            return []
