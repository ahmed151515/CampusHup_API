import requests
import numpy as np
from typing import List
from config import OLLAMA_BASE_URL, EMBEDDING_MODEL, FAISS_INDEX_DIMENSION


class OllamaEmbedder:
    """Generate embeddings using Ollama"""
    
    def __init__(self, model: str = EMBEDDING_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url
        self.embedding_url = f"{base_url}/api/embeddings"
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        try:
            response = requests.post(
                self.embedding_url,
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector on error
            return np.zeros(FAISS_INDEX_DIMENSION, dtype=np.float32)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for i, text in enumerate(texts):
            if (i + 1) % 10 == 0:
                print(f"Embedded {i + 1}/{len(texts)} documents...")
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        
        return np.array(embeddings, dtype=np.float32)
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
