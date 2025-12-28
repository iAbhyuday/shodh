"""
LlamaIndex-based ingestion pipeline for research papers.
Uses the official IngestionPipeline with declarative transformations.
"""
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .docling_parser import PaperDocument

logger = logging.getLogger(__name__)


class PaperIngestionPipeline:
    """
    Paper ingestion pipeline using LlamaIndex's IngestionPipeline.
    
    Flow: PaperDocument → LlamaIndex Documents → Transformations → ChromaDB
    """
    
    def __init__(
        self,
        embedding_model: str = "nomic-embed-text:v1.5",
        ollama_base_url: str = "http://localhost:11434",
        collection_name: str = "shodh_papers",
        chunk_size: int = 1024,  # Increased for markdown chunks
        chunk_overlap: int = 100,  # Increased overlap
        chroma_persist_path: str = "./chroma_db"
    ):
        self.embedding_model = embedding_model
        self.ollama_base_url = ollama_base_url
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chroma_persist_path = chroma_persist_path
        
        self._pipeline = None
        self._vector_store = None
        
    def _get_vector_store(self):
        """Get or create ChromaDB vector store."""
        if self._vector_store is None:
            import chromadb
            from llama_index.vector_stores.chroma import ChromaVectorStore
            
            chroma_client = chromadb.PersistentClient(path=self.chroma_persist_path)
            chroma_collection = chroma_client.get_or_create_collection(
                name=self.collection_name
            )
            self._vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        return self._vector_store
    
    def _get_embed_model(self):
        """Get Ollama embedding model."""
        from llama_index.embeddings.ollama import OllamaEmbedding
        return OllamaEmbedding(
            model_name=self.embedding_model,
            base_url=self.ollama_base_url
        )
    
    def _build_pipeline(self):
        """Build LlamaIndex IngestionPipeline with transformations."""
        from llama_index.core.ingestion import IngestionPipeline
        from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
        
        return IngestionPipeline(
            transformations=[
                # Step 1: Split by Markdown structure
                MarkdownNodeParser(),
                # Step 2: Split large chunks further if needed
                SentenceSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap
                ),
                # Step 3: Generate embeddings
                self._get_embed_model(),
            ],
            vector_store=self._get_vector_store(),
        )
    
    def _parsed_doc_to_documents(self, parsed_doc: PaperDocument) -> List:
        """Convert PaperDocument to LlamaIndex Documents."""
        from llama_index.core import Document
        
        documents = []
        
        # Main document with full markdown content
        if parsed_doc.markdown_content != "":
            documents.append(Document(
                text=parsed_doc.markdown_content,
                metadata={
                    "paper_id": parsed_doc.paper_id,
                    "title": parsed_doc.title,
                    "authors": parsed_doc.authors,
                    "item_type": "full_text"
                },
                id_=f"{parsed_doc.paper_id}_full"
            ))
        else:
            # Fallback if markdown is empty (shouldn't happen with new parser)
            logger.warning(f"No markdown content for {parsed_doc.paper_id}, using legacy section fallback")
            if parsed_doc.abstract:
                documents.append(Document(
                    text=parsed_doc.abstract,
                    metadata={"paper_id": parsed_doc.paper_id, "section": "abstract"},
                    id_=f"{parsed_doc.paper_id}_abstract"
                ))
            for _, section in enumerate(parsed_doc.sections):
                documents.append(Document(
                    text=section.content,
                    metadata={"paper_id": parsed_doc.paper_id, "section": section.title},
                    id_=f"{parsed_doc.paper_id}_section_{section.section}" if section.section else ""
                ))

        # Add figure captions as helper documents? 
        # Ideally figures should be embedded in markdown, but captions are useful.
        # Let's keep separate figure index if we want, but for now stick to one main doc for continuity.
        # If we add them, they should be clearly marked.
        # For this iteration, let's trust the MarkdownNodeParser to handle the text flow.
        
        logger.info(f"Created {len(documents)} source documents for {parsed_doc.paper_id}")
        return documents
    
    def ingest(self, parsed_doc: PaperDocument) -> int:
        """
        Ingest a parsed document using LlamaIndex IngestionPipeline.
        
        Args:
            parsed_doc: Parsed document from DoclingParser
            
        Returns:
            Number of nodes created
        """
        # Convert to LlamaIndex documents
        documents = self._parsed_doc_to_documents(parsed_doc)
        
        if not documents:
            logger.warning(f"No documents created for {parsed_doc.paper_id}")
            return 0
        
        # Build and run the pipeline
        pipeline = self._build_pipeline()
        
        # Run pipeline - automatically stores in vector store
        nodes = pipeline.run(documents=documents, show_progress=True)
        
        logger.info(f"Ingested {len(nodes)} nodes for {parsed_doc.paper_id}")
        return len(nodes)
    
    def query(
        self,
        query_text: str,
        paper_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Query the vector store for relevant chunks.
        
        Args:
            query_text: Query string
            paper_id: Optional filter by paper
            top_k: Number of results
            
        Returns:
            List of matching chunks with scores
        """
        from llama_index.core import VectorStoreIndex
        
        # Create index from vector store
        index = VectorStoreIndex.from_vector_store(
            self._get_vector_store(),
            embed_model=self._get_embed_model()
        )
        
        # Build retriever with filters
        if paper_id:
            from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
            filters = MetadataFilters(filters=[
                MetadataFilter(key="paper_id", value=paper_id)
            ])
            retriever = index.as_retriever(
                similarity_top_k=top_k,
                filters=filters
            )
        else:
            retriever = index.as_retriever(similarity_top_k=top_k)
        
        # Query
        nodes = retriever.retrieve(query_text)
        
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
            similarity_top_k=5,
            filters=filters
        )

        # 4. Configure Ollama LLM for response synthesis
        from llama_index.llms.ollama import Ollama
        llm = Ollama(
            model="qwen2.5vl:7b",
            base_url=self.ollama_base_url,
            temperature=0.7,
            request_timeout=120.0
        )

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


# Alias for backward compatibility
IngestionPipeline = PaperIngestionPipeline


# Convenience function for background ingestion
async def ingest_paper_async(
    paper_id: str,
    pdf_path: Path,
    update_status_callback=None
):
    """
    Async wrapper for paper ingestion.
    Used by background tasks in FastAPI.
    """
    from .docling_parser import DoclingParser
    
    try:
        if update_status_callback:
            await update_status_callback(paper_id, "parsing")
        
        # Parse PDF
        parser = DoclingParser()
        parsed_doc = parser.parse(pdf_path, paper_id)
        
        if update_status_callback:
            await update_status_callback(paper_id, "embedding")
        
        # Ingest using LlamaIndex pipeline
        pipeline = PaperIngestionPipeline()
        chunk_count = pipeline.ingest(parsed_doc)
        
        if update_status_callback:
            await update_status_callback(paper_id, "completed", chunk_count)
        
        return chunk_count
        
    except Exception as e:
        logger.error(f"Ingestion failed for {paper_id}: {e}")
        if update_status_callback:
            await update_status_callback(paper_id, "failed")
        raise
