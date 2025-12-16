import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.vector_store import VectorStore

def clear_cache():
    vs = VectorStore()
    coll = vs.collection
    all_data = coll.get()
    
    updates = []
    ids = []
    
    if not all_data['ids']:
        print("Database empty.")
        return

    for i, meta in enumerate(all_data['metadatas']):
        if meta and ("mindmap_json" in meta or "mermaid_code" in meta):
            new_meta = meta.copy()
            new_meta.pop("mindmap_json", None)
            new_meta.pop("mermaid_code", None)
            
            updates.append(new_meta)
            ids.append(all_data['ids'][i])
            
    if ids:
        coll.update(ids=ids, metadatas=updates)
        print(f"Cleared visualization cache for {len(ids)} papers.")
    else:
        print("No cache found to clear.")

if __name__ == "__main__":
    clear_cache()
