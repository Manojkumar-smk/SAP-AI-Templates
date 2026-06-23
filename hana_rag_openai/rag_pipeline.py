"""
============================================================
MINI TEMPLATE — Single-Turn RAG Pipeline
============================================================
Use this when: you want a one-shot RAG call — no conversation
history, just: query → retrieve → generate → return answer + sources.

Flow:
  user_query
      → retrieve_context() from HANA vector store
      → format_context() into a readable block
      → inject into RAG_PROMPT
      → LLM generates a grounded answer
      → return answer + sources + context used

Depends on:
  context_retriever.py  (retrieve + format context)
  rag_prompts.py        (RAG_PROMPT)
  llm_setup.py          (get_llm)
  hana_vector_store/embedding_setup.py

Setup:
  pip install hdbcli sap-ai-sdk-gen langchain langchain-core langchain-openai python-dotenv
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))

from langchain_core.output_parsers import StrOutputParser
from hdbcli import dbapi

from context_retriever import retrieve_context, format_context
from rag_prompts import RAG_PROMPT


def rag_query(
    conn: dbapi.Connection,
    user_query: str,
    embedding_model,
    llm,
    table_name: str = "VECTOR_STORE",
    top_k: int = 5,
    source_filter: str = None,
    min_score: float = 0.0,
    prompt=None,
) -> dict:
    """
    Single-turn RAG: query → retrieve → answer.

    Args:
        conn            : hdbcli Connection
        user_query      : user's question (plain English)
        embedding_model : embedding model (from hana_vector_store/embedding_setup.py)
        llm             : LangChain LLM (from llm_setup.py)
        table_name      : HANA vector table to search
        top_k           : number of context chunks to use (default: 5)
        source_filter   : optional — limit search to one source file/URL
        min_score       : optional — minimum similarity score (0.0–1.0)
        prompt          : optional — swap in a different prompt (from rag_prompts.py)

    Returns:
        {
            "answer":   "<LLM answer>",
            "context":  "<formatted context string>",
            "sources":  [{"rank", "source_name", "source_type", "chunk_index", "score"}],
            "chunks":   [<raw chunk dicts>]
        }
    """
    # Step 1: Retrieve chunks from HANA
    chunks  = retrieve_context(conn, user_query, embedding_model, table_name,
                               top_k, source_filter, min_score)

    # Step 2: Format into context block
    context = format_context(chunks)

    # Step 3: Run LLM chain
    active_prompt = prompt or RAG_PROMPT
    chain         = active_prompt | llm | StrOutputParser()
    answer        = chain.invoke({"context": context, "user_query": user_query})

    # Step 4: Build source citations
    sources = [
        {
            "rank":        c["rank"],
            "source_name": c["source_name"],
            "source_type": c["source_type"],
            "chunk_index": c["chunk_index"],
            "score":       c["score"],
        }
        for c in chunks
    ]

    return {
        "answer":  answer.strip(),
        "context": context,
        "sources": sources,
        "chunks":  chunks,
    }


if __name__ == "__main__":
    from connect_env import connect
    from embedding_setup import get_embedding_model
    from llm_setup import get_llm

    conn  = connect()
    model = get_embedding_model()
    llm   = get_llm()

    # ── Change to your question and table ────────────────
    QUESTION = "What is SAP HANA Cloud?"
    TABLE    = "VECTOR_STORE"
    # ─────────────────────────────────────────────────────

    result = rag_query(conn, QUESTION, model, llm, table_name=TABLE, top_k=5, min_score=0.5)

    print("\n── Answer ─────────────────────────────")
    print(result["answer"])

    print(f"\n── Sources used ({len(result['sources'])}) ─────────────")
    for s in result["sources"]:
        print(f"  [{s['rank']}] {s['source_name']} | score: {s['score']}")

    conn.close()
