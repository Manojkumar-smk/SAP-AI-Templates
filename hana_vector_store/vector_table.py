"""
============================================================
MINI TEMPLATE — HANA Vector Table Setup
============================================================
Use this when: you need to create or reset the HANA table
that stores vector embeddings (REAL_VECTOR column type).

Table schema created:
  ID           → unique UUID per chunk
  SOURCE_TYPE  → text / pdf / csv / excel / url / txt
  SOURCE_NAME  → filename or URL
  CHUNK_INDEX  → position of chunk within its source
  CONTENT      → raw text of the chunk
  METADATA     → JSON string of all metadata
  EMBEDDING    → REAL_VECTOR(dimension) — the actual vector

!! VECTOR_DIMENSION must match your embedding model:
   text-embedding-ada-002  → 1536
   text-embedding-3-large  → 3072  !!

Setup:
  pip install hdbcli python-dotenv
============================================================
"""

import os
from dotenv import load_dotenv
from hdbcli import dbapi

load_dotenv()

# ── Must match the embedding model in embedding_setup.py ─
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", 1536))
# ─────────────────────────────────────────────────────────


def create_vector_table(conn: dbapi.Connection, table_name: str = "VECTOR_STORE") -> None:
    """
    Create the HANA vector table if it doesn't already exist.

    Args:
        conn       : hdbcli Connection
        table_name : name for the vector table (default: VECTOR_STORE)
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
        "ID"          NVARCHAR(100)  NOT NULL PRIMARY KEY,
        "SOURCE_TYPE" NVARCHAR(50),
        "SOURCE_NAME" NVARCHAR(500),
        "CHUNK_INDEX" INTEGER,
        "CONTENT"     NCLOB,
        "METADATA"    NCLOB,
        "EMBEDDING"   REAL_VECTOR({VECTOR_DIMENSION})
    )
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        print(f"✅ Vector table ready: {table_name} (dim={VECTOR_DIMENSION})")
    finally:
        cursor.close()


def clear_vector_table(
    conn: dbapi.Connection,
    table_name: str = "VECTOR_STORE",
    source_name: str = None
) -> int:
    """
    Delete rows from the vector table.

    Args:
        conn        : hdbcli Connection
        table_name  : target table
        source_name : if given, deletes only rows from that source.
                      If None, deletes ALL rows (full reset).

    Returns:
        Number of rows deleted
    """
    cursor = conn.cursor()
    try:
        if source_name:
            cursor.execute(
                f'DELETE FROM "{table_name}" WHERE "SOURCE_NAME" = ?',
                (source_name,)
            )
            print(f"Cleared rows for source: {source_name}")
        else:
            cursor.execute(f'DELETE FROM "{table_name}"')
            print(f"Cleared ALL rows from: {table_name}")

        count = cursor.rowcount
        conn.commit()
        print(f"  → {count} row(s) deleted")
        return count
    finally:
        cursor.close()


def get_table_stats(conn: dbapi.Connection, table_name: str = "VECTOR_STORE") -> dict:
    """
    Return basic stats about the vector table.

    Returns:
        {"table": ..., "total_chunks": ..., "total_sources": ...}
    """
    cursor = conn.cursor()
    cursor.execute(
        f'SELECT COUNT(*), COUNT(DISTINCT "SOURCE_NAME") FROM "{table_name}"'
    )
    row = cursor.fetchone()
    cursor.close()
    return {
        "table":         table_name,
        "total_chunks":  row[0],
        "total_sources": row[1],
    }


if __name__ == "__main__":
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect

    conn = connect()

    # Create table
    create_vector_table(conn, table_name="VECTOR_STORE")

    # Check stats
    stats = get_table_stats(conn, "VECTOR_STORE")
    print(f"\nStats: {stats}")

    # Uncomment to clear all rows:
    # clear_vector_table(conn, "VECTOR_STORE")

    # Uncomment to clear rows for one source only:
    # clear_vector_table(conn, "VECTOR_STORE", source_name="report.pdf")

    conn.close()
