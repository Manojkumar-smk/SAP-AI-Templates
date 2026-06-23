# TechCorp AI Assistant — SAP Gen AI Hub Version

Same 4-tab Streamlit app as `sample_project_openai` but uses
**SAP Gen AI Hub** for LLM and embeddings instead of OpenAI direct API.

Use this when you have: SAP AI Core subscription + deployment IDs for a chat model and an embedding model.

---

## Side-by-Side Comparison

| | `sample_project_openai` | `sample_project_sapgenai` |
|---|---|---|
| LLM source | OpenAI API (`langchain_openai`) | SAP Gen AI Hub (`gen_ai_hub.proxy`) |
| Embedding source | OpenAI API (`langchain_openai`) | SAP Gen AI Hub (`gen_ai_hub.proxy`) |
| Key .env vars | `OPENAI_API_KEY` | `LLM_DEPLOYMENT_ID` + `EMBEDDING_DEPLOYMENT_ID` |
| Package | `langchain-openai` | `sap-ai-sdk-gen` |
| Template folders used | `*_openai/` | original (no `_openai` suffix) |

---

## What You'll Learn

| Tab | Template Used | Pattern |
|-----|--------------|---------|
| 🔌 Connection | `hana_db_connection/` | Connect to HANA + test Gen AI Hub |
| 🤖 SQL Assistant | `hana_ai_query/` | NL → SQL → DataFrame via SAP LLM |
| 📚 Document Q&A | `hana_vector_store/` + `hana_rag/` | RAG with SAP embeddings |
| 💬 Full Chatbot | `sap_chatbot/` | Multi-mode chatbot via SAP Gen AI Hub |

---

## Project Structure

```
sample_project_sapgenai/
├── app.py                  ← Main Streamlit app (4 tabs)
├── setup_sample_data.py    ← Run ONCE: creates DB table + embeds FAQ
├── .env.example            ← Copy to .env, fill in credentials
├── requirements.txt
└── USER_MANUAL.md
```

---

## Setup (4 Steps)

### Step 1 — Install
```bash
pip install -r requirements.txt
```

### Step 2 — Configure SAP AI Core

You need two deployments in SAP AI Launchpad:
- **Chat model** — e.g. `gpt-4o-mini` or `gpt-4o`
- **Embedding model** — `text-embedding-ada-002`

Get the deployment IDs from: **AI Launchpad → ML Operations → Deployments**

### Step 3 — Configure `.env`
```bash
cp .env.example .env
```
Fill in:
```
HANA_HOST=your-host.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=YourPassword

LLM_DEPLOYMENT_ID=d1234...       ← from AI Launchpad
EMBEDDING_DEPLOYMENT_ID=e5678... ← from AI Launchpad
AICORE_HOME=~/.aicore
AICORE_PROFILE=default

VECTOR_TABLE_NAME=VECTOR_STORE
```

### Step 4 — Create sample data (once)
```bash
python setup_sample_data.py
```

### Step 5 — Run the app
```bash
streamlit run app.py
```
Open http://localhost:8501

---

## Connection Tab Extra

This version adds a **Test SAP Gen AI Hub** button — it sends a real LLM call
to verify your `LLM_DEPLOYMENT_ID` works before you start the other tabs.

---

## Common Issues

| Problem | Fix |
|---------|-----|
| `LLM_DEPLOYMENT_ID not set` | Add it to `.env` from AI Launchpad |
| `EMBEDDING_DEPLOYMENT_ID not set` | Add it to `.env` from AI Launchpad |
| `get_proxy_client` error | SAP AI Core profile not configured — check `AICORE_HOME` |
| Table not found | Run `python setup_sample_data.py` |
| RAG returns no results | Lower `min_score` slider, or re-run setup |

---

## Learning Note

The code logic is **identical** to `sample_project_openai` — only the LLM/embedding
source changes. This is the whole point of the mini templates: swap one module,
everything else keeps working.
