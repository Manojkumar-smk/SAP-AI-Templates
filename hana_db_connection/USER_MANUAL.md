# HANA DB Connection — User Manual

Mini templates for connecting to SAP HANA Cloud.  
Each file does **one thing only** — pick the one you need.

---

## Folder Structure

```
hana_db_connection/
├── connect_env.py        ← Connect using .env file (local dev)
├── connect_btp_cf.py     ← Connect using BTP Cloud Foundry service
├── connect_hana_ml.py    ← Connect using hana-ml (for ML / DataFrame API)
├── health_check.py       ← Verify HANA is alive (timestamp + version)
├── .env.example          ← Template for your .env file
├── requirements.txt      ← All pip dependencies
└── USER_MANUAL.md        ← This file
```

---

## Quick Decision Guide

| Situation | Use this file |
|-----------|--------------|
| Running on your laptop with credentials in a `.env` file | `connect_env.py` |
| App deployed on SAP BTP (Cloud Foundry) | `connect_btp_cf.py` |
| Need hana-ml DataFrame / PAL / ML functions | `connect_hana_ml.py` |
| Just want to check if HANA is reachable | `health_check.py` |

---

## Setup (One-Time)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file (for local use)
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
HANA_HOST=your-host.hanacloud.ondemand.com
HANA_PORT=443
HANA_USER=DBADMIN
HANA_PASSWORD=YourPassword
HANA_CERTIFICATE=          # leave blank if not needed
```

---

## File-by-File Guide

---

### `connect_env.py` — Local .env Connection

**What it does:** Reads HANA credentials from your `.env` file and opens an `hdbcli` connection.

**When to use:** Local development on your machine.

**Run it:**
```bash
python connect_env.py
```

**Use in your code:**
```python
from connect_env import connect

conn = connect()

cursor = conn.cursor()
cursor.execute("SELECT * FROM MY_TABLE")
rows = cursor.fetchall()

cursor.close()
conn.close()
```

---

### `connect_btp_cf.py` — BTP Cloud Foundry Connection

**What it does:** Reads HANA credentials from `VCAP_SERVICES` (automatically injected by BTP when a HANA service is bound to your app).

**When to use:** Your app is deployed on SAP BTP / Cloud Foundry.

**Before using:**
1. Bind your HANA service: `cf bind-service <your-app> <hana-service-name>`
2. Check your service label: `cf services` → look at the **service** column
3. Update `CF_SERVICE_LABEL` in the file if it's not `"hana"`

**Run it:**
```bash
python connect_btp_cf.py
```

**Use in your code:**
```python
from connect_btp_cf import connect

conn = connect()
# ... same as connect_env usage above
conn.close()
```

---

### `connect_hana_ml.py` — hana-ml ConnectionContext

**What it does:** Opens a `hana_ml.dataframe.ConnectionContext` — required for hana-ml DataFrame operations, PAL (Predictive Analytics Library), and HANA AI functions.

**When to use:** When you need ML features, not just raw SQL.

**Difference from hdbcli:**
- `hdbcli` → raw SQL with cursor (use `connect_env.py`)
- `hana-ml` → DataFrame API, PAL, AutoML, vector store (use this file)

**Run it:**
```bash
python connect_hana_ml.py
```

**Use in your code:**
```python
from connect_hana_ml import connect

cc = connect()

# Run SQL and get a DataFrame
df = cc.sql("SELECT * FROM MY_TABLE").collect()
print(df)

cc.close()
```

---

### `health_check.py` — HANA Health Check

**What it does:** Runs two lightweight queries against HANA:
1. `SELECT CURRENT_UTCTIMESTAMP FROM DUMMY` — confirms DB is alive
2. `SELECT VALUE FROM M_SYSTEM_OVERVIEW WHERE NAME = 'Version'` — gets HANA version

Returns a dict: `{ status, timestamp, version, error }`

**When to use:** To verify your connection is working, or as a startup check in your app.

**Run it (uses `.env` by default):**
```bash
python health_check.py
```

**Switch to BTP CF — edit the import inside the file:**
```python
# from connect_env import connect       ← default
from connect_btp_cf import connect      # ← uncomment for BTP
```

**Use in your code:**
```python
from connect_env import connect
from health_check import health_check

conn   = connect()
result = health_check(conn)

print(result["status"])     # "OK" or "FAILED"
print(result["timestamp"])  # HANA UTC timestamp
print(result["version"])    # HANA version string
print(result["error"])      # None if OK

conn.close()
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `Missing required environment variables` | Check your `.env` file has all four: `HANA_HOST`, `HANA_PORT`, `HANA_USER`, `HANA_PASSWORD` |
| `HANA service 'hana' not found in VCAP_SERVICES` | Change `CF_SERVICE_LABEL` in `connect_btp_cf.py` to match your actual service label (`cf services` to check) |
| `Connection refused` or timeout | Check HANA host/port, and that your IP is allowlisted in HANA Cloud Central |
| `Authentication failed` | Double-check username and password in `.env` |

---

## How These Files Relate to the Full Template

These mini templates are extracted from `template_01_hana_connection/hana_connection.py`.  
The original file auto-detects local vs. BTP — here each scenario is a separate file so you can grab exactly what you need.
