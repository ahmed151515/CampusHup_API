"""
API Usage Examples

This file contains cURL and Python examples for using the RAG System API.
Start the API server first: python api.py
"""

# ============================================================================
# CURL Examples (PowerShell / Command Prompt)
# ============================================================================

"""
1. Health Check
   
   curl http://localhost:8000/health
   
   Response:
   {
     "ollama_available": true,
     "index_available": true,
     "total_vectors": 125
   }
"""

"""
2. Query the RAG System (Regular)

   curl -X POST http://localhost:8000/query `
     -H "Content-Type: application/json" `
     -d '{
       "query": "What are the vacation policies?",
       "top_k": 5,
       "return_sources": true
     }'
   
   Response:
   {
     "query": "What are the vacation policies?",
     "answer": "Based on the company vacation policy, employees receive...",
     "num_retrieved": 3,
     "sources": [
       {
         "content": "[Page 1] Annual Vacation Policy...",
         "source": "CompanyVacationPolicy.pdf",
         "similarity_score": 0.8234
       }
     ]
   }
"""

"""
3. Stream Response (Real-time answers)

   curl -X POST http://localhost:8000/query/stream `
     -H "Content-Type: application/json" `
     -d '{"query": "Tell me about employee benefits"}'
   
   Streams response chunks as they're generated
"""

# ============================================================================
# Python Examples
# ============================================================================

import requests
import json

BASE_URL = "http://localhost:8000"


def health_check():
    """Check system status"""
    response = requests.get(f"{BASE_URL}/health")
    print(json.dumps(response.json(), indent=2))


def query_rag(query: str, top_k: int = 5):
    """Query the RAG system"""
    payload = {
        "query": query,
        "top_k": top_k,
        "return_sources": True
    }
    
    response = requests.post(f"{BASE_URL}/query", json=payload)
    result = response.json()
    
    print(f"Query: {result['query']}")
    print(f"Answer: {result['answer']}\n")
    print(f"Sources ({result['num_retrieved']} retrieved):")
    for i, source in enumerate(result.get('sources', []), 1):
        print(f"  [{i}] {source['source']} (Similarity: {source['similarity_score']})")
        print(f"      {source['content'][:100]}...\n")


def stream_response(query: str):
    """Stream response generation"""
    payload = {"query": query, "top_k": 5}
    
    with requests.post(f"{BASE_URL}/query/stream", json=payload, stream=True) as r:
        for line in r.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8').replace('data: ', ''))
                print(data['chunk'], end='', flush=True)
        print()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("RAG System API Examples\n")
    print("Make sure to start the API first: python api.py\n")
    
    # Health check
    print("1. Health Check:")
    try:
        health_check()
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Regular query
    print("2. Regular Query:")
    try:
        query_rag("What are the vacation policies?")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Streaming query
    print("3. Streaming Response:")
    try:
        stream_response("Tell me about employee benefits")
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Advanced: Batch Queries
# ============================================================================

def batch_query(queries: list):
    """Execute multiple queries"""
    results = []
    for query in queries:
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"query": query, "top_k": 3}
            )
            results.append({
                "query": query,
                "answer": response.json()["answer"],
                "status": "success"
            })
        except Exception as e:
            results.append({
                "query": query,
                "error": str(e),
                "status": "failed"
            })
    
    return results


# ============================================================================
# Advanced: Custom Parameters
# ============================================================================

"""
Query Parameters:
- query (required): The question to ask
- top_k (optional, default=5): Number of documents to retrieve
- return_sources (optional, default=true): Include source documents in response

Examples:
{
  "query": "What is the vacation policy?",
  "top_k": 3,
  "return_sources": false
}
"""

# ============================================================================
# Integration with Other Tools
# ============================================================================

"""
Using with requests library in a web application:

from fastapi import FastAPI
import requests

app = FastAPI()

@app.post("/ask")
async def ask_question(question: str):
    rag_response = requests.post(
        "http://localhost:8000/query",
        json={"query": question}
    )
    return rag_response.json()
"""

"""
Using with curl in a shell script:

#!/bin/bash
QUERY="$1"
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"$QUERY\", \"top_k\": 5}" | jq '.answer'
"""
