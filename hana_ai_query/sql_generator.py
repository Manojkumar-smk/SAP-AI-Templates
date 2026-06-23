"""
============================================================
MINI TEMPLATE — Natural Language to SQL Generator (AI)
============================================================
Use this when: you have a user question + table schema and
want the LLM to generate a HANA-compatible SELECT query.

Flow:
  user question + schema_context → LLM → SQL string

Depends on:
  llm_setup.py          (for get_llm)
  schema_inspector.py   (for build_schema_context)

Setup:
  pip install sap-ai-sdk-gen langchain langchain-core langchain-openai python-dotenv
============================================================
"""

import re
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Prompt sent to the LLM ────────────────────────────────
SQL_PROMPT = ChatPromptTemplate.from_template("""
You are an expert SAP HANA SQL developer. Write a SQL SELECT query
for SAP HANA Cloud based on the user's question.

Rules:
- Write ONLY a single SELECT statement. No INSERT, UPDATE, DELETE, DROP, or DDL.
- Use only the tables and columns listed in the schema below.
- For HANA Cloud, use standard SQL (not MySQL or T-SQL syntax).
- For "top N" results, use: FETCH FIRST N ROWS ONLY
- Qualify table names with schema when provided (e.g. SCHEMA.TABLE).
- Return ONLY the raw SQL — no explanation, no markdown, no code fences.

Available Schema:
{schema_context}

User Question:
{user_query}

SQL Query:
""")


def generate_sql(user_query: str, schema_context: str, llm) -> str:
    """
    Use the LLM to convert a plain English question to a HANA SQL query.

    Args:
        user_query     : e.g. "Show top 5 customers by revenue"
        schema_context : output from schema_inspector.build_schema_context()
        llm            : LangChain LLM from llm_setup.get_llm()

    Returns:
        SQL SELECT string
    """
    chain = SQL_PROMPT | llm | StrOutputParser()

    raw = chain.invoke({
        "schema_context": schema_context,
        "user_query":     user_query,
    })

    # Strip markdown code fences if the LLM adds them anyway
    sql = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).strip().strip("`").strip()
    print(f"Generated SQL:\n{sql}\n")
    return sql


if __name__ == "__main__":
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from schema_inspector import build_schema_context
    from llm_setup import get_llm

    conn   = connect()
    llm    = get_llm()

    # ── Change to your table(s) and question ─────────────
    TABLES         = ["CUST_TICKETS"]
    USER_QUESTION  = "Show me the 5 most recent tickets with their category and priority"
    # ─────────────────────────────────────────────────────

    schema_context = build_schema_context(conn, TABLES)
    sql = generate_sql(USER_QUESTION, schema_context, llm)

    print("── Final SQL ──────────────────────────")
    print(sql)

    conn.close()
