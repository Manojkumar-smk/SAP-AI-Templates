"""
============================================================
MINI TEMPLATE — ChatbotConfig for OpenAI (Direct API)
============================================================
Use this when: you want to configure the chatbot using
OpenAI API directly instead of SAP Gen AI Hub.

Difference from sap_chatbot/chatbot_config.py:
  SAP version  → llm_deployment_id + embedding_deployment_id
  This version → OPENAI_API_KEY only (no deployment IDs needed)

Everything else (modes, memory, RAG, SQL settings) is identical.

Setup:
  pip install python-dotenv
============================================================
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ChatbotConfig:
    """
    Single config object for the OpenAI-powered SAP chatbot.

    ── LLM ───────────────────────────────────────────────
    llm_model     : OpenAI model name
                    "gpt-4o-mini" | "gpt-4o" | "gpt-4-turbo"
    temperature   : 0.0 = precise/factual, 1.0 = creative
    max_tokens    : max tokens in LLM response

    ── Memory ────────────────────────────────────────────
    memory_window : past conversation turns to keep (0 = stateless)

    ── RAG (HANA Vector Search) ──────────────────────────
    enable_rag          : True to enable RAG retrieval
    embedding_model     : OpenAI embedding model name
    vector_table        : HANA table with stored vectors
    rag_top_k           : chunks to retrieve per query
    rag_min_score       : minimum cosine similarity (0.0–1.0)
    rag_source_filter   : optional — limit search to one source

    ── SQL (HANA Query) ──────────────────────────────────
    enable_sql    : True to enable AI-generated SQL queries
    sql_tables    : list of HANA table names to query
    sql_schema    : HANA schema name (optional)

    ── Persona ───────────────────────────────────────────
    system_prompt : chatbot personality and rules
    bot_name      : display name for logs
    """

    # LLM (no deployment_id needed for OpenAI direct)
    llm_model:    str   = "gpt-4o-mini"
    temperature:  float = 0.1
    max_tokens:   int   = 1024

    # Memory
    memory_window: int = 10

    # RAG
    enable_rag:         bool         = False
    embedding_model:    str          = "text-embedding-3-small"
    vector_table:       str          = "VECTOR_STORE"
    rag_top_k:          int          = 5
    rag_min_score:      float        = 0.5
    rag_source_filter:  Optional[str] = None

    # SQL
    enable_sql:   bool          = False
    sql_tables:   list          = field(default_factory=list)
    sql_schema:   Optional[str] = None

    # Persona
    system_prompt: str = (
        "You are a helpful SAP AI assistant. "
        "Answer clearly and concisely. "
        "If you don't know something, say so honestly."
    )
    bot_name: str = "SAP AI Assistant"

    def __post_init__(self):
        if not self.vector_table:
            self.vector_table = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")

    def mode(self) -> str:
        parts = []
        if self.enable_rag: parts.append("RAG")
        if self.enable_sql: parts.append("SQL")
        return "+".join(parts) if parts else "GENERAL"


if __name__ == "__main__":
    # GENERAL
    c = ChatbotConfig(system_prompt="You are a SAP Basis assistant.")
    print(f"Mode: {c.mode()} | Model: {c.llm_model}")

    # RAG
    c = ChatbotConfig(enable_rag=True, vector_table="VECTOR_STORE")
    print(f"Mode: {c.mode()} | Embedding: {c.embedding_model}")

    # SQL
    c = ChatbotConfig(enable_sql=True, sql_tables=["SALES_ORDERS"])
    print(f"Mode: {c.mode()} | Tables: {c.sql_tables}")

    # FULL
    c = ChatbotConfig(enable_rag=True, enable_sql=True, sql_tables=["ORDERS"])
    print(f"Mode: {c.mode()}")
