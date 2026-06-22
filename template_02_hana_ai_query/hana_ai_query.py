"""
============================================================
TEMPLATE 02 — SAP HANA Cloud: AI-Powered SQL Query Agent
============================================================
Takes a natural language question from the user, auto-discovers
the HANA table schema, uses an LLM to generate a SELECT query,
executes it, and returns the result as a pandas DataFrame.

Inputs:
  - conn        : hdbcli Connection       (from template_01 hana_connection.py)
  - conn_ctx    : hana_ml ConnectionContext (from template_01 hana_connection.py)
  - user_query  : str — plain English question e.g. "Show top 5 customers by revenue"
  - tables      : list of table names to give as context to the AI

Dependencies:
    pip install hdbcli hana-ml cfenv python-dotenv sap-ai-sdk-gen
                langchain langchain-core langchain-openai pandas tabulate

Usage:
    python hana_ai_query.py
============================================================
"""

import os
import re
import logging
import pandas as pd
from dotenv import load_dotenv

# ── LLM imports (SAP Gen AI Hub — swap section if using OpenAI directly) ──
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── HANA connection  ──────────────────────────────────────────────────────
# Import the connection helpers from Template 01.
# Adjust the import path if this file lives in a different folder.
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "template_01_hana_connection"))
from hana_connection import get_hana_credentials, get_dbapi_connection, get_hana_ml_connection

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. LLM SETUP  (SAP Gen AI Hub)
# ─────────────────────────────────────────────
def get_llm():
    """
    Returns a LangChain-compatible LLM via SAP Gen AI Hub.

    Supported models via SAP Gen AI Hub:
      "gpt-4o-mini"   — fast, cost-efficient (default)
      "gpt-4o"        — higher quality
      "gpt-4"         — maximum quality
    Change proxy_model_name below to switch models.
    """
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID not set.\n"
            "Add it to your .env file. Get the ID from SAP AI Core deployments."
        )

    proxy_client = get_proxy_client("gen-ai-hub")

    llm = ChatOpenAI(
        proxy_model_name="gpt-4o-mini",   # ← change model here if needed
        proxy_client=proxy_client,
        deployment_id=deployment_id,
        temperature=0,                    # keep at 0 for deterministic SQL
    )
    log.info("LLM ready: gpt-4o-mini via SAP Gen AI Hub")
    return llm


# ─────────────────────────────────────────────
# 2. SCHEMA INSPECTOR
# ─────────────────────────────────────────────
def get_table_schema(conn, table_name: str, schema_name: str = None) -> dict:
    """
    Fetches column names and data types for a HANA table from SYS.COLUMNS.

    Args:
        conn        : hdbcli Connection
        table_name  : table name (case-insensitive, auto-uppercased)
        schema_name : HANA schema/user (optional — defaults to current user's schema)

    Returns:
        {
            "table":   "FULL_TABLE_NAME",
            "schema":  "SCHEMA_NAME",
            "columns": [{"name": "COL1", "type": "NVARCHAR"}, ...]
        }
    """
    table_name  = table_name.upper()
    cursor      = conn.cursor()

    if schema_name:
        schema_name = schema_name.upper()
        query = """
            SELECT COLUMN_NAME, DATA_TYPE_NAME
            FROM SYS.COLUMNS
            WHERE TABLE_NAME = ? AND SCHEMA_NAME = ?
            ORDER BY POSITION
        """
        cursor.execute(query, (table_name, schema_name))
    else:
        # Use the current connected user's schema as default
        query = """
            SELECT COLUMN_NAME, DATA_TYPE_NAME
            FROM SYS.COLUMNS
            WHERE TABLE_NAME = ? AND SCHEMA_NAME = CURRENT_USER
            ORDER BY POSITION
        """
        cursor.execute(query, (table_name,))

    rows = cursor.fetchall()
    cursor.close()

    if not rows:
        log.warning("No columns found for table '%s'. Check table name and schema.", table_name)
        return {"table": table_name, "schema": schema_name or "CURRENT_USER", "columns": []}

    columns = [{"name": r[0], "type": r[1]} for r in rows]
    resolved_schema = schema_name or "CURRENT_USER"

    log.info("Schema fetched: %s.%s — %d columns", resolved_schema, table_name, len(columns))
    return {"table": table_name, "schema": resolved_schema, "columns": columns}


