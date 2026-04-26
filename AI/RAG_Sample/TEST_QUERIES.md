# RAG System Test Queries

## Available PDF Files
The system contains the following documents about Distributed Systems:
- **Chapter1_Distributed-1.pdf** - Introduction to distributed systems fundamentals
- **Chapter-2_Distributed-1.pdf** - Core concepts and architectures
- **Chapter-3-1.pdf** - Advanced topics and patterns

---

## CLI Test Queries

Use these commands to test the RAG system:

```powershell
# Query 1: Basic distributed systems concepts
python main.py query --query "What is a distributed system?" --top-k 5

# Query 2: Consensus algorithms
python main.py query --query "Explain consensus algorithms in distributed systems" --top-k 5

# Query 3: Communication protocols
python main.py query --query "What are the main communication protocols used in distributed systems?" --top-k 5

# Query 4: Fault tolerance
python main.py query --query "How do distributed systems handle failures?" --top-k 5

# Query 5: Scaling strategies
python main.py query --query "What are the strategies for scaling distributed systems?" --top-k 5

# Query 6: CAP theorem
python main.py query --query "Explain the CAP theorem" --top-k 5

# Query 7: Load balancing
python main.py query --query "How is load balancing implemented in distributed systems?" --top-k 5

# Query 8: Replication strategies
python main.py query --query "What are the different replication strategies?" --top-k 5

# Query 9: Distributed transactions
python main.py query --query "How do distributed transactions work?" --top-k 5

# Query 10: Message queues
python main.py query --query "What role do message queues play in distributed systems?" --top-k 5
```

---

## API Test Queries (Using cURL)

First, start the API server:
```powershell
python api.py
```

Then test these endpoints:

### Health Check
```powershell
curl http://localhost:8000/health
```

### Query Examples

```powershell
# Query 1: Basic concepts
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{
    "query": "What are the key principles of distributed systems design?",
    "top_k": 5,
    "return_sources": true
  }'

# Query 2: Consistency models
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{
    "query": "Describe different consistency models in distributed systems",
    "top_k": 5,
    "return_sources": true
  }'

# Query 3: Network issues
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{
    "query": "How are network partitions handled in distributed systems?",
    "top_k": 5,
    "return_sources": true
  }'

# Query 4: Synchronization
curl -X POST http://localhost:8000/query `
  -H "Content-Type: application/json" `
  -d '{
    "query": "What synchronization mechanisms are used in distributed systems?",
    "top_k": 5,
    "return_sources": true
  }'

# Query 5: Streaming responses
curl -X POST http://localhost:8000/query/stream `
  -H "Content-Type: application/json" `
  -d '{
    "query": "Explain the purpose and importance of monitoring in distributed systems",
    "top_k": 5
  }'
```

---

## Python Script Test Queries

Create a file `test_rag_queries.py`:

```python
"""
RAG System Query Tests
Run with: python test_rag_queries.py
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

test_queries = [
    "What is a distributed system and its main characteristics?",
    "Explain the differences between synchronous and asynchronous communication",
    "What are the advantages and disadvantages of distributed systems?",
    "How do you handle clock synchronization in distributed systems?",
    "Describe the role of RPC (Remote Procedure Call) in distributed systems",
    "What is eventual consistency and when is it appropriate to use?",
    "How do distributed systems ensure data durability?",
    "Explain the concept of logical clocks",
    "What are the benefits and challenges of microservices architecture?",
    "How do distributed databases differ from traditional databases?",
]

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("HEALTH CHECK TEST")
    print("="*60)
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(json.dumps(response.json(), indent=2))
        print("✓ Health check passed")
    except Exception as e:
        print(f"✗ Health check failed: {e}")

def test_queries():
    """Test all queries"""
    print("\n" + "="*60)
    print("QUERY TESTS")
    print("="*60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}]")
        print(f"Query: {query}")
        print("-" * 60)
        
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": query,
                    "top_k": 5,
                    "return_sources": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Answer: {result['answer'][:200]}...")
                print(f"Sources retrieved: {result['num_retrieved']}")
                print("✓ Query successful")
            else:
                print(f"✗ Query failed with status {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"✗ Query failed: {e}")
        
        # Small delay between queries
        time.sleep(1)

if __name__ == "__main__":
    print("Starting RAG System Query Tests...")
    test_health()
    test_queries()
    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)
```

---

## Expected Test Results

When running these queries, you should see:
- ✓ Relevant answers about distributed systems concepts
- ✓ Retrieved document sources with similarity scores
- ✓ Responses based on the content from your PDF chapters
- ✓ Latency within acceptable range (depends on Ollama model)

## Testing Checklist

- [ ] Build index: `python main.py build-index --data-dir .`
- [ ] Run CLI queries with `python main.py query`
- [ ] Start API: `python api.py`
- [ ] Test health endpoint
- [ ] Test multiple queries via cURL
- [ ] Test streaming responses
- [ ] Run Python test script: `python test_rag_queries.py`
- [ ] Verify answers are relevant to distributed systems
- [ ] Check retrieval quality (do retrieved sources match query intent?)

