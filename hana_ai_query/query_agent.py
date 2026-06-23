"""
============================================================
MINI TEMPLATE — HANA AI Query Agent (Full Pipeline)
============================================================
Use this when: you want the full end-to-end flow in one place:
  plain English question → schema → SQL → execute → DataFrame

This combines:
  llm_setup.py + schema_inspector.py + sql_generator.py + sql_executor.py

Just call agent.ask("your question") and get a DataFrame back.

Depends on: hana_db_connection/connect_env.py (or connect_btp_cf.py)
Setup:
  pip install hdbcli hana-ml sap-ai-sdk-gen langchain langchain-core langchain-openai pandas python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))

import pandas as pd
from hdbcli import dbapi
from llm_setup import get_llm
from schema_inspector import build_schema_context
from sql_generator import generate_sql
from sql_executor import execute_sql


class QueryAgent:
    """
    Natural language → SQL → DataFrame agent for SAP HANA.

    Usage:
        from connect_env import connect
        from query_agent import QueryAgent

        conn  = connect()
        agent = QueryAgent(conn, tables=["SALES_ORDERS", "CUSTOMERS"])

        df = agent.ask("Show me the top 5 customers by total order value")
        print(df)
    """

    def __init__(self, conn: dbapi.Connection, tables: list, llm=None):
        """
        Args:
            conn   : hdbcli Connection
            tables : list of table names (str) or dicts {"table": ..., "schema": ...}
            llm    : optional — pass your own LLM; defaults to SAP Gen AI Hub
        """
        self.conn           = conn
        self.tables         = tables
        self.llm            = llm or get_llm()
        self.schema_context = build_schema_context(conn, tables)
        print(f"✅ QueryAgent ready. Tables: {tables}")

    def ask(self, user_query: str) -> pd.DataFrame:
        """
        Run the full pipeline: user question → SQL → DataFrame.

        Args:
            user_query : plain English question

        Returns:
            pandas DataFrame with results
        """
        sql = generate_sql(user_query, self.schema_context, self.llm)
        return execute_sql(self.conn, sql)

    def get_schema(self) -> str:
        """Return the schema context string (useful for debugging)."""
        return self.schema_context


if __name__ == "__main__":
    from connect_env import connect   # swap to connect_btp_cf if on BTP

    conn = connect()

    # ── Define which tables the agent can query ───────────
    TABLES = ["CUST_TICKETS"]
    # ─────────────────────────────────────────────────────

    agent = QueryAgent(conn, tables=TABLES)

    # Ask a question in plain English
    question = "Show me the 5 most recent tickets with their category and priority"
    df = agent.ask(question)

    print("\n── Result ─────────────────────────────")
    print(df.to_string(index=False))

    conn.close()
