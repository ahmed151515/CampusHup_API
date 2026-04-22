"""
RAG System Main Entry Point
"""
from cli import cli
from pathlib import Path
import sys


def main():
    """Main entry point"""
    # Print banner
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║           RAG SYSTEM - Ollama + Langchain + Faiss          ║
    ║         Query your Documents using AI                      ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Run CLI
    cli()


if __name__ == "__main__":
    main()
