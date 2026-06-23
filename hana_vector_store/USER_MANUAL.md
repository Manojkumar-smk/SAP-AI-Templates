# HANA Vector Store — User Manual

Mini templates for embedding documents and storing/searching them in SAP HANA Cloud's native Vector Engine.

**What is a vector store?**  
Text is converted into numbers (vectors/embeddings). HANA stores these vectors and can find the most *semantically similar* chunks for any query using `COSINE_SIMILARITY` — even if the exact words don't match.

---

## Folder Structure

```
hana_vector_store/
├── embedding_setup.py      ← Set up embedding model via SAP Gen AI Hub
├── document_loaders.py     ← Load documents from text, txt, PDF, CSV, Excel, URL
├── text_chunker.py         ← Split documents into chunks
├── vector_table.py         ← Create / clear HANA vector table
├── embed_and_store.py      ← Generate embeddings and insert into HANA
├── similarity_search.py    ← Search stored vectors by semantic similarity
├── vector_store_agent.py   ← Full pipeline in one class (add + search + stats)
├── .env.example            ← Template for your .env file
├── requirements.txt        ← All pip dependencies
└── USER_MANUAL.md          ← This file
```

---

## How the Pieces Fit Together

```
Your Document (PDF / CSV / URL / text / ...)
        │
        ▼
document_loaders.py   ← loads into LangChain Document objects
        │
        ▼
text_chunker.py       ← splits into smaller chunks (500 chars default)
        │
        ▼
embedding_setup.py    ← converts each chunk to a vector via SAP Gen AI Hub
        │
        ▼
vector_table.py       ← ensures the HANA table with REAL_VECTOR column exists
        │
        ▼
embed_and_store.py    ← inserts chunk + vector into HANA
        │
    HANA Vector Table
        │
        ▼
similarity_search.py  ← embeds your query, runs COSINE_SIMILARITY, returns top-K
```

`vector_store_agent.py` runs this entire flow with one `store.add()` / `store.search()` call.

---

## Quick Decision Guide

| I want to… | Use this file |
|------------|--------------|
| Set up the embedding model only | `embedding_setup.py` |
| Load a PDF / CSV / URL into Documents | `document_loaders.py` |
| Split long text into chunks | `text_chunker.py` |
| Create or reset the HANA vector table | `vector_table.py` |
| Embed chunks and insert into HANA | `embed_and_store.py` |
| Search for relevant chunks | `similarity_search.py` |
| Full pipeline — add + search in one class | `vector_store_agent.py` |

---

## Setup (One-Time)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file
```bash
cp .env.example .env
```
Fill in:
```
HANA_HOST=your-host.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=YourPassword

EMBEDDING_DEPLOYMENT_ID=your-embedding-deployment-id
VECTOR_TABLE_NAME=VECTOR_STORE
VECTOR_DIMENSION=1536
```

> **Where to get `EMBEDDING_DEPLOYMENT_ID`:**  
> SAP AI Launchpad → AI Core → Deployments → copy the ID of your embedding model deployment.

### 3. HANA connection
These files import `connect()` from `../hana_db_connection/connect_env.py`.  
Make sure that folder is set up (see `hana_db_connection/USER_MANUAL.md`).

---

## File-by-File Guide

---

### `embedding_setup.py` — Embedding Model

**What it does:** Returns a LangChain `OpenAIEmbeddings` model connected to SAP Gen AI Hub. Converts text → float vectors.

**Available models:**

| Model | Dimensions | Notes |
|-------|-----------|-------|
| `text-embedding-ada-002` | 1536 | Default, most compatible |
| `text-embedding-3-small` | 1536 | Newer, faster |
| `text-embedding-3-large` | 3072 | Highest quality |

> ⚠️ `VECTOR_DIMENSION` in `.env` and in `vector_table.py` must match your chosen model.

**Run it:**
```bash
python embedding_setup.py
```

**Use in your code:**
```python
from embedding_setup import get_embedding_model

model = get_embedding_model()

vectors = model.embed_documents(["text one", "text two"])  # list of vectors
query_v = model.embed_query("search question")             # single vector
```

---

### `document_loaders.py` — Document Loaders

**What it does:** Loads content from various sources into LangChain `Document` objects. Auto-detects input type.

**Run it:**
```bash
python document_loaders.py
```

**Use in your code:**
```python
from document_loaders import load_documents

# Auto-detect (recommended)
docs = load_documents("./report.pdf")
docs = load_documents("./data.csv", content_columns=["name", "description"])
docs = load_documents("./Sales.xlsx", content_columns=["Product", "Category"])
docs = load_documents("https://help.sap.com/docs/hana-cloud")
docs = load_documents("./notes.txt")
docs = load_documents("Any raw text string goes here.")

# Or call specific loaders directly:
from document_loaders import load_from_pdf, load_from_csv, load_from_url
docs = load_from_pdf("./report.pdf")
docs = load_from_csv("./data.csv", content_columns=["col1"], metadata_columns=["id"])
```

