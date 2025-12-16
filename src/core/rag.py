from typing import List, Dict, Any
from src.db.vector_store import vector_store

class RAGPipeline:
    def __init__(self):
        self.vector_store = vector_store

    def ingest_papers(self, papers: List[Dict[str, Any]]):
        """
        Ingest a list of papers into the Vector DB.
        """
        if not papers:
            return
            
        documents = []
        metadatas = []
        ids = []

        for paper in papers:
            # Create a rich text representation for embedding
            content = f"Title: {paper.get('title')}\nAbstract: {paper.get('abstract')}\nMetrics: {paper.get('metrics', {})}"
            documents.append(content)
            
            # Store metadata
            meta = {
                "source": paper.get("source", "unknown"),
                "title": paper.get("title", "unknown"),
                "url": paper.get("url", ""),
                "published_date": paper.get("published_date", "")
            }
            metadatas.append(meta)
            ids.append(str(paper.get("id"))) # Ensure ID is string

        self.vector_store.add_documents(documents=documents, metadatas=metadatas, ids=ids)
        print(f"Ingested {len(papers)} papers into Vector DB.")

    def retrieve_context(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Retrieve relevant papers for a query (hypothesis generation).
        """
        results = self.vector_store.query(query_text=query, n_results=k)
        return results

rag_pipeline = RAGPipeline()
