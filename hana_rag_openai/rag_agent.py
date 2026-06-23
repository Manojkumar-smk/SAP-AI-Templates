"""
============================================================
MINI TEMPLATE — RAG Agent (OpenAI version)
============================================================
Full RAG pipeline using OpenAI API directly.

Difference from hana_rag/rag_agent.py:
  - Imports llm_setup from THIS folder (OpenAI version)
  - Imports embedding from hana_vector_store_openai/ (OpenAI version)
  Everything else (prompts, memory, retrieval logic) is identical.

Methods:
  agent.ask("question")    → one-shot Q&A, no history
  agent.chat("question")   → conversational Q&A with memory
  agent.clear_memory()     → start a new conversation session
  agent.get_history()      → see current conversation history
============================================================
"""

import os, sys, pathlib

# ── OpenAI versions of dependencies ──────────────────────
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store_openai"))  # ← OpenAI embedding
# ─────────────────────────────────────────────────────────

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from hdbcli import dbapi

from llm_setup import get_llm
from embedding_setup import get_embedding_model           # from hana_vector_store_openai
from context_retriever import retrieve_context, format_context
from rag_pipeline import rag_query
from conversation_memory import ChatMemory
from rag_prompts import CONVERSATIONAL_RAG_PROMPT

load_dotenv()


class RAGAgent:
    """
    Conversational RAG agent — OpenAI API version.

    Usage:
        from connect_env import connect
        from rag_agent import RAGAgent

        conn  = connect()
        agent = RAGAgent(conn, table_name="VECTOR_STORE")

        # One-shot Q&A
        result = agent.ask("What is SAP HANA Cloud?")
        print(result["answer"])

        # Multi-turn conversation
        agent.chat("What are the features?")
        agent.chat("How does vector search work?")   # follow-up with memory

        agent.clear_memory()
    """

    def __init__(
        self,
        conn: dbapi.Connection,
        table_name: str = None,
        llm=None,
        embedding_model=None,
        top_k: int = 5,
        min_score: float = 0.0,
        memory_window: int = 5,
    ):
        self.conn            = conn
        self.table_name      = table_name or os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
        self.llm             = llm or get_llm()
        self.embedding_model = embedding_model or get_embedding_model()
        self.top_k           = top_k
        self.min_score       = min_score
        self.memory          = ChatMemory(window=memory_window)

        print(f"✅ RAGAgent ready (OpenAI) | table={self.table_name} | top_k={top_k}")

    def ask(self, user_query: str, source_filter: str = None, top_k: int = None) -> dict:
        """
        One-shot RAG — no conversation history.
        Returns: {"answer", "sources", "context", "chunks"}
        """
        return rag_query(
            conn=self.conn,
            user_query=user_query,
            embedding_model=self.embedding_model,
            llm=self.llm,
            table_name=self.table_name,
            top_k=top_k or self.top_k,
            source_filter=source_filter,
            min_score=self.min_score,
        )

    def chat(self, user_query: str, source_filter: str = None, top_k: int = None) -> dict:
        """
        Conversational RAG — uses rolling memory for follow-up questions.
        Returns: {"answer", "sources", "chat_history"}
        """
        chat_history = self.memory.get_history_string()

        chunks  = retrieve_context(
            self.conn, user_query, self.embedding_model, self.table_name,
            top_k or self.top_k, source_filter, self.min_score
        )
        context = format_context(chunks)

        chain  = CONVERSATIONAL_RAG_PROMPT | self.llm | StrOutputParser()
        answer = chain.invoke({
            "chat_history": chat_history,
            "context":      context,
            "user_query":   user_query,
        }).strip()

        self.memory.save(user_query, answer)

        return {
            "answer":       answer,
            "sources":      [{"rank": c["rank"], "source_name": c["source_name"],
                              "source_type": c["source_type"], "score": c["score"]} for c in chunks],
            "chat_history": chat_history,
        }

    def clear_memory(self) -> None:
        """Reset conversation memory."""
        self.memory.clear()

    def get_history(self) -> str:
        """Return current conversation history as formatted string."""
        return self.memory.get_history_string()


if __name__ == "__main__":
    from connect_env import connect

    conn  = connect()
    agent = RAGAgent(conn, table_name="VECTOR_STORE", top_k=5, min_score=0.5)

    # ── Single-turn Q&A ──────────────────────────────────
    result = agent.ask("What is SAP HANA Cloud?")
    print(f"\nAnswer: {result['answer']}")
    for s in result["sources"]:
        print(f"  [{s['rank']}] {s['source_name']} | score: {s['score']}")

    # ── Multi-turn ───────────────────────────────────────
    agent.chat("What are the key features?")
    agent.chat("How does vector search work in that context?")

    conn.close()
