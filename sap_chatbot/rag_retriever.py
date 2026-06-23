"""
============================================================
MINI TEMPLATE — RAG Retriever for Chatbot
============================================================
Use this when: your chatbot needs to answer questions from
documents stored in the HANA Vector Store.

Fetches top-K chunks from HANA using cosine similarity,
applies score filtering, and returns:
  - context_text : formatted string injected into the prompt
  - sources      : list of source citations for the response

Depends on:
  hana_vector_store/similarity_search.py
  hana_vector_store/embedding_setup.py

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain-openai python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store"))

from hdbcli import dbapi
from chatbot_config import ChatbotConfig
from similarity_search import similarity_search


def rag_retrieve(
    conn: dbapi.Connection,
    user_message: str,
    config: ChatbotConfig,
    embedder,
) -> tuple[str, list]:
    """
    Retrieve relevant chunks from HANA Vector Store for the chatbot.

    Args:
        conn         : hdbcli Connection
        user_message : the user's chat message
        config       : ChatbotConfig (reads vector_table, rag_top_k, rag_min_score, rag_source_filter)
        embedder     : embedding model (from llm_setup.build_embedding_model)

    Returns:
        context_text : str  — formatted numbered context block for the prompt
                              empty string if no relevant chunks found
        sources      : list — list of source dicts for the response
                              [{"rank", "source_name", "source_type", "score"}]
    """
    chunks = similarity_search(
        conn=conn,
        query=user_message,
        embedding_model=embedder,
        table_name=config.vector_table,
        top_k=config.rag_top_k,
        source_filter=config.rag_source_filter,
    )

    # Filter by minimum score
    if config.rag_min_score > 0:
        before = len(chunks)
        chunks = [c for c in chunks if c["score"] >= config.rag_min_score]
        if before != len(chunks):
            print(f"Score filter ({config.rag_min_score}): {before} → {len(chunks)} chunks")

    if not chunks:
        return "", []

    # Format context block
    lines = [
        f"[{c['rank']}] {c['source_name']} (score: {c['score']})\n{c['content']}"
        for c in chunks
    ]
    context_text = "\n\n".join(lines)

    sources = [
        {
            "rank":        c["rank"],
            "source_name": c["source_name"],
            "source_type": c["source_type"],
            "score":       c["score"],
        }
        for c in chunks
    ]

    print(f"✅ RAG: retrieved {len(chunks)} chunks for: '{user_message[:50]}'")
    return context_text, sources


if __name__ == "__main__":
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect
    from embedding_setup import get_embedding_model

    conn     = connect()
    embedder = get_embedding_model()

    config = ChatbotConfig(
        enable_rag    = True,
        vector_table  = "VECTOR_STORE",
        rag_top_k     = 3,
        rag_min_score = 0.5,
    )

    context_text, sources = rag_retrieve(conn, "What is SAP HANA Cloud?", config, embedder)

    print("\n── Context ────────────────────────────")
    print(context_text or "(no relevant chunks found)")
    print("\n── Sources ────────────────────────────")
    for s in sources:
        print(f"  [{s['rank']}] {s['source_name']} | score: {s['score']}")

    conn.close()
