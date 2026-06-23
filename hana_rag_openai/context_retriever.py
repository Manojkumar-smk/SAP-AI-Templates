"""
============================================================
MINI TEMPLATE — Context Retriever
============================================================
Use this when: you need to fetch relevant chunks from HANA
Vector Store and format them into a readable context block
that gets injected into the RAG prompt.

Two functions:
  retrieve_context() → fetches top-K chunks from HANA
  format_context()   → formats chunks into a numbered string

Depends on:
  hana_vector_store/similarity_search.py
  hana_vector_store/embedding_setup.py

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain-openai python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store"))

from similarity_search import similarity_search
from hdbcli import dbapi


def retrieve_context(
    conn: dbapi.Connection,
    user_query: str,
    embedding_model,
    table_name: str = "VECTOR_STORE",
    top_k: int = 5,
    source_filter: str = None,
    min_score: float = 0.0,
) -> list[dict]:
    """
    Fetch the most relevant chunks from HANA Vector Store.

    Args:
        conn            : hdbcli Connection
        user_query      : the user's question
        embedding_model : same model used when storing vectors
        table_name      : HANA vector table to search
        top_k           : number of chunks to retrieve (default: 5)
        source_filter   : optional — limit search to one source (e.g. "report.pdf")
        min_score       : optional — discard chunks below this score (0.0–1.0)

    Returns:
        List of chunk dicts (rank, score, content, source_type, source_name, ...)
    """
    chunks = similarity_search(
        conn=conn,
        query=user_query,
        embedding_model=embedding_model,
        table_name=table_name,
        top_k=top_k,
        source_filter=source_filter,
    )

    if min_score > 0.0:
        before = len(chunks)
        chunks = [c for c in chunks if c["score"] >= min_score]
        print(f"Score filter ({min_score}): {before} → {len(chunks)} chunks retained")

    print(f"✅ Retrieved {len(chunks)} context chunk(s) for: '{user_query[:60]}'")
    return chunks


def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a numbered context block for the LLM prompt.

    Each chunk is numbered and shows its source for transparency.

    Example output:
        [1] Source: report.pdf (chunk 3)
        SAP HANA Cloud supports vector embeddings via REAL_VECTOR...

        [2] Source: https://help.sap.com (chunk 0)
        The cosine similarity function compares two vectors...

    Args:
        chunks : list of dicts from retrieve_context()

    Returns:
        Formatted string to inject into the RAG prompt as {context}
    """
    if not chunks:
        return "No relevant context found."

    parts = [
        f"[{c['rank']}] Source: {c['source_name']} (chunk {c['chunk_index']})\n{c['content']}"
        for c in chunks
    ]
    return "\n\n".join(parts)


if __name__ == "__main__":
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from embedding_setup import get_embedding_model

    conn  = connect()
    model = get_embedding_model()

    # ── Change to your query and table ───────────────────
    QUERY = "What is SAP HANA Cloud?"
    TABLE = "VECTOR_STORE"
    # ─────────────────────────────────────────────────────

    chunks  = retrieve_context(conn, QUERY, model, table_name=TABLE, top_k=3, min_score=0.5)
    context = format_context(chunks)

    print("\n── Formatted Context ──────────────────")
    print(context)

    conn.close()
