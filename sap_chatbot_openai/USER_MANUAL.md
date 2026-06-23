# SAP Chatbot (OpenAI) — User Manual

Same as `sap_chatbot/` but uses **OpenAI API directly** for LLM and embeddings.
Use this while learning with a personal OpenAI API key + SAP BTP Trial HANA.

---

## What Changed vs. `sap_chatbot/`

| File | Changed? | Why |
|------|----------|-----|
| `chatbot_config.py` | ✅ YES | Removed `llm_deployment_id` / `embedding_deployment_id`; OPENAI_API_KEY only |
| `llm_setup.py` | ✅ YES | `langchain_openai.ChatOpenAI` + `OpenAIEmbeddings` |
| `chatbot_core.py` | ✅ YES | `sys.path` → `hana_vector_store_openai/` (OpenAI embeddings) |
| `prompt_builder.py` | ❌ No | Pure LangChain, no API calls |
| `rag_retriever.py` | ❌ No | Takes `embedding_model` as parameter |
| `sql_retriever.py` | ❌ No | Takes `llm` as parameter |
| `chatbot_presets.py` | ❌ No | Builds config only, no direct API calls |
| `cli_runner.py` | ❌ No | Pure CLI I/O logic |
| `.env.example` | ✅ YES | `OPENAI_API_KEY` instead of deployment IDs |
| `requirements.txt` | ✅ YES | `langchain-openai` instead of `sap-ai-sdk-gen` |

---

## Folder Structure

```
sap_chatbot_openai/
├── chatbot_config.py   ← ✅ CHANGED — OpenAI model names, no deployment IDs
├── llm_setup.py        ← ✅ CHANGED — OpenAI direct API
├── chatbot_core.py     ← ✅ CHANGED — imports from openai vector store
├── prompt_builder.py   ← same
├── rag_retriever.py    ← same
├── sql_retriever.py    ← same
├── chatbot_presets.py  ← same
├── cli_runner.py       ← same
├── .env.example        ← ✅ CHANGED — OPENAI_API_KEY
├── requirements.txt    ← ✅ CHANGED — langchain-openai
└── USER_MANUAL.md
```

---

## Prerequisites

- **SAP BTP Trial HANA** — for database connectivity
- **OpenAI API key** — from [platform.openai.com](https://platform.openai.com)
- If using **RAG mode**: documents must be embedded with `hana_vector_store_openai/` first

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
Fill in your values:
```
HANA_HOST=your-host.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=YourPassword

OPENAI_API_KEY=sk-...

# Only if enable_rag=True:
VECTOR_TABLE_NAME=VECTOR_STORE
```

---

## Quick Start

### GENERAL mode (plain chatbot)
```python
from connect_env import connect          # from hana_db_connection/
from chatbot_config import ChatbotConfig
from chatbot_core import SAPChatbot

conn   = connect()
config = ChatbotConfig(llm_model="gpt-4o-mini")
bot    = SAPChatbot(conn, config)

result = bot.chat("What is SAP HANA Cloud?")
print(result["answer"])
```

### RAG mode (document Q&A)
```python
# First embed your docs using hana_vector_store_openai/

config = ChatbotConfig(enable_rag=True, vector_table="VECTOR_STORE")
bot    = SAPChatbot(conn, config)

result = bot.chat("What does the document say about pricing?")
print(result["answer"])
for s in result["sources"]:
    print(f"  Source: {s['source_name']}")
```

### SQL mode (structured data Q&A)
```python
config = ChatbotConfig(enable_sql=True, sql_tables=["SALES_ORDERS", "PRODUCTS"])
bot    = SAPChatbot(conn, config)

result = bot.chat("What were total sales last month?")
print(result["answer"])
print(f"SQL used: {result['sql_used']}")
```

### FULL mode (RAG + SQL combined)
```python
config = ChatbotConfig(
    enable_rag=True,  vector_table="VECTOR_STORE",
    enable_sql=True,  sql_tables=["SALES_ORDERS"],
)
bot = SAPChatbot(conn, config)
```

### Using presets
```python
from chatbot_presets import create_general_chatbot, create_rag_chatbot
from chatbot_core import SAPChatbot

config = create_rag_chatbot()            # preconfigured ChatbotConfig
bot    = SAPChatbot(conn, config)
```

### CLI runner
```python
from chatbot_presets import create_general_chatbot
from chatbot_core import SAPChatbot
from cli_runner import run_cli

conn   = connect()
config = create_general_chatbot()
bot    = SAPChatbot(conn, config)
run_cli(bot)   # /reset, /history, /mode, /quit commands
```

---

## Multi-turn Conversation

```python
bot.chat("What is SAP HANA?")
bot.chat("How does vector search work in it?")   # follows up with memory
bot.chat("What about pricing?")

bot.print_history()   # see full conversation
bot.reset()           # start fresh
```

---

## OpenAI Model Options

| Model | Speed | Cost | Best for |
|-------|-------|------|----------|
| `gpt-4o-mini` | Fast | Low | Learning, testing (default) |
| `gpt-4o` | Medium | Medium | Production quality |
| `gpt-4-turbo` | Medium | Higher | Complex reasoning |

Embedding model: `text-embedding-3-small` (default, cheap) or `text-embedding-3-large` (better quality).

---

## Learning Notes

- This folder + `hana_vector_store_openai/` must use the **same embedding model**.
  If you embed with `text-embedding-3-small`, also search with `text-embedding-3-small`.
- For full file-by-file details, see `sap_chatbot/USER_MANUAL.md` — the API is identical,
  only the LLM/embedding source changes.
