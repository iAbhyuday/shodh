import sys
import os
import chromadb
from unittest.mock import patch, MagicMock

# Ensure src is in pythonpath
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import get_settings
from src.db.vector_store import get_chroma_client

def verify_remote_config():
    print("Verifying Remote ChromaDB Config Logic...")
    
    # 1. Default (Local)
    settings = get_settings()
    settings.VECTOR_DB_HOST = None
    
    try:
        client = get_chroma_client(settings)
        print(f"Default Client Type: {type(client)}")
    except Exception as e:
        print(f"FAIL: Failed to create default client: {e}")
        sys.exit(1)

    # 2. Remote
    print("Testing Remote Config...")
    settings.VECTOR_DB_HOST = "localhost"
    settings.VECTOR_DB_PORT = 8000
    
    # Mock HttpClient and ChromaSettings
    with patch('chromadb.HttpClient') as MockHttpClient, \
         patch('src.db.vector_store.ChromaSettings') as MockSettings:
        
        client = get_chroma_client(settings)
        print("Mocked HttpClient called.")
        
        # Verify call args
        args, kwargs = MockHttpClient.call_args
        if kwargs.get('host') == "localhost" and kwargs.get('port') == 8000:
             print("SUCCESS: HttpClient instantiated correctly with host/port.")
        else:
             print(f"FAIL: HttpClient called with wrong args: {kwargs}")
             
        if 'settings' in kwargs:
             print("SUCCESS: settings param passed to HttpClient.")
        else:
             print("WARNING: settings param NOT passed (logic might differ from user edit check).")

if __name__ == "__main__":
    verify_remote_config()
