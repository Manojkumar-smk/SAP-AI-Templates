"""
============================================================
MINI TEMPLATE — Safe SQL Executor (HANA → DataFrame)
============================================================
Use this when: you have a SQL query string and want to run it
against HANA and get back a pandas DataFrame.

Safety: only SELECT statements are allowed — any other
statement type raises a ValueError before touching the DB.

Depends on: hana_db_connection/connect_env.py (or connect_btp_cf.py)
Setup:
  pip install hdbcli pandas python-dotenv
============================================================
"""

import pandas as pd
from hdbcli import dbapi


def execute_sql(conn: dbapi.Connection, sql: str) -> pd.DataFrame:
    """
    Execute a SELECT query on HANA and return results as a DataFrame.

    Args:
        conn : hdbcli Connection
        sql  : SQL SELECT string

    Returns:
        pandas DataFrame

    Raises:
        ValueError  : if sql is not a SELECT statement
        Exception   : re-raises DB errors with the failing SQL attached
    """
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
        print(f"✅ Query returned {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        raise Exception(f"SQL execution failed: {e}\nSQL:\n{sql}")
    finally:
        cursor.close()


if __name__ == "__main__":
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect

    conn = connect()

    # ── Paste any SELECT query here ───────────────────────
    SQL = "SELECT CURRENT_UTCTIMESTAMP AS NOW FROM DUMMY"
    # ─────────────────────────────────────────────────────

    df = execute_sql(conn, SQL)
    print(df.to_string(index=False))

    conn.close()