---

### `text_chunker.py` — Text Chunker

**What it does:** Splits documents into smaller chunks so each embedding represents a focused piece of content.

**Tuning guide:**
- `chunk_size=300` → short, precise chunks — good for Q&A
- `chunk_size=500` → balanced (default)
- `chunk_size=1000` → larger context per result — good for summaries
- `chunk_overlap=50` → small overlap prevents losing context at boundaries

**Run it:**
```bash
python text_chunker.py
```

**Use in your code:**
```python
from text_chunker import chunk_documents

chunks = chunk_documents(docs)                          # defaults: 500 size, 50 overlap
chunks = chunk_documents(docs, chunk_size=300, chunk_overlap=30)
print(f"{len(chunks)} chunks created")
```

---

### `vector_table.py` — HANA Vector Table

**What it does:** Creates the HANA table with a `REAL_VECTOR` column. Also clears rows and returns stats.

**Run it:**
```bash
python vector_table.py
```

**Use in your code:**
```python
from vector_table import create_vector_table, clear_vector_table, get_table_stats

create_vector_table(conn, "VECTOR_STORE")      # create (safe to call multiple times)

clear_vector_table(conn, "VECTOR_STORE")                       # delete ALL rows
clear_vector_table(conn, "VECTOR_STORE", source_name="report.pdf")  # delete one source

stats = get_table_stats(conn, "VECTOR_STORE")
# → {"table": "VECTOR_STORE", "total_chunks": 142, "total_sources": 3}
```

---

### `embed_and_store.py` — Embed and Store

**What it does:** Takes chunked Documents, calls the embedding model in batches, and inserts results into HANA using `TO_REAL_VECTOR()`.

**Run it:**
```bash
python embed_and_store.py
```

**Use in your code:**
```python
from embed_and_store import embed_and_store

stored = embed_and_store(conn, chunks, model, table_name="VECTOR_STORE", batch_size=50)
print(f"Stored {stored} chunks")
```

> Reduce `batch_size` (e.g. to 10) if you hit SAP Gen AI Hub rate limits.

---

### `similarity_search.py` — Similarity Search

**What it does:** Embeds your query and runs `COSINE_SIMILARITY` against all stored vectors in HANA. Returns top-K results sorted by score.

**Score guide:**
- `0.9–1.0` → very high relevance
- `0.7–0.9` → good match
- `< 0.7`   → weak match

**Run it:**
```bash
python similarity_search.py
```

**Use in your code:**
```python
from similarity_search import similarity_search

results = similarity_search(conn, "What is the refund policy?", model, top_k=5)

for r in results:
    print(r["rank"], r["score"], r["content"])

# Filter to a specific source
results = similarity_search(conn, "pricing", model, source_filter="catalogue.pdf")
```

---

### `vector_store_agent.py` — Full Pipeline Agent

**What it does:** Wraps all the above into one class. Use this if you don't want to wire the pieces manually.

**Run it:**
```bash
python vector_store_agent.py
```

**Use in your code:**
```python
from connect_env import connect
from vector_store_agent import VectorStoreAgent

conn  = connect()
store = VectorStoreAgent(conn, table_name="VECTOR_STORE")

# Add any source
store.add("./report.pdf")
store.add("./products.csv", content_columns=["name", "description"])
store.add("https://help.sap.com/docs/hana-cloud")
store.add("Some inline text to embed.")

# Re-add a source (replace old vectors)
store.add("./report.pdf", clear_existing=True)

# Search
results = store.search("What is the return policy?", top_k=3)
for r in results:
    print(r["score"], r["content"])

# Stats and cleanup
print(store.get_stats())
store.clear(source_name="old_file.pdf")   # clear one source
store.clear()                              # clear everything

conn.close()
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `EMBEDDING_DEPLOYMENT_ID not set` | Add it to `.env`. Get from SAP AI Launchpad → AI Core → Deployments |
| `REAL_VECTOR dimension mismatch` | `VECTOR_DIMENSION` in `.env` must match the model (1536 for ada-002, 3072 for 3-large). Drop and recreate the table if you changed models |
| `Table already exists` error | `create_vector_table` uses `IF NOT EXISTS` — safe to call repeatedly. If schema changed, run `clear_vector_table` and recreate |
| API rate limit on embedding | Reduce `batch_size` in `embed_and_store.py` (try 10–20) |
| Low search scores (< 0.5) | Content may not be relevant to query, or chunk size is too large — try smaller chunks |
| Import error on `connect_env` | `hana_db_connection/` folder must exist at the same level as `hana_vector_store/` |

---

## How These Files Relate to the Full Template

These mini templates are extracted from `template_03_hana_vector_store/hana_vector_store.py`.  
The original file bundles everything into one large file with a single `HANAVectorStore` class — here each step is isolated so you can use, test, or swap just the part you need.
