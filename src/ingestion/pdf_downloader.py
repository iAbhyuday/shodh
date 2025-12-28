"""
PDF Downloader for research papers from arXiv.
Downloads PDFs to local storage for ingestion.
"""
import os
import re
import requests
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Default storage location
PDF_STORAGE_PATH = Path("/Users/abhyuday/Downloads/shodh_papers")


class PDFDownloader:
    """Downloads PDFs from arXiv and other sources."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or PDF_STORAGE_PATH
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def _extract_arxiv_id(self, paper_id: str) -> str:
        """Extract clean arXiv ID from various formats."""
        # Handle formats like "2512.13672", "arxiv:2512.13672", "2512.13672v1"
        match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', paper_id)
        if match:
            return match.group(1)
        return paper_id
    
    def _get_arxiv_pdf_url(self, arxiv_id: str) -> str:
        """Get PDF URL from arXiv ID."""
        clean_id = self._extract_arxiv_id(arxiv_id)
        return f"https://arxiv.org/pdf/{clean_id}.pdf"
    
    def get_pdf_path(self, paper_id: str) -> Path:
        """Get expected local path for a paper's PDF."""
        clean_id = self._extract_arxiv_id(paper_id)
        return self.storage_path / f"{clean_id}.pdf"
    
    def is_downloaded(self, paper_id: str) -> bool:
        """Check if PDF is already downloaded."""
        return self.get_pdf_path(paper_id).exists()
    
    def download(self, paper_id: str, source_url: Optional[str] = None) -> Path:
        """
        Download PDF for a paper.
        
        Args:
            paper_id: Paper identifier (e.g., arXiv ID)
            source_url: Optional direct PDF URL (if not arXiv)
            
        Returns:
            Path to downloaded PDF
            
        Raises:
            RuntimeError: If download fails
        """
        pdf_path = self.get_pdf_path(paper_id)
        
        # Skip if already downloaded
        if pdf_path.exists():
            logger.info(f"PDF already exists: {pdf_path}")
            return pdf_path
        
        # Determine download URL
        if source_url:
            url = source_url
        else:
            url = self._get_arxiv_pdf_url(paper_id)
        
        logger.info(f"Downloading PDF from {url}")
        
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verify it's actually a PDF
            content_type = response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower() and not url.endswith('.pdf'):
                raise RuntimeError(f"Response is not a PDF: {content_type}")
            
            # Write to file
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded PDF to {pdf_path}")
            return pdf_path
            
        except requests.RequestException as e:
            logger.error(f"Failed to download PDF: {e}")
            raise RuntimeError(f"PDF download failed: {e}")
    
    def delete(self, paper_id: str) -> bool:
        """Delete a downloaded PDF."""
        pdf_path = self.get_pdf_path(paper_id)
        if pdf_path.exists():
            pdf_path.unlink()
            logger.info(f"Deleted PDF: {pdf_path}")
            return True
        return False
