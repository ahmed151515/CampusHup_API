import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Any
from config import FAISS_INDEX_PATH, FAISS_INDEX_DIMENSION, TOP_K_RESULTS


class FaissVectorDB:
    """Manage Faiss vector database"""
    
    def __init__(self, index_path: str = str(FAISS_INDEX_PATH)):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / "faiss.index"
        self.metadata_file = self.index_path / "metadata.pkl"
        self.index = None
        self.documents = []
    
    def create_index(self, dimension: int = FAISS_INDEX_DIMENSION):
        """Create a new Faiss index"""
        self.index = faiss.IndexFlatL2(dimension)
        print(f"Created Faiss index with dimension {dimension}")
    
    def add_vectors(self, vectors: np.ndarray, documents: List[Dict[str, Any]]):
        """Add vectors and metadata to index"""
        if self.index is None:
            self.create_index()
        
        if vectors.shape[0] != len(documents):
            raise ValueError("Number of vectors must match number of documents")
        
        # Add vectors to index
        self.index.add(vectors)
        self.documents.extend(documents)
        print(f"Added {len(vectors)} vectors to index. Total: {self.index.ntotal}")
    
    def search(self, query_vector: np.ndarray, k: int = TOP_K_RESULTS) -> List[Tuple[float, Dict]]:
        """Search for similar vectors"""
        if self.index is None or self.index.ntotal == 0:
            return []
        
        k = min(k, self.index.ntotal)  # Ensure k doesn't exceed total vectors
        distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                results.append((float(distance), self.documents[int(idx)]))
        
        return results
    
    def save(self):
        """Save index and metadata to disk"""
        if self.index is None:
            print("No index to save")
            return
        
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.documents, f)
        print(f"Saved index to {self.index_file}")
        print(f"Saved metadata to {self.metadata_file}")
    
    def load(self):
        """Load index and metadata from disk"""
        if not self.index_file.exists() or not self.metadata_file.exists():
            print("Index files not found")
            return False
        
        self.index = faiss.read_index(str(self.index_file))
        with open(self.metadata_file, 'rb') as f:
            self.documents = pickle.load(f)
        print(f"Loaded index with {self.index.ntotal} vectors")
        return True
    
    def is_available(self) -> bool:
        """Check if index exists"""
        return self.index_file.exists() and self.metadata_file.exists()