def build_schema_context(conn, tables: list) -> str:
    """
    Builds a human-readable schema description for all requested tables.
    This is injected into the AI prompt so the LLM knows the DB structure.

    Args:
        conn   : hdbcli Connection
        tables : list of table name strings, or list of dicts {"table": ..., "schema": ...}

    Returns:
        Multiline string describing each table and its columns.

    Example output:
        Table: SALES_ORDERS
          - ORDER_ID       : NVARCHAR
          - CUSTOMER_NAME  : NVARCHAR
          - ORDER_VALUE    : DECIMAL
    """
    lines = []
    for entry in tables:
        if isinstance(entry, dict):
            info = get_table_schema(conn, entry["table"], entry.get("schema"))
        else:
            info = get_table_schema(conn, entry)

        lines.append(f"Table: {info['schema']}.{info['table']}")
        if info["columns"]:
            for col in info["columns"]:
                lines.append(f"  - {col['name']:<30} : {col['type']}")
        else:
            lines.append("  (no columns found — check table name)")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# 3. SQL GENERATION (AI)
# ─────────────────────────────────────────────

SQL_PROMPT = ChatPromptTemplate.from_template("""
You are an expert SAP HANA SQL developer. Your task is to write a SQL SELECT query
for SAP HANA Cloud based on the user's question.

Rules:
- Write only a single SQL SELECT statement. No INSERT, UPDATE, DELETE, DROP, or DDL.
- Use only the tables and columns listed in the schema below.
- For HANA Cloud, use standard SQL. Avoid MySQL or T-SQL specific syntax.
- If the user asks for "top N", use "LIMIT N" or "FETCH FIRST N ROWS ONLY".
- Qualify table names with schema when provided (e.g. SCHEMA.TABLE).
- Return ONLY the raw SQL query — no explanation, no markdown, no code fences.

Available Schema:
{schema_context}

User Question:
{user_query}

SQL Query:
""")


def generate_sql(user_query: str, schema_context: str, llm) -> str:
    """
    Uses the LLM to convert a natural language question into a HANA SQL query.

    Args:
        user_query     : plain English question from the user
        schema_context : output from build_schema_context()
        llm            : LangChain LLM instance

    Returns:
        SQL query string (SELECT only)
    """
    chain = SQL_PROMPT | llm | StrOutputParser()

    raw = chain.invoke({
        "schema_context": schema_context,
        "user_query":     user_query,
    })

    # Strip markdown fences if the LLM adds them anyway
    sql = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip().strip("`").strip()

    log.info("Generated SQL:\n%s", sql)
    return sql


