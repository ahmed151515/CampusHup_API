import click
from pathlib import Path
from document_loader import DocumentParser
from embeddings import OllamaEmbedder
from vector_db import FaissVectorDB
from retrieval import RAGChain
from config import OLLAMA_BASE_URL


@click.group()
def cli():
    """RAG System CLI"""
    pass


@cli.command()
@click.option('--data-dir', default='.', help='Directory containing PDF and Excel files')
def build_index(data_dir):
    """Build the Faiss index from documents"""
    click.echo("Starting index build...")
    
    # Check Ollama
    embedder = OllamaEmbedder()
    if not embedder.is_available():
        click.echo(f"❌ Error: Ollama not available at {OLLAMA_BASE_URL}", err=True)
        click.echo("Make sure Ollama is running: ollama serve", err=True)
        return
    
    click.echo("✓ Ollama is available")
    
    # Load documents
    click.echo("Loading documents...")
    documents = DocumentParser.load_and_process_documents(data_dir)
    
    if not documents:
        click.echo("❌ No documents found", err=True)
        return
    
    click.echo(f"✓ Loaded {len(documents)} document chunks")
    
    # Generate embeddings
    click.echo("Generating embeddings... (this may take a while)")
    texts = [doc["content"] for doc in documents]
    embeddings = embedder.embed_texts(texts)
    click.echo(f"✓ Generated {len(embeddings)} embeddings")
    
    # Create and save index
    click.echo("Creating Faiss index...")
    vector_db = FaissVectorDB()
    vector_db.add_vectors(embeddings, documents)
    vector_db.save()
    click.echo("✓ Index saved successfully")


@cli.command()
@click.option('--query', prompt='Enter your query', help='Query to search')
@click.option('--top-k', default=5, help='Number of documents to retrieve')
def query(query, top_k):
    """Query the RAG system"""
    # Initialize components
    embedder = OllamaEmbedder()
    vector_db = FaissVectorDB()
    
    # Check Ollama
    if not embedder.is_available():
        click.echo(f"❌ Error: Ollama not available at {OLLAMA_BASE_URL}", err=True)
        return
    
    # Load index
    if not vector_db.load():
        click.echo("❌ Index not found. Run 'build-index' first.", err=True)
        return
    
    click.echo("\n🔍 Querying...")
    rag_chain = RAGChain(vector_db, embedder)
    result = rag_chain.query(query, k=top_k)
    
    click.echo(f"\n{'='*60}")
    click.echo(f"Query: {result['query']}")
    click.echo(f"{'='*60}")
    click.echo(f"\nAnswer:\n{result['answer']}")
    click.echo(f"\n{'='*60}")
    click.echo(f"Retrieved {result['num_retrieved']} documents:")
    click.echo('='*60)
    
    for i, source in enumerate(result['sources'], 1):
        click.echo(f"\n[Source {i}] {source['source']} (Similarity: {source['similarity_score']})")
        click.echo(f"{source['content']}")


@cli.command()
def check_ollama():
    """Check if Ollama is available"""
    embedder = OllamaEmbedder()
    if embedder.is_available():
        click.echo("✓ Ollama is available")
    else:
        click.echo(f"❌ Ollama not available at {OLLAMA_BASE_URL}", err=True)
        click.echo("Start Ollama with: ollama serve", err=True)


@cli.command()
def check_index():
    """Check if index exists"""
    vector_db = FaissVectorDB()
    if vector_db.is_available():
        vector_db.load()
        click.echo(f"✓ Index found with {vector_db.index.ntotal} vectors")
    else:
        click.echo("❌ Index not found. Run 'build-index' first.", err=True)


if __name__ == '__main__':
    cli()
