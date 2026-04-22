import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
FAISS_INDEX_PATH = MODELS_DIR / "faiss_index"

# Ollama Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "all-minilm:latest"
LLM_MODEL = "llama3.2:latest"

# Chunking Configuration
CHUNK_SIZE = 512  # tokens
CHUNK_OVERLAP = 50  # tokens

# Vector DB Configuration
VECTOR_DB_TYPE = "faiss"
FAISS_INDEX_DIMENSION = 384  # all-minilm embedding dimension

# RAG Configuration
TOP_K_RESULTS = 5  # Number of documents to retrieve
SIMILARITY_THRESHOLD = 0.5

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
API_RELOAD = True

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
FAISS_INDEX_PATH.mkdir(exist_ok=True)
