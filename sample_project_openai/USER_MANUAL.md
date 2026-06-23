# TechCorp AI Assistant — Sample Project

A complete working Streamlit app that demonstrates all 4 OpenAI template modules
in one place. Built for learning: one screen, four tabs, each showing a different AI pattern.

---

## What You'll Learn

| Tab | Template Used | Pattern |
|-----|--------------|---------|
| 🔌 Connection | `hana_db_connection/` | Connect to HANA, health check, view data |
| 🤖 SQL Assistant | `hana_ai_query_openai/` | Natural language → SQL → DataFrame |
| 📚 Document Q&A | `hana_vector_store_openai/` + `hana_rag_openai/` | RAG with citations |
| 💬 Full Chatbot | `sap_chatbot_openai/` | Multi-mode chatbot with memory |

---

## Project Structure

```
sample_project/
├── app.py                  ← Main Streamlit app (4 tabs)
├── setup_sample_data.py    ← Run ONCE: creates DB table + embeds FAQ
├── .env.example            ← Copy to .env, fill in credentials
├── requirements.txt
└── USER_MANUAL.md
```

---

## Setup (3 Steps)

### Step 1 — Install
```bash
pip install -r requirements.txt
```

### Step 2 — Configure `.env`
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

### Step 3 — Create sample data (once)
```bash
python setup_sample_data.py
```
This creates:
- `SAMPLE_EMPLOYEES` table with 10 employee rows (for SQL tab)
- Company FAQ document embedded in `VECTOR_STORE` (for RAG tab)

### Step 4 — Run the app
```bash
streamlit run app.py
```
Open http://localhost:8501

---

## Sample Data

### SAMPLE_EMPLOYEES table
| ID | Name | Department | Role | Salary | Location |
|----|------|-----------|------|--------|----------|
| 1 | Alice Johnson | Engineering | Senior Developer | 95,000 | Bangalore |
| 2 | Bob Smith | Engineering | Junior Developer | 55,000 | Hyderabad |
| 3 | Carol White | HR | HR Manager | 75,000 | Mumbai |
| ... | | | | | |

### Company FAQ document
Topics covered: Work From Home Policy, Leave Policy, Performance Reviews,
Salary & Bonus, Benefits, Onboarding, Travel Policy, IT Security.

---

## Tab-by-Tab Guide

### 🔌 Connection Tab
- Click **Test Connection** to verify HANA credentials
- Shows **Show SAMPLE_EMPLOYEES** — view all 10 employee rows
- Shows **Vector Store stats** — number of chunks embedded

### 🤖 SQL Assistant Tab
- Pick an example question or type your own
- The AI generates SQL → runs it → shows results as a table
- Also gives an AI summary of the data
- Great for learning how NL→SQL works

### 📚 Document Q&A Tab
- Ask anything about the company FAQ document
- Adjust **top_k** (how many chunks to retrieve) and **min score** (similarity threshold)
- See **Sources** — which chunks were used to build the answer
- See **Raw context** — exact text sent to the LLM

### 💬 Full Chatbot Tab
Choose a mode:
- **GENERAL** — plain chatbot, nothing loaded from HANA
- **RAG** — every message first searches the company FAQ
- **SQL** — every message can trigger a HANA SQL query
- **FULL** — both RAG + SQL enabled simultaneously

Memory is maintained across turns. Use **Reset conversation** to start fresh.

---

## OpenAI Models Used

| Model | Purpose | Cost |
|-------|---------|------|
| `gpt-4o-mini` | LLM for SQL, RAG answers, chatbot | Very low |
| `text-embedding-3-small` | Document embedding for vector store | Very low |

---

## Common Issues

| Problem | Fix |
|---------|-----|
| "Table SAMPLE_EMPLOYEES not found" | Run `python setup_sample_data.py` |
| "OPENAI_API_KEY not set" | Add `OPENAI_API_KEY=sk-...` to `.env` |
| "Connection failed" | Check HANA_HOST / HANA_PASSWORD in `.env` |
| RAG returns no results | Run setup_sample_data.py, or lower `min_score` slider |
