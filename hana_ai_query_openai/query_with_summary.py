"""
============================================================
MINI TEMPLATE — Query with AI Summary
============================================================
Use this when: you want the query result AND a plain English
summary of what the data means — all in one call.

Returns:
  {
    "sql":     "<generated SQL>",
    "data":    <pandas DataFrame>,
    "summary": "<natural language answer>"
  }

Depends on: query_agent.py (and all its dependencies)
Setup:
  pip install hdbcli sap-ai-sdk-gen langchain langchain-core langchain-openai pandas tabulate python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))

import pandas as pd
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm_setup import get_llm
from schema_inspector import build_schema_context
from sql_generator import generate_sql
from sql_executor import execute_sql

# ── Summary prompt ────────────────────────────────────────
SUMMARY_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful data analyst. The user asked: "{user_query}"

The SQL query run was:
{sql}

The result has {row_count} rows. Here is a sample (up to 20 rows):
{sample_data}

Write a concise, clear answer to the user's question based on this data.
Do not mention SQL or technical details — just answer naturally.
""")


def ask_with_summary(conn, tables: list, user_query: str, llm=None) -> dict:
    """
    Full pipeline: question → SQL → execute → AI summary.

    Args:
        conn       : hdbcli Connection
        tables     : list of table names (str) or dicts {"table": ..., "schema": ...}
        user_query : plain English question
        llm        : optional LangChain LLM (defaults to SAP Gen AI Hub)

    Returns:
        {
            "sql":     "<generated SELECT>",
            "data":    <pandas DataFrame>,
            "summary": "<AI-generated plain English answer>"
        }
    """
    llm = llm or get_llm()

    schema_context = build_schema_context(conn, tables)
    sql            = generate_sql(user_query, schema_context, llm)
    df             = execute_sql(conn, sql)

    # Generate plain English summary of results
    sample = df.head(20).to_markdown(index=False) if not df.empty else "No results found."

    summary_chain = SUMMARY_PROMPT | llm | StrOutputParser()
    summary = summary_chain.invoke({
        "user_query":  user_query,
        "sql":         sql,
        "row_count":   len(df),
        "sample_data": sample,
    })

    return {"sql": sql, "data": df, "summary": summary}


if __name__ == "__main__":
    from connect_env import connect   # swap to connect_btp_cf if on BTP

    conn = connect()

    # ── Change tables and question ────────────────────────
    TABLES   = ["CUST_TICKETS"]
    QUESTION = "How many tickets are there per category?"
    # ─────────────────────────────────────────────────────

    result = ask_with_summary(conn, TABLES, QUESTION)

    print("\n── Generated SQL ──────────────────────")
    print(result["sql"])

    print("\n── Data ───────────────────────────────")
    print(result["data"].to_string(index=False))

    print("\n── AI Summary ─────────────────────────")
    print(result["summary"])

    conn.close()
