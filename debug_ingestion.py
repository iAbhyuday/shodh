import sys
import os
# Add src to path
sys.path.append(os.getcwd())

from src.agents.ingestion_agent import IngestionAgent
from src.agents.metrics_agent import MetricsAgent
from src.core.rag import rag_pipeline

def test_ingestion():
    topics = ["Agents"]
    print(f"Testing ingestion for: {topics}")
    
    ingestion_agent = IngestionAgent()
    papers = ingestion_agent.run(topics)
    print(f"Fetched {len(papers)} papers.")
    
    if not papers:
        print("No papers fetched. Check network or API.")
        return

    print("Extracting metrics (mocking/Ollama)...")
    metrics_agent = MetricsAgent()
    enriched_papers = metrics_agent.run(papers[:1]) # Test with just 1 paper to be fast
    print(f"Enriched paper 1: {enriched_papers[0].get('metrics')}")
    
    print("Ingesting into RAG...")
    rag_pipeline.ingest_papers(enriched_papers)
    print("Ingestion complete. Checking DB...")
    
    count = rag_pipeline.vector_store.collection.count()
    print(f"DB Count: {count}")

if __name__ == "__main__":
    test_ingestion()
