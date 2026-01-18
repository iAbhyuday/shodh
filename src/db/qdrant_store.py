"""
Qdrant vector store client and utilities.
Provides hybrid search with dense + sparse vectors.
"""
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, 
    Distance, 
    PointStruct,
    SparseVectorParams,
    SparseIndexParams,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    SearchRequest,
    NamedVector,
    NamedSparseVector,
    SparseVector,
    Prefetch,
    Query,
    FusionQuery,
    Fusion,
)
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

# Embedding dimensions (nomic-embed-text)
DENSE_VECTOR_SIZE = 768


def get_qdrant_client(settings=None):
    """Get Qdrant client based on configuration."""
    if settings is None:
        from src.core.config import get_settings
        settings = get_settings()
    
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )


def ensure_collection(client: QdrantClient, collection_name: str, vector_size: int = DENSE_VECTOR_SIZE):
    """Create collection if it doesn't exist."""
    try:
        client.get_collection(collection_name)
        logger.info(f"Collection '{collection_name}' exists")
    except (UnexpectedResponse, Exception):
        logger.info(f"Creating collection '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False)
                )
            }
        )
        logger.info(f"Collection '{collection_name}' created")


def text_to_sparse_vector(text: str) -> Dict[str, List]:
    """
    Convert text to sparse vector for BM25-like matching.
    Uses term frequency as values.
    """
    import re
    from collections import Counter
    
    # Simple tokenization
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    tokens = text.split()
    
    # Count term frequencies
    tf = Counter(tokens)
    
    # Convert to sparse vector format
    # Use hash of token as index
    indices = []
    values = []
    for token, count in tf.items():
        idx = abs(hash(token)) % (2**31)  # Positive 32-bit hash
        indices.append(idx)
        values.append(float(count))
    
    return {"indices": indices, "values": values}


class QdrantVectorStore:
    """
    Qdrant-based vector store with hybrid search support.
    Replaces ChromaDB + BM25Index with unified solution.
    """
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        from src.core.config import get_settings
        settings = get_settings()
        
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        
        self._client = None
        self._embed_model = None
    
    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(host=self.host, port=self.port)
            ensure_collection(self._client, self.collection_name)
        return self._client
    
    def _get_embed_model(self):
        """Get embedding model via Factory."""
        if self._embed_model is None:
            from src.core.llm_factory import LLMFactory
            self._embed_model = LLMFactory.get_llama_index_embedding()
        return self._embed_model
    
    def add_documents(
        self,
        documents: List[Dict],
        paper_id: str
    ) -> int:
        """
        Add documents to Qdrant with both dense and sparse vectors.
        
        Args:
            documents: List of {text, metadata} dicts
            paper_id: Paper ID for metadata
            
        Returns:
            Number of documents added
        """
        if not documents:
            return 0
        
        embed_model = self._get_embed_model()
        points = []
        
        for i, doc in enumerate(documents):
            text = doc.get('text', doc.get('content', ''))
            metadata = doc.get('metadata', {})
            metadata['paper_id'] = paper_id
            
            # Generate dense embedding
            dense_vector = embed_model.get_text_embedding(text)
            
            # Generate sparse vector for keyword matching
            sparse = text_to_sparse_vector(text)
            
            # Create unique ID
            doc_id = abs(hash(f"{paper_id}_{i}_{text[:100]}")) % (2**63)
            
            points.append(PointStruct(
                id=doc_id,
                vector={
                    "dense": dense_vector,
                    "sparse": SparseVector(
                        indices=sparse["indices"],
                        values=sparse["values"]
                    )
                },
                payload={
                    "content": text,
                    **metadata
                }
            ))
        
        # Batch upsert
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Added {len(points)} documents to Qdrant for paper {paper_id}")
        return len(points)
    
    def hybrid_search(
        self,
        query: str,
        paper_id: Optional[Any] = None,
        section: Optional[str] = None,
        top_k: int = 5,
        alpha: float = 0.5
    ) -> List[Dict]:
        """
        Hybrid search using RRF fusion of dense + sparse.
        
        Args:
            query: Search query
            paper_id: Optional paper ID filter (string or list)
            section: Optional section filter (e.g., "abstract", "methods")
            top_k: Number of results
            alpha: Not used (Qdrant uses RRF internally)
            
        Returns:
            List of {content, score, metadata} dicts
        """
        embed_model = self._get_embed_model()
        
        # Generate query vectors
        dense_query = embed_model.get_text_embedding(query)
        sparse_query = text_to_sparse_vector(query)
        
        # Build filter conditions
        filter_conditions = []
        
        if paper_id:
            if isinstance(paper_id, list):
                filter_conditions.append(FieldCondition(
                    key="paper_id",
                    match=MatchAny(any=paper_id)
                ))
            else:
                filter_conditions.append(FieldCondition(
                    key="paper_id",
                    match=MatchValue(value=paper_id)
                ))
        
        if section:
            filter_conditions.append(FieldCondition(
                key="section",
                match=MatchValue(value=section)
            ))
        
        query_filter = Filter(must=filter_conditions) if filter_conditions else None
        
        # Hybrid search with RRF fusion
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                Prefetch(
                    query=dense_query,
                    using="dense",
                    limit=top_k * 2
                ),
                Prefetch(
                    query=SparseVector(
                        indices=sparse_query["indices"],
                        values=sparse_query["values"]
                    ),
                    using="sparse",
                    limit=top_k * 2
                )
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=query_filter,
            limit=top_k,
            with_payload=True
        )
        
        # Convert to standard format
        output = []
        for point in results.points:
            payload = point.payload or {}
            output.append({
                "content": payload.get("content", ""),
                "score": point.score,
                "metadata": {k: v for k, v in payload.items() if k != "content"}
            })
        
        return output
    
    async def ahybrid_search(
        self,
        query: str,
        paper_id: Optional[Any] = None,
        section: Optional[str] = None,
        top_k: int = 5,
        alpha: float = 0.5
    ) -> List[Dict]:
        """Async version - runs sync in threadpool."""
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(
            self.hybrid_search, query, paper_id, section, top_k, alpha
        )
    
    def get_collection_info(self) -> Dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "points_count": info.points_count,
            "status": info.status
        }
