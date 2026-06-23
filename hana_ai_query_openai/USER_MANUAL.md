# HANA AI Query (OpenAI) — User Manual

Same as `hana_ai_query/` but uses **OpenAI API directly** instead of SAP Gen AI Hub.
Use this while learning with a personal OpenAI API key + SAP BTP Trial HANA.

---

## What Changed vs. `hana_ai_query/`

| File | Changed? | Why |
|------|----------|-----|
| `llm_setup.py` | ✅ YES | Uses `langchain_openai.ChatOpenAI` + `OPENAI_API_KEY` |
| `schema_inspector.py` | ❌ No | No LLM involved |
| `sql_generator.py` | ❌ No | Takes `llm` as parameter |
| `sql_executor.py` | ❌ No | Pure HANA SQL, no LLM |
| `query_agent.py` | ❌ No | Imports local `llm_setup` → picks up OpenAI version |
| `query_with_summary.py` | ❌ No | Same — imports local `llm_setup` |
| `.env.example` | ✅ YES | `OPENAI_API_KEY` instead of `LLM_DEPLOYMENT_ID` |
| `requirements.txt` | ✅ YES | `langchain-openai` instead of `sap-ai-sdk-gen` |

---

## Folder Structure

```
hana_ai_query_openai/
├── llm_setup.py            ← ✅ CHANGED — OpenAI direct API
├── schema_inspector.py     ← same
├── sql_generator.py        ← same
├── sql_executor.py         ← same
├── query_agent.py          ← same (imports local llm_setup)
├── query_with_summary.py   ← same (imports local llm_setup)
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
```

> **Get your OpenAI API key:** platform.openai.com → API Keys → Create new secret key

---

## Quick Start

```python
from connect_env import connect          # from hana_db_connection/
from llm_setup import get_llm
from query_agent import QueryAgent

conn  = connect()
agent = QueryAgent(conn, tables=["YOUR_TABLE"])

df = agent.ask("Show me the top 5 rows")
print(df)
conn.close()
```

---

## Model Options

| Model | Speed | Cost | Notes |
|-------|-------|------|-------|
| `gpt-4o-mini` | Fast | Low | Default — good for learning |
| `gpt-4o` | Medium | Medium | Better SQL quality |
| `gpt-4-turbo` | Slower | Higher | Best quality |

```python
llm = get_llm(model="gpt-4o")       # higher quality
llm = get_llm(model="gpt-4o-mini")  # cheaper for testing
```

---

For full file-by-file details, see `hana_ai_query/USER_MANUAL.md` — the API is identical, only the LLM source changes.
