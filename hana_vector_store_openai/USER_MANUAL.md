# HANA Vector Store (OpenAI) — User Manual

Same as `hana_vector_store/` but uses **OpenAI API directly** for embeddings.
Use this while learning with a personal OpenAI API key + SAP BTP Trial HANA.

---

## What Changed vs. `hana_vector_store/`

| File | Changed? | Why |
|------|----------|-----|
| `embedding_setup.py` | ✅ YES | Uses `langchain_openai.OpenAIEmbeddings` + `OPENAI_API_KEY` |
| `document_loaders.py` | ❌ No | No embedding involved |
| `text_chunker.py` | ❌ No | No embedding involved |
| `vector_table.py` | ❌ No | Pure HANA SQL |
| `embed_and_store.py` | ❌ No | Takes `embedding_model` as parameter |
| `similarity_search.py` | ❌ No | Takes `embedding_model` as parameter |
| `vector_store_agent.py` | ❌ No | Imports local `embedding_setup` → picks up OpenAI version |
| `.env.example` | ✅ YES | `OPENAI_API_KEY` instead of `EMBEDDING_DEPLOYMENT_ID` |
| `requirements.txt` | ✅ YES | `langchain-openai` instead of `sap-ai-sdk-gen` |

---

## Folder Structure

```
hana_vector_store_openai/
├── embedding_setup.py      ← ✅ CHANGED — OpenAI direct API
├── document_loaders.py     ← same
├── text_chunker.py         ← same
├── vector_table.py         ← same
├── embed_and_store.py      ← same (takes embedding_model as param)
├── similarity_search.py    ← same (takes embedding_model as param)
├── vector_store_agent.py   ← same (imports local embedding_setup)
├── .env.example            ← ✅ CHANGED — OPENAI_API_KEY
├── requirements.txt        ← ✅ CHANGED — langchain-openai
└── USER_MANUAL.md
```

---

## Setup

### 1. Install
```bash
pip install -r requirements.txt
```

### 2. Create `.env`
```bash
cp .env.example .env
```
Fill in:
```
HANA_HOST=your-host.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=YourPassword

OPENAI_API_KEY=sk-...
VECTOR_TABLE_NAME=VECTOR_STORE
VECTOR_DIMENSION=1536
```

---

## Quick Start

```python
from connect_env import connect          # from hana_db_connection/
from vector_store_agent import VectorStoreAgent

conn  = connect()
store = VectorStoreAgent(conn, table_name="VECTOR_STORE")

# Add content
store.add("SAP HANA Cloud supports vector search natively.")
store.add("./data/report.pdf")

# Search
results = store.search("What is HANA Cloud?", top_k=3)
for r in results:
    print(r["score"], r["content"])

conn.close()
```

---

## Embedding Model Options

| Model | Dimensions | Cost | Notes |
|-------|-----------|------|-------|
| `text-embedding-3-small` | 1536 | Low | Default — best for learning |
| `text-embedding-3-large` | 3072 | Medium | Higher quality |
| `text-embedding-ada-002` | 1536 | Low | Legacy, still works |

Change in `embedding_setup.py`:
```python
EMBEDDING_MODEL  = "text-embedding-3-small"   # change here
VECTOR_DIMENSION = 1536                        # change to match
```

> ⚠️ If you change the model, drop and recreate the HANA vector table — dimension must match.

---

For full file-by-file details, see `hana_vector_store/USER_MANUAL.md` — the API is identical, only the embedding source changes.
