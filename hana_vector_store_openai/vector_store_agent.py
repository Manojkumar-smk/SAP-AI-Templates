"""
============================================================
MINI TEMPLATE — HANA Vector Store Agent (Full Pipeline)
============================================================
Use this when: you want the complete vector store workflow
in one class — load, chunk, embed, store, search, stats.

This combines all the other mini templates:
  embedding_setup + document_loaders + text_chunker
  + vector_table + embed_and_store + similarity_search

Just call:
  store.add("your_file.pdf")           → loads, chunks, embeds, stores
  store.search("your question")        → semantic search → list of results
  store.get_stats()                    → table row/source counts

Setup:
  pip install -r requirements.txt
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))

from hdbcli import dbapi
from embedding_setup import get_embedding_model
from document_loaders import load_documents
from text_chunker import chunk_documents
from vector_table import create_vector_table, clear_vector_table, get_table_stats
from embed_and_store import embed_and_store
from similarity_search import similarity_search


class VectorStoreAgent:
    """
    All-in-one HANA Vector Store — load any source, search semantically.

    Usage:
        from connect_env import connect
        from vector_store_agent import VectorStoreAgent

        conn  = connect()
        store = VectorStoreAgent(conn, table_name="MY_VECTORS")

        # Add documents from any source
        store.add("path/to/document.pdf")
        store.add("path/to/data.csv", content_columns=["title", "body"])
        store.add("https://help.sap.com/docs/hana-cloud")
        store.add("This is some raw text I want to embed.")

        # Semantic search
        results = store.search("What is the refund policy?", top_k=3)
        for r in results:
            print(r["score"], r["content"])

        # Stats
        print(store.get_stats())
    """

    def __init__(
        self,
        conn: dbapi.Connection,
        table_name: str = "VECTOR_STORE",
        embedding_model=None,
    ):
        self.conn            = conn
        self.table_name      = table_name
        self.embedding_model = embedding_model or get_embedding_model()

        # Ensure the vector table exists on startup
        create_vector_table(conn, table_name)

    def add(
        self,
        input_source: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        clear_existing: bool = False,
        **loader_kwargs,
    ) -> int:
        """
        Full pipeline: load → chunk → embed → store.

        Args:
            input_source   : file path, URL, or raw text string
            chunk_size     : characters per chunk (default: 500)
            chunk_overlap  : overlap between chunks (default: 50)
            clear_existing : if True, removes existing vectors for this source first
            **loader_kwargs: passed to loader (e.g. content_columns for CSV/Excel)

        Returns:
            Number of chunks stored
        """
        docs = load_documents(input_source, **loader_kwargs)

        if clear_existing and docs:
            source_name = docs[0].metadata.get("source_name")
            if source_name:
                clear_vector_table(self.conn, self.table_name, source_name)

        chunks = chunk_documents(docs, chunk_size, chunk_overlap)
        return embed_and_store(self.conn, chunks, self.embedding_model, self.table_name)

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str = None,
    ) -> list[dict]:
        """
        Semantic similarity search across all stored vectors.

        Args:
            query         : natural language question or sentence
            top_k         : number of results to return
            source_filter : optional — limit to a specific source file or URL

        Returns:
            List of result dicts with rank, score, content, source info
        """
        return similarity_search(
            self.conn, query, self.embedding_model,
            self.table_name, top_k, source_filter
        )

    def clear(self, source_name: str = None) -> int:
        """
        Clear vectors from the table.
        If source_name is given, only that source is cleared.
        If None, ALL rows are deleted.
        """
        return clear_vector_table(self.conn, self.table_name, source_name)

    def get_stats(self) -> dict:
        """Return total chunks and sources in the vector table."""
        return get_table_stats(self.conn, self.table_name)


if __name__ == "__main__":
    from connect_env import connect   # swap to connect_btp_cf if on BTP

    conn  = connect()
    store = VectorStoreAgent(conn, table_name="VECTOR_STORE")

    # ── Add content (pick any source) ────────────────────
    store.add("SAP HANA Cloud is a cloud-native in-memory database platform.")
    # store.add("./data/report.pdf")
    # store.add("./data/products.csv", content_columns=["name", "description"])
    # store.add("https://help.sap.com/docs/hana-cloud")
    # ─────────────────────────────────────────────────────

    # Stats
    print("\nStats:", store.get_stats())

    # Search
    query   = "What is SAP HANA Cloud?"
    results = store.search(query, top_k=3)

    print(f"\n── Search Results for: '{query}' ───────")
    for r in results:
        print(f"\nRank {r['rank']} | Score: {r['score']}")
        print(f"  Source  : {r['source_type']} → {r['source_name']}")
        print(f"  Content : {r['content'][:200]}")

    conn.close()
