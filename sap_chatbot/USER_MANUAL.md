# SAP Chatbot — User Manual

Mini templates for a fully configurable SAP AI chatbot backed by SAP Gen AI Hub.

**Four modes — mix and match:**

| Mode | What it does |
|------|-------------|
| **GENERAL** | LLM + memory only — no database |
| **RAG** | LLM + HANA Vector search — answers from your documents |
| **SQL** | LLM + HANA SQL — answers from live table data |
| **FULL** | RAG + SQL + memory combined — the most powerful mode |

---

## Folder Structure

```
sap_chatbot/
├── chatbot_config.py    ← All chatbot parameters in one dataclass
├── llm_setup.py         ← Build LLM + embedding model from config
├── prompt_builder.py    ← Dynamic prompt that adapts to active mode
├── rag_retriever.py     ← Fetch context from HANA Vector Store
├── sql_retriever.py     ← Generate + run SQL, return results as text
├── chatbot_core.py      ← SAPChatbot class: chat(), reset(), history
├── chatbot_presets.py   ← One-line factory functions for each mode
├── cli_runner.py        ← Interactive terminal chat loop
├── .env.example         ← Template for your .env file
├── requirements.txt     ← All pip dependencies
└── USER_MANUAL.md       ← This file
```

---

## How the Pieces Fit Together

```
ChatbotConfig  ← all settings in one place
      │
      ├──► llm_setup.py        builds LLM + embedding model
      │
      ├──► rag_retriever.py    fetches relevant chunks from HANA Vector Store
      │         (only if enable_rag = True)
      │
      ├──► sql_retriever.py    generates + runs SQL, returns results
      │         (only if enable_sql = True)
      │
      ├──► prompt_builder.py   builds prompt dynamically for active mode
      │
      └──► chatbot_core.py     SAPChatbot.chat() ties it all together
                │
                └──► cli_runner.py   interactive terminal loop
```

`chatbot_presets.py` wraps this into one-line factory calls.

---

## Quick Decision Guide

| I want to… | Use this file |
|------------|--------------|
| Configure the chatbot (all settings) | `chatbot_config.py` |
| Build LLM / embedding model | `llm_setup.py` |
| Customize the chatbot's prompt | `prompt_builder.py` |
| Add RAG (document search) | `rag_retriever.py` |
| Add SQL (live HANA data) | `sql_retriever.py` |
| Core chatbot class | `chatbot_core.py` |
| One-line chatbot creation | `chatbot_presets.py` |
| Run chatbot in terminal | `cli_runner.py` |

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
EMBEDDING_DEPLOYMENT_ID=your-embedding-deployment-id   # only for RAG mode
VECTOR_TABLE_NAME=VECTOR_STORE                         # only for RAG mode
```

### 3. HANA connection
These files import `connect()` from `../hana_db_connection/connect_env.py`.

---

## File-by-File Guide

---

### `chatbot_config.py` — All Parameters

**What it does:** One dataclass with every chatbot setting. Change here, behaviour changes everywhere.

**Key parameters:**

```python
from chatbot_config import ChatbotConfig

# GENERAL mode
config = ChatbotConfig(
    system_prompt = "You are a helpful SAP Basis assistant.",
    memory_window = 10,        # remember last 10 turns
    temperature   = 0.1,       # low = factual
)

# RAG mode
config = ChatbotConfig(
    enable_rag              = True,
    vector_table            = "VECTOR_STORE",
    rag_top_k               = 5,       # chunks to retrieve
    rag_min_score           = 0.5,     # minimum similarity threshold
    rag_source_filter       = "report.pdf",  # optional: limit to one file
)

# SQL mode
config = ChatbotConfig(
    enable_sql  = True,
    sql_tables  = ["SALES_ORDERS", "CUSTOMERS"],
    sql_schema  = "DBADMIN",   # optional
)

# FULL mode (RAG + SQL)
config = ChatbotConfig(
    enable_rag  = True,
    enable_sql  = True,
    sql_tables  = ["SALES_ORDERS"],
    vector_table = "VECTOR_STORE",
)

print(config.mode())   # → "GENERAL" | "RAG" | "SQL" | "RAG+SQL"
```

---

### `llm_setup.py` — Build Models

**What it does:** Creates LLM and embedding model instances from a ChatbotConfig.

**Use in your code:**
```python
from llm_setup import build_llm, build_embedding_model

llm      = build_llm(config)
embedder = build_embedding_model(config)   # only if enable_rag = True
```

---

### `prompt_builder.py` — Dynamic Prompt

**What it does:** Builds a `ChatPromptTemplate` that includes the right sections based on what's active:
- Always: system prompt + chat history + user message
- If RAG active: `KNOWLEDGE BASE CONTEXT` section
- If SQL active: `DATABASE RESULTS` section

**Customize the chatbot's instructions** by editing `system_prompt` in `ChatbotConfig` — you don't need to touch `prompt_builder.py` for most customizations.

**Use in your code:**
```python
from prompt_builder import build_prompt

