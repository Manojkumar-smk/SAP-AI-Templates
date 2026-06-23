"""
============================================================
MINI TEMPLATE — RAG Agent (Full Pipeline)
============================================================
Use this when: you want everything in one class —
single-turn Q&A, multi-turn conversation, and source citations.

Combines:
  llm_setup + embedding_setup + context_retriever
  + rag_pipeline + conversation_memory + rag_prompts

Methods:
  agent.ask("question")    → one-shot Q&A, no history
  agent.chat("question")   → conversational Q&A with memory
  agent.clear_memory()     → start a new conversation session
  agent.get_history()      → see current conversation history

Setup:
  pip install -r requirements.txt
============================================================
"""

import os, sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store"))

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from hdbcli import dbapi

from llm_setup import get_llm
from embedding_setup import get_embedding_model
from context_retriever import retrieve_context, format_context
from rag_pipeline import rag_query
from conversation_memory import ChatMemory
from rag_prompts import CONVERSATIONAL_RAG_PROMPT

load_dotenv()


class RAGAgent:
    """
    Conversational RAG agent backed by HANA Vector Store.

    Usage:
        from connect_env import connect
        from rag_agent import RAGAgent

        conn  = connect()
        agent = RAGAgent(conn, table_name="VECTOR_STORE")

        # One-shot Q&A
        result = agent.ask("What is SAP HANA Cloud?")
        print(result["answer"])
        print(result["sources"])

        # Multi-turn conversation
        r1 = agent.chat("What are the key features of HANA Vector Engine?")
        r2 = agent.chat("How does cosine similarity work in that context?")  # "that" resolved via history
        r3 = agent.chat("Summarize what we discussed.")

        # Reset conversation
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
        """
        Args:
            conn            : hdbcli Connection
            table_name      : HANA vector table to search
            llm             : optional — defaults to SAP Gen AI Hub (gpt-4o-mini)
            embedding_model : optional — defaults to SAP Gen AI Hub embedding
            top_k           : context chunks per query (default: 5)
            min_score       : minimum similarity score to include chunk (default: 0.0)
            memory_window   : conversation turns to remember (default: 5)
        """
        self.conn            = conn
        self.table_name      = table_name or os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
        self.llm             = llm or get_llm()
        self.embedding_model = embedding_model or get_embedding_model()
        self.top_k           = top_k
        self.min_score       = min_score
        self.memory          = ChatMemory(window=memory_window)

        print(f"✅ RAGAgent ready | table={self.table_name} | top_k={top_k} | min_score={min_score}")

    # ── Single-turn Q&A ───────────────────────────────────
    def ask(
        self,
        user_query: str,
        source_filter: str = None,
        top_k: int = None,
    ) -> dict:
        """
        One-shot RAG — no conversation history.

        Returns:
            {
                "answer":   "<LLM answer>",
                "sources":  [{"rank", "source_name", "source_type", "chunk_index", "score"}],
                "context":  "<formatted context string>",
                "chunks":   [<raw chunk dicts>]
            }
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

    # ── Multi-turn conversational Q&A ─────────────────────
    def chat(
        self,
        user_query: str,
        source_filter: str = None,
        top_k: int = None,
    ) -> dict:
        """
        Conversational RAG — uses rolling memory for follow-up questions.
        Each turn is automatically saved to memory.

        Returns:
            {
                "answer":       "<LLM answer>",
                "sources":      [{"rank", "source_name", "source_type", "score"}],
                "chat_history": "<formatted history string used in prompt>"
            }
        """
        chat_history = self.memory.get_history_string()

        # Retrieve context
        chunks  = retrieve_context(
            self.conn, user_query, self.embedding_model, self.table_name,
            top_k or self.top_k, source_filter, self.min_score
        )
        context = format_context(chunks)

        # Run conversational LLM chain
        chain  = CONVERSATIONAL_RAG_PROMPT | self.llm | StrOutputParser()
        answer = chain.invoke({
            "chat_history": chat_history,
            "context":      context,
            "user_query":   user_query,
        }).strip()

        # Save this turn to memory
        self.memory.save(user_query, answer)

        sources = [
            {
                "rank":        c["rank"],
                "source_name": c["source_name"],
                "source_type": c["source_type"],
                "score":       c["score"],
            }
            for c in chunks
        ]

        return {
            "answer":       answer,
            "sources":      sources,
            "chat_history": chat_history,
        }

    def clear_memory(self) -> None:
        """Reset conversation memory (start a new session)."""
        self.memory.clear()

    def get_history(self) -> str:
        """Return current conversation history as a formatted string."""
        return self.memory.get_history_string()


if __name__ == "__main__":
    from connect_env import connect

    conn  = connect()
    agent = RAGAgent(
        conn=conn,
        table_name="VECTOR_STORE",
        top_k=5,
        min_score=0.5,
        memory_window=5,
    )

    # ── Example A: Single-turn Q&A ────────────────────────
    print("\n── Single-turn Q&A ──────────────────────")
    result = agent.ask("What is SAP HANA Cloud?")
    print(f"Answer: {result['answer']}")
    print(f"Sources:")
    for s in result["sources"]:
        print(f"  [{s['rank']}] {s['source_name']} | score: {s['score']}")

    # ── Example B: Multi-turn conversation ────────────────
    print("\n── Multi-turn Conversation ──────────────")
    questions = [
        "What are the key features of HANA Vector Engine?",
        "How does cosine similarity work in that context?",
        "Give me a brief summary of what we discussed.",
    ]
    for q in questions:
        print(f"\nUser: {q}")
        r = agent.chat(q)
        print(f"Assistant: {r['answer']}")

    # ── Example C: Source-filtered Q&A ───────────────────
    # result = agent.ask("Main points?", source_filter="report.pdf", top_k=3)

    conn.close()
