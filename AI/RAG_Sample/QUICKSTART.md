# Quick Start Guide

## One-Time Setup

### 1. Install Python Dependencies

Open PowerShell in the `RAG_Sample` folder and run:

```powershell
pip install -r requirements.txt
```

### 2. Ensure Ollama is Running

Open a new PowerShell and run:

```powershell
ollama serve
```

Keep this window open while using the RAG system.

### 3. Verify Models Are Available

In another PowerShell:

```powershell
ollama list
```

Should show:
- `all-minilm:latest` (45 MB)
- `llama3.2:latest` (2.0 GB)

If missing:
```powershell
ollama pull all-minilm
ollama pull llama3.2
```

---

## Using the RAG System

### First Run: Build the Index

```powershell
python main.py build-index --data-dir .
```

This processes your PDF and Excel files. **Takes a few minutes on first run.**

### Query the System (CLI)

```powershell
# Interactive mode - you'll be prompted for a query
python main.py query

# Or provide query directly
python main.py query --query "What are the vacation policies?"
```

### API Server (Alternative Interface)

Start the REST API:

```powershell
python api.py
```

Then open browser: **http://localhost:8000/docs**

---

## Example Queries

Try these questions:

```
- "How many vacation days do employees get?"
- "What are the vacation policy rules?"
- "List all employees and their departments"
- "What are the benefits for senior staff?"
- "Tell me about company vacation policies"
```

---

## Troubleshooting

**"Ollama not available"**
→ Make sure `ollama serve` is running in another PowerShell window

**"Index not found"**
→ Run `python main.py build-index --data-dir .` first

**"Slow embedding generation"**
→ Normal on first run. Results are cached. Subsequent queries are instant.

---

## Project Files Overview

| File | Purpose |
|------|---------|
| `config.py` | Settings (models, chunk size, etc.) |
| `document_loader.py` | Parse PDF & Excel |
| `embeddings.py` | Call Ollama for embeddings |
| `vector_db.py` | Manage Faiss index |
| `retrieval.py` | RAG pipeline (retrieve + generate) |
| `cli.py` | Command-line tool |
| `api.py` | REST API server |
| `main.py` | Entry point |

---

## Next: Customize

See `README.md` for detailed configuration and advanced usage.
