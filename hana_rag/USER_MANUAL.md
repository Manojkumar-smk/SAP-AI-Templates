# HANA RAG — User Manual

Mini templates for Retrieval-Augmented Generation (RAG) on SAP HANA Cloud.

**What is RAG?**  
Instead of relying on an LLM's general knowledge, RAG first *retrieves* relevant text chunks from your own documents (stored in HANA Vector Store), then *generates* an answer grounded only in that context. This eliminates hallucinations and gives you cited sources for every answer.

---

## Folder Structure

```
hana_rag/
├── llm_setup.py            ← LLM for answer generation (SAP Gen AI Hub)
├── rag_prompts.py          ← Prompt templates (standard, conversational, structured)
├── context_retriever.py    ← Fetch top-K chunks from HANA + format into context block
├── rag_pipeline.py         ← Single-turn RAG: query → retrieve → answer + sources
├── conversation_memory.py  ← Rolling chat memory for multi-turn conversations
├── rag_agent.py            ← Full agent: ask() + chat() + clear_memory()
├── .env.example            ← Template for your .env file
├── requirements.txt        ← All pip dependencies
└── USER_MANUAL.md          ← This file
```

---

## How the Pieces Fit Together

```
User Question
      │
      ▼
context_retriever.py  ←── HANA Vector Store (hana_vector_store/)
      │  top-K chunks
      ▼
rag_prompts.py        ←── injects context + question into prompt template
      │
      ▼
llm_setup.py          ←── LLM generates a grounded answer
      │
      ▼
Answer + Source Citations
      │
      ▼ (multi-turn only)
conversation_memory.py ←── saves turn, injects history into next prompt
```

`rag_agent.py` wires all of this together — use it when you don't want to manage the pieces manually.

---

## Prerequisites

This folder **depends on** `hana_vector_store/` — your documents must already be embedded and stored in HANA before you can do RAG. If you haven't done that yet:

1. Set up `hana_db_connection/` first
2. Then use `hana_vector_store/vector_store_agent.py` to load and embed your documents
3. Then use this folder for RAG queries

---

## Quick Decision Guide

| I want to… | Use this file |
|------------|--------------|
| Just set up the chat LLM | `llm_setup.py` |
| Customize how the LLM is prompted | `rag_prompts.py` |
| Retrieve and format context chunks from HANA | `context_retriever.py` |
| One-shot RAG (no conversation history) | `rag_pipeline.py` |
| Manage rolling conversation memory | `conversation_memory.py` |
| Full pipeline: single-turn + multi-turn in one class | `rag_agent.py` |

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

LLM_DEPLOYMENT_ID=your-llm-deployment-id
EMBEDDING_DEPLOYMENT_ID=your-embedding-deployment-id

VECTOR_TABLE_NAME=VECTOR_STORE
```

> **Two deployment IDs needed:**
> - `LLM_DEPLOYMENT_ID` → your chat model (e.g. gpt-4o-mini deployment)
> - `EMBEDDING_DEPLOYMENT_ID` → your embedding model (e.g. text-embedding-ada-002 deployment)
>
> Both found at: SAP AI Launchpad → AI Core → Deployments

---

## File-by-File Guide

---

### `llm_setup.py` — Chat LLM

**What it does:** Returns a LangChain `ChatOpenAI` via SAP Gen AI Hub for generating answers.

**Run it:**
```bash
python llm_setup.py
```

**Use in your code:**
```python
from llm_setup import get_llm

llm = get_llm()                          # default: gpt-4o-mini, temperature=0.1
llm = get_llm(model="gpt-4o")           # higher quality
llm = get_llm(temperature=0.0)          # fully deterministic
```

> For RAG, keep `temperature` low (0.0–0.2) to get factual, grounded answers.

---

### `rag_prompts.py` — Prompt Templates

**What it does:** Provides three ready-made prompt templates. Swap them to change the LLM's behavior.

| Prompt | Use when |
|--------|----------|
| `RAG_PROMPT` | Standard single-turn Q&A |
| `CONVERSATIONAL_RAG_PROMPT` | Multi-turn with `{chat_history}` |
| `STRUCTURED_RAG_PROMPT` | Want bullet-point formatted answers |

**Use in your code:**
```python
from rag_prompts import RAG_PROMPT, CONVERSATIONAL_RAG_PROMPT, STRUCTURED_RAG_PROMPT
from langchain_core.output_parsers import StrOutputParser

chain  = RAG_PROMPT | llm | StrOutputParser()
answer = chain.invoke({"context": context_str, "user_query": "your question"})
```

**Customize the prompt** by editing the template string inside `rag_prompts.py` — change the language, tone, output format, or add domain-specific rules.

---

### `context_retriever.py` — Context Retriever

**What it does:** Fetches the most relevant chunks from HANA and formats them into a numbered context block for the prompt.

**Run it:**
```bash
python context_retriever.py
```

**Use in your code:**
```python
from context_retriever import retrieve_context, format_context

