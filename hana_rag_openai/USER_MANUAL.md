# HANA RAG (OpenAI) — User Manual

Same as `hana_rag/` but uses **OpenAI API directly** for both LLM and embeddings.
Use this while learning with a personal OpenAI API key + SAP BTP Trial HANA.

---

## What Changed vs. `hana_rag/`

| File | Changed? | Why |
|------|----------|-----|
| `llm_setup.py` | ✅ YES | Uses `langchain_openai.ChatOpenAI` + `OPENAI_API_KEY` |
| `rag_agent.py` | ✅ YES | Imports embedding from `hana_vector_store_openai/` |
| `rag_prompts.py` | ❌ No | Pure LangChain templates, no API calls |
| `context_retriever.py` | ❌ No | Takes `embedding_model` as parameter |
| `rag_pipeline.py` | ❌ No | Takes `llm` and `embedding_model` as parameters |
| `conversation_memory.py` | ❌ No | Pure LangChain memory, no API calls |
| `.env.example` | ✅ YES | `OPENAI_API_KEY` instead of deployment IDs |
| `requirements.txt` | ✅ YES | `langchain-openai` instead of `sap-ai-sdk-gen` |

---

## Folder Structure

```
hana_rag_openai/
├── llm_setup.py            ← ✅ CHANGED — OpenAI direct API
├── rag_agent.py            ← ✅ CHANGED — imports from openai vector store
├── rag_prompts.py          ← same
├── context_retriever.py    ← same
├── rag_pipeline.py         ← same
├── conversation_memory.py  ← same
├── .env.example            ← ✅ CHANGED — OPENAI_API_KEY
├── requirements.txt        ← ✅ CHANGED — langchain-openai
└── USER_MANUAL.md
```

---

## Prerequisites

Documents must already be embedded in HANA using **`hana_vector_store_openai/`** — not the SAP Gen AI Hub version. Both must use the same embedding model so similarity scores are meaningful.

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
```

---

## Quick Start

```python
from connect_env import connect          # from hana_db_connection/
from rag_agent import RAGAgent

conn  = connect()
agent = RAGAgent(conn, table_name="VECTOR_STORE", top_k=5, min_score=0.5)

# One-shot
result = agent.ask("What is SAP HANA Cloud?")
print(result["answer"])

# Multi-turn
agent.chat("What are the key features?")
agent.chat("How does vector search work in that context?")

conn.close()
```

---

## Learning Note

This folder and `hana_vector_store_openai/` must use the **same embedding model**.
If you embed documents with `text-embedding-3-small`, also search with `text-embedding-3-small`.

For full file-by-file details, see `hana_rag/USER_MANUAL.md` — the API is identical, only the LLM/embedding source changes.
