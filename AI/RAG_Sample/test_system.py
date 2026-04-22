"""
Test and diagnostic script for RAG system
"""
import sys
from pathlib import Path

def check_ollama():
    """Check Ollama availability and models"""
    print("\n" + "="*60)
    print("🔍 Checking Ollama...")
    print("="*60)
    
    try:
        from embeddings import OllamaEmbedder
        from config import OLLAMA_BASE_URL
        
        embedder = OllamaEmbedder()
        if embedder.is_available():
            print(f"✓ Ollama is running at {OLLAMA_BASE_URL}")
            return True
        else:
            print(f"❌ Ollama not found at {OLLAMA_BASE_URL}")
            print("   Start Ollama with: ollama serve")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_documents():
    """Check if documents exist"""
    print("\n" + "="*60)
    print("📄 Checking Documents...")
    print("="*60)
    
    pdf_file = Path("CompanyVacationPolicy.pdf")
    excel_file = Path("employee_list.xlsx")
    
    pdf_exists = pdf_file.exists()
    excel_exists = excel_file.exists()
    
    if pdf_exists:
        size_mb = pdf_file.stat().st_size / (1024*1024)
        print(f"✓ {pdf_file.name} ({size_mb:.2f} MB)")
    else:
        print(f"❌ {pdf_file.name} not found")
    
    if excel_exists:
        size_mb = excel_file.stat().st_size / (1024*1024)
        print(f"✓ {excel_file.name} ({size_mb:.2f} MB)")
    else:
        print(f"❌ {excel_file.name} not found")
    
    return pdf_exists and excel_exists


def check_index():
    """Check if Faiss index exists"""
    print("\n" + "="*60)
    print("🗂️  Checking Index...")
    print("="*60)
    
    try:
        from vector_db import FaissVectorDB
        
        vector_db = FaissVectorDB()
        if vector_db.is_available():
            vector_db.load()
            print(f"✓ Faiss index found")
            print(f"  Total vectors: {vector_db.index.ntotal}")
            print(f"  Documents indexed: {len(vector_db.documents)}")
            return True
        else:
            print("❌ Faiss index not found")
            print("   Build it with: python main.py build-index --data-dir .")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_embedding():
    """Test embedding generation"""
    print("\n" + "="*60)
    print("🧠 Testing Embedding Generation...")
    print("="*60)
    
    try:
        from embeddings import OllamaEmbedder
        
        embedder = OllamaEmbedder()
        test_text = "What is the vacation policy?"
        
        print(f"Generating embedding for: '{test_text}'")
        embedding = embedder.embed_text(test_text)
        
        print(f"✓ Embedding generated")
        print(f"  Dimension: {embedding.shape[0]}")
        print(f"  First 5 values: {embedding[:5]}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_query():
    """Test a sample query"""
    print("\n" + "="*60)
    print("❓ Testing Query...")
    print("="*60)
    
    try:
        from embeddings import OllamaEmbedder
        from vector_db import FaissVectorDB
        from retrieval import RAGChain
        
        embedder = OllamaEmbedder()
        vector_db = FaissVectorDB()
        
        if not vector_db.load():
            print("❌ Index not loaded. Build it first.")
            return False
        
        rag_chain = RAGChain(vector_db, embedder)
        query = "What are the vacation policies?"
        
        print(f"Query: '{query}'")
        print("Generating response... (this may take a minute)")
        
        result = rag_chain.query(query, k=3, return_sources=False)
        
        print(f"\n✓ Response generated")
        print(f"  Retrieved {result['num_retrieved']} documents")
        print(f"\nAnswer (first 300 chars):\n{result['answer'][:300]}...")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostics"""
    print("""
╔════════════════════════════════════════════════════════════╗
║           RAG SYSTEM - DIAGNOSTIC TEST                     ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Run checks
    results.append(("Ollama", check_ollama()))
    results.append(("Documents", check_documents()))
    results.append(("Index", check_index()))
    
    if results[-1][1]:  # If index exists
        results.append(("Embedding", test_embedding()))
        results.append(("Query", test_query()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Summary")
    print("="*60)
    
    for name, passed in results:
        status = "✓" if passed else "❌"
        print(f"{status} {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ All checks passed! System is ready.")
        print("\nStart querying with:")
        print("  python main.py query")
    else:
        print("❌ Some checks failed. See details above.")
        print("\nNext steps:")
        if not results[0][1]:
            print("  1. Start Ollama: ollama serve")
        if not results[1][1]:
            print("  2. Add PDF and Excel files to this folder")
        if not results[2][1]:
            print("  3. Build index: python main.py build-index --data-dir .")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
