"""
RAG System Query Tests - Test script to validate the RAG system
Run with: python test_rag_queries.py

Make sure to start the API first:
  python api.py
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

# Test queries covering different aspects of distributed systems
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
    "What consensus algorithms are commonly used?",
    "How is load balancing implemented in distributed systems?",
    "Explain the CAP theorem and its implications",
    "What are the challenges in distributed system design?",
    "How do you achieve fault tolerance in distributed systems?",
]

def test_health():
    """Test health check endpoint"""
    print("\n" + "="*70)
    print("HEALTH CHECK TEST")
    print("="*70)
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        result = response.json()
        print(json.dumps(result, indent=2))
        
        if response.status_code == 200:
            print("✓ Health check PASSED")
            return True
        else:
            print("✗ Health check FAILED")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to {BASE_URL}")
        print("  Make sure the API is running: python api.py")
        return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_queries(limit=None):
    """Test all queries"""
    print("\n" + "="*70)
    print("QUERY TESTS")
    print("="*70)
    
    queries_to_test = test_queries[:limit] if limit else test_queries
    passed = 0
    failed = 0
    
    for i, query in enumerate(queries_to_test, 1):
        print(f"\n[Query {i}/{len(queries_to_test)}]")
        print(f"Question: {query}")
        print("-" * 70)
        
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": query,
                    "top_k": 5,
                    "return_sources": True
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Display answer (first 300 chars)
                answer = result.get('answer', 'No answer generated')
                print(f"\nAnswer: {answer[:300]}{'...' if len(answer) > 300 else ''}")
                
                # Display sources
                sources = result.get('sources', [])
                num_retrieved = result.get('num_retrieved', 0)
                print(f"\nSources retrieved: {num_retrieved}")
                
                for j, source in enumerate(sources[:3], 1):  # Show top 3 sources
                    source_name = source.get('source', 'Unknown')
                    similarity = source.get('similarity_score', 0)
                    content_preview = source.get('content', '')[:100]
                    print(f"\n  [{j}] {source_name}")
                    print(f"      Similarity: {similarity:.4f}")
                    print(f"      Content: {content_preview}...")
                
                print("\n✓ Query successful")
                passed += 1
            else:
                print(f"✗ Query failed with status {response.status_code}")
                print(response.text)
                failed += 1
        except requests.exceptions.Timeout:
            print(f"✗ Query timed out (60s)")
            failed += 1
        except Exception as e:
            print(f"✗ Query failed: {e}")
            failed += 1
        
        # Small delay between queries to avoid overloading
        time.sleep(2)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total: {len(queries_to_test)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(queries_to_test)*100):.1f}%")
    
    return failed == 0

def main():
    """Main test runner"""
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║                   RAG SYSTEM QUERY TESTS                              ║
║     Testing Distributed Systems Knowledge Base                        ║
╚════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for optional limit argument
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Running limited test set: {limit} queries\n")
        except ValueError:
            print(f"Usage: python test_rag_queries.py [number_of_queries]")
            sys.exit(1)
    
    # Run tests
    health_ok = test_health()
    
    if not health_ok:
        print("\n✗ Cannot proceed without healthy API server")
        sys.exit(1)
    
    all_passed = test_queries(limit=limit)
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("⚠ Some tests failed. Check output above.")
    print("="*70)

if __name__ == "__main__":
    main()
