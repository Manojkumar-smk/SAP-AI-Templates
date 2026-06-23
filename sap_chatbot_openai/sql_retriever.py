"""
============================================================
MINI TEMPLATE — SQL Retriever for Chatbot
============================================================
Use this when: your chatbot needs to answer questions from
live structured data in HANA tables.

Flow:
  user message
    → fetch table schema from SYS.COLUMNS
    → LLM generates a SELECT query
    → execute on HANA
    → return results as readable text for the prompt

Depends on:
  hana_ai_query/schema_inspector.py
  hana_ai_query/sql_generator.py
  hana_ai_query/sql_executor.py

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain langchain-core langchain-openai pandas python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_ai_query"))

from hdbcli import dbapi
from chatbot_config import ChatbotConfig
from schema_inspector import build_schema_context
from sql_generator import generate_sql
from sql_executor import execute_sql


def sql_retrieve(
    conn: dbapi.Connection,
    user_message: str,
    config: ChatbotConfig,
    llm,
) -> tuple[str, str]:
    """
    Generate and execute a SQL query for the chatbot based on the user's message.

    Args:
        conn         : hdbcli Connection
        user_message : the user's chat message
        config       : ChatbotConfig (reads sql_tables, sql_schema)
        llm          : LangChain LLM for SQL generation

    Returns:
        sql_result : str — query results as readable text (or error message)
                          injected into the prompt as {sql_result}
        sql_used   : str — the generated SQL query (for transparency in response)
    """
    # Build table list with optional schema
    tables = []
    for t in config.sql_tables:
        if isinstance(t, dict):
            tables.append(t)
        elif config.sql_schema:
            tables.append({"table": t, "schema": config.sql_schema})
        else:
            tables.append(t)

    # Build schema context for LLM
    schema_ctx = build_schema_context(conn, tables)

    # Generate SQL
    sql_used = generate_sql(user_message, schema_ctx, llm)

    # Execute SQL
    try:
        df         = execute_sql(conn, sql_used)
        sql_result = df.to_string(index=False) if not df.empty else "Query returned no rows."
        print(f"✅ SQL: executed, {len(df)} rows returned")
    except Exception as e:
        sql_result = f"SQL execution error: {e}"
        print(f"⚠️  SQL error: {e}")

    return sql_result, sql_used


if __name__ == "__main__":
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from llm_setup import build_llm

    conn   = connect()
    config = ChatbotConfig(
        enable_sql = True,
        sql_tables = ["CUST_TICKETS"],   # ← change to your table
    )
    llm = build_llm(config)

    sql_result, sql_used = sql_retrieve(
        conn, "Show me the 5 most recent tickets", config, llm
    )

    print("\n── SQL Used ───────────────────────────")
    print(sql_used)
    print("\n── Result ─────────────────────────────")
    print(sql_result)

    conn.close()
