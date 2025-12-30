import logging
from typing import List, Optional, Any, Dict, Union
from src.core.config import get_settings

logger = logging.getLogger(__name__)

class PaperRetriever:
    """
    Paper retrieval logic using LlamaIndex.
    Decoupled from IngestionPipeline.
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None,
        collection_name: Optional[str] = None,
        chroma_persist_path: Optional[str] = None,
    ):
        settings = get_settings()
        # We allow None here so that LLMFactory can pick provider-specific defaults
        self.embedding_model = embedding_model 
        self.collection_name = collection_name or settings.COLLECTION_NAME
        self.chroma_persist_path = chroma_persist_path or \
            settings.VECTOR_DB_PATH
        
        self._vector_store = None
        
    def _get_vector_store(self):
        """Get or create ChromaDB vector store."""
        if self._vector_store is None:
            import chromadb
            from llama_index.vector_stores.chroma import ChromaVectorStore
            from src.db.vector_store import get_chroma_client
            from src.core.config import get_settings
            
            chroma_client = get_chroma_client(get_settings())
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            self._vector_store = ChromaVectorStore(
                chroma_collection=chroma_collection)
        
        return self._vector_store
    
    def _get_embed_model(self):
        """Get embedding model via Factory."""
        from src.core.llm_factory import LLMFactory
        return LLMFactory.get_llama_index_embedding(model_name=self.embedding_model)

    def query(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Query the vector store for relevant chunks.
        
        Args:
            query_text: Query string
            paper_id: Optional string (single paper) or list of strings (multiple papers)
            top_k: Number of results
        """
        from llama_index.core import VectorStoreIndex
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
        
        index = VectorStoreIndex.from_vector_store(
            self._get_vector_store(),
            embed_model=self._get_embed_model()
        )
        
        filters = None
        if paper_id:
            if isinstance(paper_id, list):
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id, operator="in")
                ])
            else:
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id)
                ])
        
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=filters
        )
        
        nodes = retriever.retrieve(query_text)
        results = []
        for node in nodes:
            results.append({
                "content": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return results

    async def aquery(
        self,
        query_text: str,
        paper_id: Optional[Any] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Async query the vector store for relevant chunks.
        """
        from llama_index.core import VectorStoreIndex
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
        
        index = VectorStoreIndex.from_vector_store(
            self._get_vector_store(),
            embed_model=self._get_embed_model()
        )
        
        filters = None
        if paper_id:
            if isinstance(paper_id, list):
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id, operator="in")
                ])
            else:
                filters = MetadataFilters(filters=[
                    MetadataFilter(key="paper_id", value=paper_id)
                ])
        
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=filters
        )
        
        nodes = await retriever.aretrieve(query_text)
        results = []
        for node in nodes:
            results.append({
                "content": node.text,
                "score": node.score,
                "metadata": node.metadata
            })
        return results

    def get_query_engine(self, paper_id: str):
        """
        Get a LlamaIndex QueryEngine for a specific paper.
        Used by the ReAct Agent Tools.
        """
        from llama_index.core import VectorStoreIndex, get_response_synthesizer
        from llama_index.core.retrievers import VectorIndexRetriever
        from llama_index.core.query_engine import RetrieverQueryEngine
        from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

        # 1. Get Filters
        filters = MetadataFilters(filters=[
            MetadataFilter(key="paper_id", value=paper_id)
        ])

        # 2. Build Index (from existing store)
        index = VectorStoreIndex.from_vector_store(
            self._get_vector_store(),
            embed_model=self._get_embed_model()
        )

        # 3. Configure Retriever (Top-5 chunks)
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=10,
            filters=filters
        )

        # 4. Configure LLM for response synthesis via Factory
        from src.core.llm_factory import LLMFactory
        # Pass None as model_name to let Factory use provider-specific default
        llm = LLMFactory.get_llama_index_llm(model_name=None)

        # 5. Configure Response Synthesizer with Ollama
        response_synthesizer = get_response_synthesizer(
            response_mode="compact",
            llm=llm
        )

        # 6. Build Query Engine
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
        )

        return query_engine
