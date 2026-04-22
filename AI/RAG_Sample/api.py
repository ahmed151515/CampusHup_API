from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
from embeddings import OllamaEmbedder
from vector_db import FaissVectorDB
from retrieval import RAGChain
from config import API_HOST, API_PORT, OLLAMA_BASE_URL


# Initialize FastAPI
app = FastAPI(title="RAG System API", description="Retrieve and Generate answers from your documents")

# Initialize components
embedder = OllamaEmbedder()
vector_db = FaissVectorDB()
rag_chain = None


# Models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    return_sources: Optional[bool] = True


class SourceDocument(BaseModel):
    content: str
    source: str
    similarity_score: float


class QueryResponse(BaseModel):
    query: str
    answer: str
    num_retrieved: int
    sources: Optional[List[SourceDocument]] = []


class StatusResponse(BaseModel):
    ollama_available: bool
    index_available: bool
    total_vectors: int


# Startup event
@app.on_event("startup")
async def startup_event():
    global rag_chain
    
    # Check Ollama
    if not embedder.is_available():
        print(f"⚠️  Warning: Ollama not available at {OLLAMA_BASE_URL}")
    
    # Load index
    if vector_db.load():
        rag_chain = RAGChain(vector_db, embedder)
        print(f"✓ Loaded index with {vector_db.index.ntotal} vectors")
    else:
        print("⚠️  Warning: Index not found. Build index with CLI first.")


# Health check
@app.get("/health", response_model=StatusResponse)
async def health():
    """Check system status"""
    return StatusResponse(
        ollama_available=embedder.is_available(),
        index_available=vector_db.is_available(),
        total_vectors=vector_db.index.ntotal if vector_db.index else 0
    )


# Query endpoint
@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the RAG system"""
    if not embedder.is_available():
        raise HTTPException(status_code=503, detail="Ollama not available")
    
    if not rag_chain:
        raise HTTPException(status_code=503, detail="Index not loaded. Build index first.")
    
    result = rag_chain.query(
        request.query,
        k=request.top_k,
        return_sources=request.return_sources
    )
    
    return QueryResponse(
        query=result["query"],
        answer=result["answer"],
        num_retrieved=result["num_retrieved"],
        sources=[
            SourceDocument(
                content=source["content"],
                source=source["source"],
                similarity_score=source["similarity_score"]
            )
            for source in result.get("sources", [])
        ] if request.return_sources else []
    )


# Stream endpoint
@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    """Stream query response"""
    if not embedder.is_available():
        raise HTTPException(status_code=503, detail="Ollama not available")
    
    if not rag_chain:
        raise HTTPException(status_code=503, detail="Index not loaded")
    
    def generate():
        for chunk in rag_chain.stream_response(request.query, k=request.top_k):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