# ─────────────────────────────────────────────
# 4. SQL EXECUTION
# ─────────────────────────────────────────────
def execute_sql(conn, sql: str) -> pd.DataFrame:
    """
    Executes a SQL SELECT query and returns the result as a pandas DataFrame.

    Args:
        conn : hdbcli Connection
        sql  : SQL query string

    Returns:
        pandas DataFrame with query results.

    Raises:
        ValueError  : if the query is not a SELECT statement (safety guard)
        Exception   : re-raises DB errors with the failing SQL attached
    """
    # Safety guard — only allow SELECT
    first_word = sql.strip().split()[0].upper()
    if first_word != "SELECT":
        raise ValueError(
            f"Only SELECT queries are allowed. Got: '{first_word}'\nSQL: {sql}"
        )

    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows    = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df      = pd.DataFrame(rows, columns=columns)
        log.info("Query returned %d rows, %d columns", len(df), len(df.columns))
        return df
    except Exception as e:
        log.error("SQL execution failed.\nSQL: %s\nError: %s", sql, e)
        raise Exception(f"SQL execution failed: {e}\nSQL attempted:\n{sql}")
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# 5. MAIN AGENT CLASS
# ─────────────────────────────────────────────
class HANAQueryAgent:
    """
    All-in-one agent: natural language → SQL → execute → DataFrame.

    Usage:
        from hana_connection import get_hana_credentials, get_dbapi_connection
        from hana_ai_query import HANAQueryAgent

        creds = get_hana_credentials()
        conn  = get_dbapi_connection(creds)

        agent = HANAQueryAgent(conn, tables=["SALES_ORDERS", "CUSTOMERS"])
        df    = agent.ask("Show me the top 5 customers by total order value")
        print(df)
    """

    def __init__(self, conn, tables: list, llm=None):
        """
        Args:
            conn   : hdbcli Connection from hana_connection.py
            tables : list of table names (str) or dicts {"table": ..., "schema": ...}
                     that the agent is allowed to query
            llm    : optional — pass your own LLM. Defaults to SAP Gen AI Hub.
        """
        self.conn           = conn
        self.tables         = tables
        self.llm            = llm or get_llm()
        self.schema_context = build_schema_context(conn, tables)

        log.info("HANAQueryAgent ready. Tables in scope: %s", tables)

    def ask(self, user_query: str) -> pd.DataFrame:
        """
        Full pipeline: user question → SQL → execute → DataFrame.

        Args:
            user_query : plain English question

        Returns:
            pandas DataFrame with query results
        """
        log.info("User query: %s", user_query)

        # Step 1: AI generates SQL
        sql = generate_sql(user_query, self.schema_context, self.llm)

        # Step 2: Execute against HANA
        df = execute_sql(self.conn, sql)

        return df

    def ask_with_summary(self, user_query: str) -> dict:
        """
        Same as ask() but also generates a plain English summary of the results.

        Returns:
            {
                "sql":     "<generated SQL>",
                "data":    <pandas DataFrame>,
                "summary": "<AI-generated summary of results>"
            }
        """
        log.info("User query (with summary): %s", user_query)

        # Step 1: Generate and execute SQL
        sql = generate_sql(user_query, self.schema_context, self.llm)
        df  = execute_sql(self.conn, sql)

        # Step 2: AI summarizes the results
        summary_prompt = ChatPromptTemplate.from_template("""
You are a helpful data analyst. The user asked: "{user_query}"

The SQL query run was:
{sql}

The result contains {row_count} rows. Here is a sample (up to 20 rows):
{sample_data}

Write a concise, clear answer to the user's question based on this data.
Do not mention SQL or technical details — just answer the question naturally.
""")
        summary_chain   = summary_prompt | self.llm | StrOutputParser()
        sample_markdown = df.head(20).to_markdown(index=False) if not df.empty else "No results found."

        summary = summary_chain.invoke({
            "user_query":  user_query,
            "sql":         sql,
            "row_count":   len(df),
            "sample_data": sample_markdown,
        })

        log.info("Summary generated.")
        return {"sql": sql, "data": df, "summary": summary}

    def get_schema(self) -> str:
        """Returns the current schema context string (useful for debugging)."""
        return self.schema_context


# ─────────────────────────────────────────────
# 6. MAIN — run standalone
# ─────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SAP HANA Cloud — AI Query Agent")
    print("=" * 60)

    # ── Step 1: Connect ──────────────────────────────────────────
    creds   = get_hana_credentials()
    conn    = get_dbapi_connection(creds)

    # ── Step 2: Define which tables the agent can query ──────────
    # Option A: simple list of table names (uses current user's schema)
    TABLES = ["CUST_TICKETS"]

    # Option B: specify schema explicitly
    # TABLES = [{"table": "CUST_TICKETS", "schema": "DBADMIN"}]

    # ── Step 3: Create the agent ─────────────────────────────────
    agent = HANAQueryAgent(conn, tables=TABLES)

    # ── Step 4a: Simple query — returns DataFrame ────────────────
    print("\n── Example 1: Simple query ──")
    user_question = "Show me the 5 most recent tickets with their category and priority"
    df = agent.ask(user_question)
    print(df.to_string(index=False))

    # ── Step 4b: Query with AI summary ───────────────────────────
    print("\n── Example 2: Query with natural language summary ──")
    user_question_2 = "How many tickets are there per category?"
    result = agent.ask_with_summary(user_question_2)

    print("\nGenerated SQL:")
    print(result["sql"])
    print("\nData:")
    print(result["data"].to_string(index=False))
    print("\nAI Summary:")
    print(result["summary"])

    # ── Step 5: Clean up ─────────────────────────────────────────
    conn.close()
    print("\n" + "=" * 60 + "\n")
