# RAG System - Ollama + Langchain + Faiss

A complete Retrieval-Augmented Generation (RAG) system that embeds PDF and Excel documents and allows you to query them using Ollama models with a Faiss vector database.

## Architecture

```
┌─────────────────────────┐
│   PDF / Excel Files     │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Document Parser        │  (PyPDF2, openpyxl)
│  - Extract text         │
│  - Chunk documents      │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Embeddings Generator   │  (Ollama all-minilm)
│  - Convert chunks to    │
│    vector embeddings    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Faiss Vector DB        │  (Persist embeddings)
│  - Index vectors        │
│  - Similarity search    │
└────────────┬────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────────┐  ┌──────────────┐
│  CLI Tool   │  │  FastAPI     │
│  - Query    │  │  - REST API  │
│  - Build    │  │  - Streaming │
└────┬────────┘  └──────┬───────┘
     │                  │
     └────────┬─────────┘
              │
              ▼
      ┌───────────────────┐
      │  LLM (llama3.2)   │
      │  - Generate       │
      │    answers        │
      └───────────────────┘
```

## Features

✅ **Document Processing**: Parse PDF and Excel files automatically
✅ **Smart Chunking**: Overlapping chunks for better context
✅ **Fast Embeddings**: Using lightweight all-minilm (45MB)
✅ **Scalable Vector DB**: Faiss index for fast similarity search
✅ **Dual Interface**: CLI tool + REST API
✅ **Streaming Responses**: Real-time answer generation
✅ **Source Attribution**: See which documents were used

## Prerequisites

- **Python 3.8+**
- **Ollama** running locally (with models: `all-minilm:latest`, `llama3.2:latest`)
- **Pip** for dependency management

## Installation

### 1. Install Python Dependencies

```bash
cd "C:\Users\zedan\OneDrive\Documents\RAG_Sample"
pip install -r requirements.txt
```

**Important on Windows**: If you get FAISS installation issues:
```bash
pip install faiss-cpu
# OR if using GPU:
pip install faiss-gpu
```

### 2. Verify Ollama is Running

```bash
# In a new terminal/PowerShell
ollama serve
```

Then verify models are available:
```bash
ollama list
```

You should see:
- `all-minilm:latest`
- `llama3.2:latest`

If missing, pull them:
```bash
ollama pull all-minilm
ollama pull llama3.2
```

## Usage

### Step 1: Build the Index

Build Faiss index from your PDF and Excel files:

```bash
python main.py build-index --data-dir .
```

This will:
1. ✓ Parse `CompanyVacationPolicy.pdf` and `employee_list.xlsx`
2. ✓ Chunk documents intelligently
3. ✓ Generate embeddings using all-minilm
4. ✓ Create and save Faiss index

**Expected output:**
```
Starting index build...
✓ Ollama is available
Loading documents...
Processing PDF: CompanyVacationPolicy.pdf
Processing Excel: employee_list.xlsx
✓ Loaded X document chunks
Generating embeddings... (this may take a while)
...
✓ Generated X embeddings
Creating Faiss index...
✓ Index saved successfully
```

### Step 2: Query the System

#### CLI Interface

```bash
# Interactive query
python main.py query

# Or with query directly
python main.py query --query "What are the vacation policy days?"
```

**Example:**
```
Enter your query: How many vacation days do employees get?
🔍 Querying...

============================================================
Query: How many vacation days do employees get?
============================================================

Answer:
Based on the company vacation policy, employees typically receive:
- 20 days of paid vacation per year
- 5 additional days for management
- Additional days for senior roles

============================================================
Retrieved 3 documents:
============================================================

[Source 1] CompanyVacationPolicy.pdf (Similarity: 0.8234)
[Page 1] Annual Vacation Policy...
```

#### REST API Interface

Start the API server:

```bash
python api.py
```

API will be available at `http://localhost:8000`

**Query endpoint** (POST):
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are vacation policies?", "top_k": 5}'
```

**Streaming endpoint** (Server-Sent Events):
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about employee benefits"}'
```

**Health check**:
```bash
curl http://localhost:8000/health
```

**Interactive API docs** (Swagger UI):
- http://localhost:8000/docs

## CLI Commands

```bash
# Build/rebuild index
python main.py build-index [--data-dir PATH]

# Query the system
python main.py query [--query TEXT] [--top-k NUM]

# Check Ollama status
python main.py check-ollama

# Check index status
python main.py check-index

# Start REST API
python api.py
```

## Configuration

Edit `config.py` to customize:

```python
# Ollama Models
EMBEDDING_MODEL = "all-minilm:latest"  # For embeddings
LLM_MODEL = "llama3.2:latest"          # For answer generation

# Chunking
CHUNK_SIZE = 512        # tokens per chunk
CHUNK_OVERLAP = 50      # token overlap between chunks

# Retrieval
TOP_K_RESULTS = 5       # documents to retrieve
SIMILARITY_THRESHOLD = 0.5  # minimum similarity score

# API
API_HOST = "0.0.0.0"
API_PORT = 8000
```

## Project Structure

```
RAG_Sample/
├── config.py              # Configuration
├── document_loader.py     # PDF/Excel parsing
├── embeddings.py          # Ollama embeddings
├── vector_db.py           # Faiss index management
├── retrieval.py           # RAG chain orchestration
├── cli.py                 # Command-line interface
├── api.py                 # FastAPI server
├── main.py                # Entry point
├── requirements.txt       # Python dependencies
├── models/
│   └── faiss_index/       # Saved Faiss index
├── CompanyVacationPolicy.pdf
└── employee_list.xlsx
```

## Troubleshooting

### Ollama not available
```
❌ Error: Ollama not available at http://localhost:11434
```
**Solution**: Make sure Ollama is running
```bash
ollama serve
```

### Index not found
```
❌ Index not found. Run 'build-index' first.
```
**Solution**: Build the index first
```bash
python main.py build-index --data-dir .
```

### Slow embedding generation
- All-minilm is fast but generating embeddings for large datasets still takes time
- First run will be slow; subsequent queries are fast (index is cached)

### Memory issues with Faiss
- Faiss CPU is lightweight; if issues persist, reduce chunk size or use fewer documents
- Consider Faiss GPU if you have CUDA: `pip install faiss-gpu`

### PDF extraction issues
- Some PDFs may require OCR for scanned documents
- Excel files should be in `.xlsx` format (not `.xls`)

## Performance Tips

1. **Chunking**: Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` based on your documents
2. **Top-K**: Lower `TOP_K_RESULTS` for faster retrieval
3. **Batch Processing**: For many documents, build index once and reuse

## Next Steps

- Add more documents: Just place PDF/Excel files in the project folder and rebuild index
- Fine-tune prompts: Edit system prompt in `retrieval.py`
- Use different models: Change `EMBEDDING_MODEL` or `LLM_MODEL` in `config.py`
- Add database support: Extend `vector_db.py` to use PostgreSQL + pgvector

## License

MIT

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify Ollama is running and models are available
3. Check that PDF/Excel files exist in the project folder
