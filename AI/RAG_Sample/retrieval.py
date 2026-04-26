import requests
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from embeddings import OllamaEmbedder
from vector_db import FaissVectorDB
from config import OLLAMA_BASE_URL, LLM_MODEL, TOP_K_RESULTS, SIMILARITY_THRESHOLD


class RAGChain:
    """Orchestrate the RAG pipeline"""
    
    def __init__(self, vector_db: FaissVectorDB, embedder: OllamaEmbedder):
        self.vector_db = vector_db
        self.embedder = embedder
        self.llm_url = f"{OLLAMA_BASE_URL}/api/generate"
    
    def retrieve(self, query: str, k: int = TOP_K_RESULTS) -> List[Dict[str, Any]]:
        """Retrieve relevant documents for query"""
        query_embedding = self.embedder.embed_text(query)
        results = self.vector_db.search(query_embedding, k=k)
        
        # Filter by similarity threshold
        retrieved_docs = []
        for distance, doc in results:
            # Convert L2 distance to similarity score (lower distance = higher similarity)
            similarity = 1 / (1 + distance)
            if similarity >= SIMILARITY_THRESHOLD:
                doc_with_score = {**doc, "similarity_score": similarity}
                retrieved_docs.append(doc_with_score)
        
        return retrieved_docs
    
    def build_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Build context from retrieved documents"""
        context = "Retrieved Context:\n"
        for i, doc in enumerate(retrieved_docs, 1):
            context += f"\n[Document {i}] (Source: {doc.get('source', 'Unknown')})\n"
            context += f"{doc['content']}\n"
            print(context)
        return context
    
    def generate_response(self, query: str, context: str) -> str:
        """Generate response using Ollama LLM"""
        prompt = f"""You are a helpful assistant. Use the provided context to answer the user's question.
If the context doesn't contain relevant information, say so.

{context}

User Question: {query}

Answer:"""
        
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120
            )
            response.raise_for_status()
            answer = response.json().get("response", "").strip()
            return answer
        except Exception as e:
            return f"Error generating response: {e}"
    
    def query(self, query: str, k: int = TOP_K_RESULTS, return_sources: bool = True) -> Dict[str, Any]:
        """Execute full RAG pipeline"""
        # Retrieve
        retrieved_docs = self.retrieve(query, k=k)
        
        if not retrieved_docs:
            return {
                "query": query,
                "answer": "No relevant documents found in the knowledge base.",
                "sources": [],
                "num_retrieved": 0
            }
        
        # Build context
        context = self.build_context(retrieved_docs)
        
        # Generate
        answer = self.generate_response(query, context)
        
        # Prepare response
        result = {
            "query": query,
            "answer": answer,
            "num_retrieved": len(retrieved_docs),
        }
        
        if return_sources:
            result["sources"] = [
                {
                    "content": doc["content"][:200] + "...",
                    "source": doc["source"],
                    "similarity_score": round(doc["similarity_score"], 4)
                }
                for doc in retrieved_docs
            ]
        
        return result
    
    def stream_response(self, query: str, k: int = TOP_K_RESULTS):
        """Stream response generation"""
        retrieved_docs = self.retrieve(query, k=k)
        
        if not retrieved_docs:
            yield "No relevant documents found in the knowledge base."
            return
        
        context = self.build_context(retrieved_docs)
        prompt = f"""You are a helpful assistant. Use the provided context to answer the user's question.
If the context doesn't contain relevant information, say so.

{context}

User Question: {query}

Answer:"""
        
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": 0.7,
                },
                timeout=120,
                stream=True
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
        except Exception as e:
            yield f"Error generating response: {e}"