# Retrieve
chunks = retrieve_context(
    conn, "your question", embedding_model,
    table_name="VECTOR_STORE",
    top_k=5,
    source_filter="report.pdf",  # optional: limit to one document
    min_score=0.5,               # optional: only high-confidence chunks
)

# Format into a string for the prompt
context = format_context(chunks)
print(context)
# [1] Source: report.pdf (chunk 3)
# SAP HANA Cloud supports...
#
# [2] Source: report.pdf (chunk 7)
# The Vector Engine uses REAL_VECTOR...
```

**Tuning `min_score`:**
- `0.0` → include all retrieved chunks (no filter)
- `0.5` → only fairly relevant chunks
- `0.7` → only highly relevant chunks (fewer but more precise)

---

### `rag_pipeline.py` — Single-Turn RAG

**What it does:** The complete one-shot pipeline: question → retrieve → generate → return answer + sources.

**Run it:**
```bash
python rag_pipeline.py
```

**Use in your code:**
```python
from rag_pipeline import rag_query

result = rag_query(
    conn=conn,
    user_query="What is the refund policy?",
    embedding_model=model,
    llm=llm,
    table_name="VECTOR_STORE",
    top_k=5,
    min_score=0.5,
)

print(result["answer"])    # LLM's grounded answer
print(result["sources"])   # which documents were cited
print(result["context"])   # full context block fed to the LLM
```

**Swap the prompt:**
```python
from rag_prompts import STRUCTURED_RAG_PROMPT

result = rag_query(..., prompt=STRUCTURED_RAG_PROMPT)
```

---

### `conversation_memory.py` — Conversation Memory

**What it does:** Stores recent conversation turns and provides them as a formatted string for the `{chat_history}` slot in `CONVERSATIONAL_RAG_PROMPT`.

**Run it:**
```bash
python conversation_memory.py
```

**Use in your code:**
```python
from conversation_memory import ChatMemory

memory = ChatMemory(window=5)   # keep last 5 turns

# After each RAG response, save the turn
memory.save(user_question, llm_answer)

# Before the next LLM call, get the history
history_str = memory.get_history_string()
# → "User: What is HANA?\nAssistant: SAP HANA is...\nUser: ..."

# Start a new conversation
memory.clear()

# Check how many turns are stored
print(memory.turn_count())
```

---

### `rag_agent.py` — Full RAG Agent

**What it does:** Combines all pieces into one class. Use `ask()` for single-turn, `chat()` for multi-turn.

**Run it:**
```bash
python rag_agent.py
```

**Use in your code:**
```python
from connect_env import connect
from rag_agent import RAGAgent

conn  = connect()
agent = RAGAgent(
    conn=conn,
    table_name="VECTOR_STORE",
    top_k=5,
    min_score=0.5,        # filter low-relevance chunks
    memory_window=5,      # remember last 5 turns
)

# ── Single-turn (no history) ─────────────────────────────
result = agent.ask("What is SAP HANA Cloud?")
print(result["answer"])
for s in result["sources"]:
    print(f"  [{s['rank']}] {s['source_name']} | {s['score']}")

# ── Multi-turn conversation ──────────────────────────────
r1 = agent.chat("What are the features of HANA Vector Engine?")
r2 = agent.chat("How does cosine similarity work in that context?")
r3 = agent.chat("Give me a summary of what we discussed.")

print(agent.get_history())   # see the full conversation so far

agent.clear_memory()         # start fresh

# ── Filter to a specific document ───────────────────────
result = agent.ask("Main points?", source_filter="report.pdf", top_k=3)
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `LLM_DEPLOYMENT_ID not set` | Add to `.env`. Get from SAP AI Launchpad → AI Core → Deployments (chat model) |
| `EMBEDDING_DEPLOYMENT_ID not set` | Add to `.env`. Get from Deployments (embedding model) |
| `"I don't have enough information"` always returned | Chunks in HANA may not match your query — check `min_score` (lower it) or verify documents were embedded with the same model |
| Low-quality answers | Try `model="gpt-4o"` in `get_llm()`, increase `top_k`, or lower `min_score` |
| Follow-up questions not resolved | Make sure you're using `agent.chat()` not `agent.ask()` — only `chat()` uses memory |
| Import error on `similarity_search` or `embedding_setup` | `hana_vector_store/` folder must exist at the same level as `hana_rag/` |

---

## How These Files Relate to the Full Template

These mini templates are extracted from `template_04_hana_rag/hana_rag.py`.  
The original bundles everything into one large file with a single `HANARagAgent` class — here each step is isolated so you can pick, test, or customize just the part you need.
