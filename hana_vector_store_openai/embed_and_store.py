"""
============================================================
MINI TEMPLATE — Embed and Store in HANA
============================================================
Use this when: you have chunked documents and want to generate
embeddings and insert them into the HANA vector table.

Flow:
  list of chunk Documents
      → embedding model generates vectors (in batches)
      → inserted into HANA with TO_REAL_VECTOR()

Reduce batch_size if you hit API rate limits.

Depends on:
  embedding_setup.py  (for get_embedding_model)
  vector_table.py     (table must already exist)

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain langchain-openai python-dotenv
============================================================
"""

import json
import uuid
from hdbcli import dbapi
from langchain.schema import Document


def embed_and_store(
    conn: dbapi.Connection,
    chunks: list[Document],
    embedding_model,
    table_name: str = "VECTOR_STORE",
    batch_size: int = 50,
) -> int:
    """
    Generate embeddings for chunks and insert into HANA.

    Args:
        conn            : hdbcli Connection
        chunks          : list of Documents from text_chunker.py
        embedding_model : model from embedding_setup.get_embedding_model()
        table_name      : target HANA vector table
        batch_size      : chunks per embedding API call (reduce if rate-limited)

    Returns:
        Total number of chunks stored
    """
    if not chunks:
        print("⚠️  No chunks to store — skipping.")
        return 0

    insert_sql = f"""
        INSERT INTO "{table_name}"
            ("ID", "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA", "EMBEDDING")
        VALUES (?, ?, ?, ?, ?, ?, TO_REAL_VECTOR(?))
    """

    cursor      = conn.cursor()
    total       = 0

    for start in range(0, len(chunks), batch_size):
        batch  = chunks[start : start + batch_size]
        texts  = [c.page_content for c in batch]

        print(f"Embedding batch {start + 1}–{start + len(batch)} of {len(chunks)} ...")
        vectors = embedding_model.embed_documents(texts)

        rows = [
            (
                str(uuid.uuid4()),
                chunk.metadata.get("source_type", "unknown"),
                chunk.metadata.get("source_name", "unknown"),
                chunk.metadata.get("chunk_index", 0),
                chunk.page_content,
                json.dumps(chunk.metadata),
                str(vector),               # HANA expects a string → TO_REAL_VECTOR converts it
            )
            for chunk, vector in zip(batch, vectors)
        ]

        cursor.executemany(insert_sql, rows)
        conn.commit()
        total += len(rows)
        print(f"  ✅ Stored {len(rows)} chunks (total: {total})")

    cursor.close()
    print(f"\n✅ Done. Total chunks stored: {total}")
    return total


if __name__ == "__main__":
    import sys, pathlib
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from embedding_setup import get_embedding_model
    from document_loaders import load_documents
    from text_chunker import chunk_documents
    from vector_table import create_vector_table

    conn  = connect()
    model = get_embedding_model()

    TABLE = "VECTOR_STORE"
    create_vector_table(conn, TABLE)

    # ── Load and chunk your content ───────────────────────
    docs   = load_documents("SAP HANA Cloud supports in-memory and vector processing.")
    chunks = chunk_documents(docs)
    # ─────────────────────────────────────────────────────

    embed_and_store(conn, chunks, model, table_name=TABLE)
    conn.close()
