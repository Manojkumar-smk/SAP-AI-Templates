"""
============================================================
Router — POST /api/sql-query
============================================================
Natural language -> SQL -> HANA -> JSON rows. Same two-layer
safety pattern as hana_ai_query/sql_executor.py: the prompt
says SELECT-only, AND the code independently checks the first
word of the generated SQL before executing it.
============================================================
"""

from fastapi import APIRouter, HTTPException
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from schemas import SqlQueryRequest, SqlQueryResponse
from llm_client import get_llm
from hana_db import get_connection

router = APIRouter()

SQL_PROMPT = ChatPromptTemplate.from_template("""
You are a HANA SQL expert. Write ONE SELECT statement only — no INSERT/UPDATE/DELETE/DDL.
Use "FETCH FIRST N ROWS ONLY" for row limits.
Schema: {schema}
Question: {question}
SQL:
""")


def _schema_context(conn, tables: list) -> str:
    lines = []
    cursor = conn.cursor()
    for t in tables:
        cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE_NAME FROM SYS.COLUMNS WHERE TABLE_NAME = ? ORDER BY POSITION",
            (t.upper(),))
        cols = cursor.fetchall()
        lines.append(f"Table: {t}")
        lines += [f"  - {c[0]} : {c[1]}" for c in cols]
    cursor.close()
    return "\n".join(lines)


@router.post("/api/sql-query", response_model=SqlQueryResponse)
def sql_query(req: SqlQueryRequest) -> SqlQueryResponse:
    conn = get_connection()
    try:
        schema = _schema_context(conn, req.tables)
        chain = SQL_PROMPT | get_llm(temperature=0) | StrOutputParser()
        sql = chain.invoke({"schema": schema, "question": req.question}).strip().strip("`")

        if sql.split()[0].upper() != "SELECT":                 # safety check #2 — independent of the prompt
            raise HTTPException(status_code=400, detail=f"Generated statement was not a SELECT: {sql}")

        cursor = conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        cursor.close()

        return SqlQueryResponse(sql=sql, row_count=len(rows), rows=rows)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SQL query failed: {e}")
    finally:
        conn.close()
