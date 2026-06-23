# HANA AI Query — User Manual

Mini templates for building an AI-powered SQL query agent on SAP HANA Cloud.  
Ask questions in plain English → AI generates SQL → HANA runs it → you get a DataFrame.

---

## Folder Structure

```
hana_ai_query/
├── llm_setup.py            ← Connect to LLM via SAP Gen AI Hub
├── schema_inspector.py     ← Fetch HANA table schema for AI context
├── sql_generator.py        ← Convert plain English question → SQL (AI)
├── sql_executor.py         ← Run SQL safely on HANA → DataFrame
├── query_agent.py          ← Full pipeline in one agent.ask() call
├── query_with_summary.py   ← Query + AI plain English summary of results
├── .env.example            ← Template for your .env file
├── requirements.txt        ← All pip dependencies
└── USER_MANUAL.md          ← This file
```

---

## How the Pieces Fit Together

```
Your Question (plain English)
        │
        ▼
schema_inspector.py   ←  reads your HANA table columns
        │
        ▼
sql_generator.py      ←  LLM generates a SELECT query
        │
        ▼
sql_executor.py       ←  runs the query on HANA
        │
        ▼
   pandas DataFrame
        │
        ▼ (optional)
query_with_summary.py ←  LLM summarizes the result in plain English
```

`query_agent.py` wires all of this together — use it when you don't want to manage the pieces manually.

---

## Quick Decision Guide

| I want to… | Use this file |
|------------|--------------|
| Just set up the LLM connection | `llm_setup.py` |
| Just inspect a HANA table's columns | `schema_inspector.py` |
| Generate SQL from a question (no execution) | `sql_generator.py` |
| Run a SQL string and get a DataFrame | `sql_executor.py` |
| Full pipeline: question → DataFrame | `query_agent.py` |
| Full pipeline + plain English answer | `query_with_summary.py` |

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
HANA_CERTIFICATE=

LLM_DEPLOYMENT_ID=your-deployment-id-here
```

> **Where to get `LLM_DEPLOYMENT_ID`:**  
> SAP AI Launchpad → AI Core → Deployments → copy the ID of your deployed model.

### 3. HANA connection
These files import `connect()` from `../hana_db_connection/connect_env.py`.  
Make sure you've set up that folder first (see `hana_db_connection/USER_MANUAL.md`).

---

## File-by-File Guide

---

### `llm_setup.py` — LLM via SAP Gen AI Hub

**What it does:** Returns a LangChain-compatible `ChatOpenAI` LLM instance connected to SAP AI Core via the Gen AI Hub proxy.

**Available models:**

| Model | Speed | Quality |
|-------|-------|---------|
| `gpt-4o-mini` | Fast | Good (default) |
| `gpt-4o` | Medium | Better |
| `gpt-4` | Slower | Best |

**Run it:**
```bash
python llm_setup.py
```

**Use in your code:**
```python
from llm_setup import get_llm

llm = get_llm()                          # default: gpt-4o-mini
llm = get_llm(model="gpt-4o")           # higher quality
llm = get_llm(temperature=0.7)          # more creative responses
```

---

### `schema_inspector.py` — Table Schema Fetcher

**What it does:** Queries `SYS.COLUMNS` in HANA to get column names and data types, then formats them into a string the LLM can read.

**Run it:**
```bash
python schema_inspector.py
```

**Use in your code:**
```python
from schema_inspector import get_table_schema, build_schema_context

# Single table
info = get_table_schema(conn, "SALES_ORDERS")
# Returns: {"table": "SALES_ORDERS", "schema": "DBADMIN", "columns": [...]}

# Multiple tables → formatted string for AI prompt
schema_context = build_schema_context(conn, ["SALES_ORDERS", "CUSTOMERS"])

