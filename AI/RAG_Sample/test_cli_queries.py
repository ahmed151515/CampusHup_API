"""
RAG System CLI Query Tests - Test without API server
Run with: python test_cli_queries.py

This script tests the RAG system directly using the CLI interface.
"""
import subprocess
import sys
import json
from pathlib import Path

# Test queries for the distributed systems knowledge base
test_queries = [
    "What is a distributed system?",
    "Explain the CAP theorem",
    "What are consensus algorithms?",
    "How do distributed systems handle failures?",
    "Describe synchronization mechanisms",
    "What is eventual consistency?",
    "How does replication work in distributed systems?",
    "Explain logical clocks",
    "What are the benefits of distributed systems?",
    "What communication patterns are used?",
]

def run_query(query: str, top_k: int = 5) -> dict:
    """Run a single query using the CLI"""
    try:
        # Run the CLI query command
        result = subprocess.run(
            [sys.executable, "main.py", "query", 
             "--query", query, 
             "--top-k", str(top_k)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Query timed out (120s)",
            "return_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "return_code": -1
        }

def main():
    """Main test runner"""
    print("""
╔════════════════════════════════════════════════════════════════════════╗
║                 RAG SYSTEM CLI QUERY TESTS                            ║
║      Testing Distributed Systems Knowledge Base via CLI                ║
╚════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check if index exists
    index_path = Path("models/faiss_index/faiss.index")
    if not index_path.exists():
        print("\n⚠ FAISS index not found at: models/faiss_index/faiss.index")
        print("Build the index first by running:")
        print("  python main.py build-index --data-dir .")
        print("\nAborting tests.")
        sys.exit(1)
    
    print("\n✓ FAISS index found\n")
    
    passed = 0
    failed = 0
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*70}")
        print(f"[Query {i}/{len(test_queries)}]")
        print(f"Question: {query}")
        print(f"{'='*70}")
        
        result = run_query(query, top_k=5)
        
        if result["success"]:
            print(result["output"])
            print("\n✓ Query successful")
            passed += 1
        else:
            print(f"✗ Query failed")
            if result["error"]:
                print(f"Error: {result['error']}")
            print("Output:", result["output"][:200] if result["output"] else "None")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total queries: {len(test_queries)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_queries)*100):.1f}%")
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
