"""
============================================================
MINI TEMPLATE — Cosine Similarity Search (HANA Vector Engine)
============================================================
Use this when: you have vectors stored in HANA and want to
find the most semantically similar chunks for a query.

How it works:
  1. Embed your query text → query vector
  2. HANA computes COSINE_SIMILARITY between query vector
     and every stored EMBEDDING
  3. Returns top-K results sorted by similarity score (0–1)
     where 1.0 = identical, 0.0 = completely unrelated

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain-openai python-dotenv
============================================================
"""

import json
from hdbcli import dbapi


def similarity_search(
    conn: dbapi.Connection,
    query: str,
    embedding_model,
    table_name: str = "VECTOR_STORE",
    top_k: int = 5,
    source_filter: str = None,
) -> list[dict]:
    """
    Find the top-K most relevant chunks for a query.

    Args:
        conn            : hdbcli Connection
        query           : natural language question or sentence
        embedding_model : same model used during embedding
        table_name      : HANA vector table to search
        top_k           : number of results to return (default: 5)
        source_filter   : optional — limit search to a specific source_name
                          e.g. "report.pdf" or "https://example.com"

    Returns:
        List of dicts:
        [
            {
                "rank":        1,
                "score":       0.92,       ← cosine similarity (0–1)
                "content":     "chunk text ...",
                "source_type": "pdf",
                "source_name": "report.pdf",
                "chunk_index": 3,
                "metadata":    {...}
            },
            ...
        ]
    """
    query_vector = str(embedding_model.embed_query(query))
    cursor       = conn.cursor()

    if source_filter:
        sql = f"""
            SELECT TOP {top_k}
                "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA",
                COSINE_SIMILARITY("EMBEDDING", TO_REAL_VECTOR(?)) AS SCORE
            FROM "{table_name}"
            WHERE "SOURCE_NAME" = ?
            ORDER BY SCORE DESC
        """
        cursor.execute(sql, (query_vector, source_filter))
    else:
        sql = f"""
            SELECT TOP {top_k}
                "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA",
                COSINE_SIMILARITY("EMBEDDING", TO_REAL_VECTOR(?)) AS SCORE
            FROM "{table_name}"
            ORDER BY SCORE DESC
        """
        cursor.execute(sql, (query_vector,))

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()

    results = []
    for rank, row in enumerate(rows, start=1):
        rec = dict(zip(columns, row))
        results.append({
            "rank":        rank,
            "score":       round(float(rec["SCORE"]), 4),
            "content":     rec["CONTENT"],
            "source_type": rec["SOURCE_TYPE"],
            "source_name": rec["SOURCE_NAME"],
            "chunk_index": rec["CHUNK_INDEX"],
            "metadata":    json.loads(rec["METADATA"]) if rec["METADATA"] else {},
        })

    print(f"✅ Search complete — {len(results)} result(s) for: '{query[:60]}'")
    return results


if __name__ == "__main__":
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from embedding_setup import get_embedding_model

    conn  = connect()
    model = get_embedding_model()

    # ── Change query and table name as needed ─────────────
    QUERY = "What is SAP HANA Cloud used for?"
    TABLE = "VECTOR_STORE"
    # ─────────────────────────────────────────────────────

    results = similarity_search(conn, QUERY, model, table_name=TABLE, top_k=3)

    print(f"\n── Top {len(results)} Results ─────────────────────")
    for r in results:
        print(f"\nRank {r['rank']} | Score: {r['score']}")
        print(f"  Source  : {r['source_type']} → {r['source_name']}")
        print(f"  Content : {r['content'][:200]}")

    conn.close()