prompt = build_prompt(config, has_rag=True, has_sql=False)
chain  = prompt | llm | StrOutputParser()
answer = chain.invoke({"rag_context": ctx, "history": [], "user_message": "..."})
```

---

### `rag_retriever.py` — RAG Retrieval

**What it does:** Fetches top-K chunks from HANA Vector Store and formats them as a context block for the prompt. Requires documents already embedded via `hana_vector_store/`.

**Use in your code:**
```python
from rag_retriever import rag_retrieve

context_text, sources = rag_retrieve(conn, "user question", config, embedder)

# context_text → injected into prompt as {rag_context}
# sources      → cited in the response
for s in sources:
    print(s["source_name"], s["score"])
```

---

### `sql_retriever.py` — SQL Retrieval

**What it does:** Inspects your HANA table schemas, generates SQL from the user's message, executes it, and returns results as readable text for the prompt. Uses `hana_ai_query/` internally.

**Use in your code:**
```python
from sql_retriever import sql_retrieve

sql_result, sql_used = sql_retrieve(conn, "Top 5 customers by revenue", config, llm)

# sql_result → injected into prompt as {sql_result}
# sql_used   → shown in response for transparency
print(sql_used)
print(sql_result)
```

---

### `chatbot_core.py` — SAPChatbot Class

**What it does:** The main chatbot class. Wires all pieces together.

**Use in your code:**
```python
from chatbot_core import SAPChatbot

bot = SAPChatbot(config, conn=conn)

# Chat
response = bot.chat("What is HANA Cloud?")
print(response["answer"])
print(response["mode"])      # "GENERAL" / "RAG" / "SQL" / "RAG+SQL"
print(response["sources"])   # RAG citations
print(response["sql_used"])  # SQL query run
print(response["turn"])      # turn number

# Memory
bot.reset()                  # clear history
bot.get_history()            # list of {"role", "content"} dicts
bot.print_history()          # print to console
bot.get_turn_count()         # int
```

---

### `chatbot_presets.py` — One-Line Factory Functions

**What it does:** Creates a ready `SAPChatbot` in one line for each common mode.

**Use in your code:**
```python
from chatbot_presets import (
    create_general_chatbot,
    create_rag_chatbot,
    create_sql_chatbot,
    create_full_chatbot,
)

# GENERAL
bot = create_general_chatbot(
    system_prompt = "You are a SAP HR assistant.",
    memory_window = 10,
)

# RAG
bot = create_rag_chatbot(
    conn          = conn,
    vector_table  = "VECTOR_STORE",
    rag_min_score = 0.5,
)

# SQL
bot = create_sql_chatbot(
    conn       = conn,
    sql_tables = ["CUST_TICKETS", "PRODUCTS"],
)

# FULL
bot = create_full_chatbot(
    conn         = conn,
    sql_tables   = ["SALES_ORDERS"],
    vector_table = "VECTOR_STORE",
)

# All return a SAPChatbot — call bot.chat("your question")
response = bot.chat("What are the open tickets this week?")
print(response["answer"])
```

---

### `cli_runner.py` — Interactive Terminal Chat

**What it does:** Runs your chatbot in an interactive terminal loop. Best for testing.

**Run it:**
```bash
python cli_runner.py
```

**Terminal commands:**
| Command | Action |
|---------|--------|
| `/reset` | Clear conversation, start fresh |
| `/history` | Print full conversation |
| `/mode` | Show active mode and turn count |
| `/quit` | Exit |

**To switch mode:** Open `cli_runner.py`, comment/uncomment the preset you want.

---

## Mode Comparison

| | GENERAL | RAG | SQL | FULL |
|--|---------|-----|-----|------|
| LLM answer | ✅ | ✅ | ✅ | ✅ |
| Conversation memory | ✅ | ✅ | ✅ | ✅ |
| Answers from documents | ❌ | ✅ | ❌ | ✅ |
| Answers from live DB data | ❌ | ❌ | ✅ | ✅ |
| HANA connection required | ❌ | ✅ | ✅ | ✅ |
| Embedding model required | ❌ | ✅ | ❌ | ✅ |

---

## Common Errors

| Error | Fix |
|-------|-----|
| `LLM_DEPLOYMENT_ID not set` | Add to `.env` (chat model deployment) |
| `EMBEDDING_DEPLOYMENT_ID not set` | Add to `.env` (embedding model deployment — only for RAG) |
| `conn is required when enable_rag or enable_sql is True` | Pass `conn=connect()` to `SAPChatbot()` or preset factory |
| `sql_tables must not be empty` | Add table names to `ChatbotConfig(sql_tables=["TABLE1"])` |
| RAG returns no context | Check `rag_min_score` — try lowering it. Also verify documents are embedded in the vector table |
| SQL returns wrong results | Try a more specific question or use `gpt-4o` for better SQL generation |
| Follow-up questions not resolved | Check `memory_window > 0` in config |

---

## How These Files Relate to the Full Template

These mini templates are extracted from `template_05_sap_chatbot/sap_chatbot.py`.  
The original file bundles everything into one large file — here each piece is isolated so you can grab exactly what you need, test it independently, or build your own chatbot by mixing and matching.
