"""
============================================================
MINI TEMPLATE — HANA Table Schema Inspector
============================================================
Use this when: you need to fetch column info from a HANA table
and build a schema description to feed into an AI prompt.

Why: The LLM needs to know table structure (column names + types)
before it can generate correct SQL.

Depends on: hana_db_connection/connect_env.py (or connect_btp_cf.py)
Setup:
  pip install hdbcli python-dotenv
============================================================
"""

import sys, pathlib
# ── Point to your hana_db_connection folder ──────────────
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
from connect_env import connect   # swap to connect_btp_cf if on BTP
# ─────────────────────────────────────────────────────────


def get_table_schema(conn, table_name: str, schema_name: str = None) -> dict:
    """
    Fetch column names and types for a HANA table from SYS.COLUMNS.

    Args:
        conn        : hdbcli Connection
        table_name  : table name (auto-uppercased)
        schema_name : HANA schema (optional — defaults to current user's schema)

    Returns:
        {
            "table":   "TABLE_NAME",
            "schema":  "SCHEMA_NAME",
            "columns": [{"name": "COL1", "type": "NVARCHAR"}, ...]
        }
    """
    table_name = table_name.upper()
    cursor = conn.cursor()

    if schema_name:
        cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE_NAME FROM SYS.COLUMNS "
            "WHERE TABLE_NAME = ? AND SCHEMA_NAME = ? ORDER BY POSITION",
            (table_name, schema_name.upper())
        )
    else:
        cursor.execute(
            "SELECT COLUMN_NAME, DATA_TYPE_NAME FROM SYS.COLUMNS "
            "WHERE TABLE_NAME = ? AND SCHEMA_NAME = CURRENT_USER ORDER BY POSITION",
            (table_name,)
        )

    rows = cursor.fetchall()
    cursor.close()

    columns = [{"name": r[0], "type": r[1]} for r in rows]
    if not columns:
        print(f"⚠️  No columns found for '{table_name}'. Check table name and schema.")

    return {
        "table":   table_name,
        "schema":  schema_name or "CURRENT_USER",
        "columns": columns,
    }


def build_schema_context(conn, tables: list) -> str:
    """
    Build a human-readable schema string for multiple tables.
    This string is injected into the AI prompt.

    Args:
        conn   : hdbcli Connection
        tables : list of table names (str) OR dicts {"table": "...", "schema": "..."}

    Returns:
        Multiline string like:
            Table: DBADMIN.SALES_ORDERS
              - ORDER_ID       : NVARCHAR
              - ORDER_VALUE    : DECIMAL
    """
    lines = []
    for entry in tables:
        if isinstance(entry, dict):
            info = get_table_schema(conn, entry["table"], entry.get("schema"))
        else:
            info = get_table_schema(conn, entry)

        lines.append(f"Table: {info['schema']}.{info['table']}")
        for col in info["columns"]:
            lines.append(f"  - {col['name']:<30} : {col['type']}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    conn = connect()

    # ── Change to your actual table name(s) ──────────────
    TABLES = ["CUST_TICKETS"]
    # or with explicit schema:
    # TABLES = [{"table": "CUST_TICKETS", "schema": "DBADMIN"}]
    # ─────────────────────────────────────────────────────

    schema_context = build_schema_context(conn, TABLES)
    print("\n── Schema Context ─────────────────────")
    print(schema_context)

    conn.close()
