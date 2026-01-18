import logging
from typing import List, Optional, Any, Dict, Union
from src.core.config import get_settings

logger = logging.getLogger(__name__)


def get_retriever():
    """Factory function to get the retriever."""
    return QdrantRetriever()


class QdrantRetriever:
    """
    Paper retrieval using Qdrant with native hybrid search.
    """
    
    def __init__(self):
        from src.db.qdrant_store import QdrantVectorStore
        self._store = QdrantVectorStore()
    
    def query(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        section: Optional[str] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Query using Qdrant hybrid search.
        
        Args:
            query_text: Search query
            paper_id: Optional paper ID filter (string or list)
            section: Optional section filter (e.g., "abstract", "methods")
            top_k: Number of results
        """
        return self._store.hybrid_search(
            query=query_text,
            paper_id=paper_id,
            section=section,
            top_k=top_k
        )
    
    async def aquery(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        section: Optional[str] = None,
        top_k: int = 5
    ) -> List[dict]:
        """Async query using Qdrant hybrid search."""
        return await self._store.ahybrid_search(
            query=query_text,
            paper_id=paper_id,
            section=section,
            top_k=top_k
        )