# With explicit schema
schema_context = build_schema_context(conn, [
    {"table": "SALES_ORDERS", "schema": "DBADMIN"},
    {"table": "CUSTOMERS",    "schema": "DBADMIN"},
])
```

---

### `sql_generator.py` — Natural Language → SQL

**What it does:** Sends your question + schema context to the LLM and returns a clean HANA SQL SELECT string.

**Run it:**
```bash
python sql_generator.py
```

**Use in your code:**
```python
from sql_generator import generate_sql

sql = generate_sql(
    user_query     = "Show me the top 5 customers by total order value",
    schema_context = schema_context,   # from schema_inspector
    llm            = llm,              # from llm_setup
)
print(sql)
# → SELECT CUSTOMER_NAME, SUM(ORDER_VALUE) AS TOTAL ...
```

**Safety:** The LLM is instructed to generate SELECT only. `sql_executor.py` adds a second guard.

---

### `sql_executor.py` — Safe SQL Execution

**What it does:** Runs a SQL SELECT on HANA and returns a pandas DataFrame. Rejects any non-SELECT statement before touching the DB.

**Run it:**
```bash
python sql_executor.py
```

**Use in your code:**
```python
from sql_executor import execute_sql

df = execute_sql(conn, "SELECT TOP 10 * FROM SALES_ORDERS")
print(df)
```

**Safety guard:**
```python
execute_sql(conn, "DROP TABLE SALES_ORDERS")
# → raises ValueError: Only SELECT queries are allowed. Got: 'DROP'
```

---

### `query_agent.py` — Full Pipeline Agent

**What it does:** Combines `llm_setup` + `schema_inspector` + `sql_generator` + `sql_executor` into one `agent.ask()` call.

**Run it:**
```bash
python query_agent.py
```

**Use in your code:**
```python
from connect_env import connect
from query_agent import QueryAgent

conn  = connect()
agent = QueryAgent(conn, tables=["SALES_ORDERS", "CUSTOMERS"])

# Ask anything in plain English
df = agent.ask("Which customers placed more than 10 orders last month?")
print(df)

# Debug: see what schema context the agent is using
print(agent.get_schema())

conn.close()
```

**With explicit schema:**
```python
agent = QueryAgent(conn, tables=[
    {"table": "SALES_ORDERS", "schema": "DBADMIN"},
    {"table": "CUSTOMERS",    "schema": "DBADMIN"},
])
```

---

### `query_with_summary.py` — Query + AI Summary

**What it does:** Runs the full pipeline AND asks the LLM to summarize the results in plain English — no SQL or technical jargon in the answer.

**Run it:**
```bash
python query_with_summary.py
```

**Use in your code:**
```python
from connect_env import connect
from query_with_summary import ask_with_summary

conn   = connect()
result = ask_with_summary(
    conn       = conn,
    tables     = ["CUST_TICKETS"],
    user_query = "How many tickets are there per category?",
)

print(result["sql"])      # the generated SELECT
print(result["data"])     # pandas DataFrame
print(result["summary"])  # plain English answer, e.g.:
                          # "There are 3 ticket categories. 'Bug' has the most
                          #  with 142 tickets, followed by 'Feature Request' (89)..."
conn.close()
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `LLM_DEPLOYMENT_ID not set` | Add it to `.env`. Get it from SAP AI Launchpad → AI Core → Deployments |
| `No columns found for table 'X'` | Table name is wrong or it's in a different schema — pass `{"table": "X", "schema": "YOUR_SCHEMA"}` |
| `SQL execution failed` | The LLM generated invalid SQL — try a more specific question, or use `gpt-4o` for better SQL quality |
| `Only SELECT queries are allowed` | The LLM tried to generate a non-SELECT — the safety guard blocked it. Rephrase as a read-only question |
| Import error on `connect_env` | Make sure `hana_db_connection/` folder exists at the same level as `hana_ai_query/` |

---

## How These Files Relate to the Full Template

These mini templates are extracted from `template_02_hana_ai_query/hana_ai_query.py`.  
The original file bundles everything into one large file — here each piece is isolated so you can use, test, or swap just the part you need.
