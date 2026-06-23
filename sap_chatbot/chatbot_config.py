"""
============================================================
MINI TEMPLATE — ChatbotConfig (All Parameters in One Place)
============================================================
Use this when: you want to configure your chatbot's behaviour
without touching any other file. All settings live here.

ChatbotConfig drives the entire SAPChatbot — change this
dataclass to switch modes, models, memory, and personas.

Four modes (set via flags):
  GENERAL → LLM + memory only (no DB)
  RAG     → LLM + HANA Vector search + memory
  SQL     → LLM + HANA SQL query + memory
  FULL    → RAG + SQL + memory combined

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
    Single config object that drives the entire chatbot.
    Pass this to SAPChatbot() — no other setup needed.

    ── LLM ───────────────────────────────────────────────
    llm_model         : model name via SAP Gen AI Hub
                        "gpt-4o-mini" | "gpt-4o" | "gpt-4"
    llm_deployment_id : SAP AI Core deployment ID (chat model)
    temperature       : 0.0 = precise/factual, 1.0 = creative
    max_tokens        : max tokens in LLM response

    ── Memory ────────────────────────────────────────────
    memory_window     : past conversation turns to keep (0 = stateless)

    ── RAG (HANA Vector Search) ──────────────────────────
    enable_rag              : True to enable RAG retrieval
    embedding_deployment_id : SAP AI Core deployment ID (embedding model)
    embedding_model         : embedding model name
    vector_table            : HANA table with stored vectors (from hana_vector_store)
    rag_top_k               : chunks to retrieve per query
    rag_min_score           : minimum cosine similarity score (0.0–1.0)
    rag_source_filter       : optional — limit search to one source file/URL

    ── SQL (HANA Query) ──────────────────────────────────
    enable_sql        : True to enable AI-generated SQL queries
    sql_tables        : list of HANA table names the chatbot can query
    sql_schema        : HANA schema name (optional)

    ── Persona ───────────────────────────────────────────
    system_prompt     : chatbot personality and rules
    bot_name          : display name for logs
    """

    # LLM
    llm_model:          str   = "gpt-4o-mini"
    llm_deployment_id:  str   = None
    temperature:        float = 0.1
    max_tokens:         int   = 1024

    # Memory
    memory_window:      int   = 10       # 0 = stateless

    # RAG
    enable_rag:               bool         = False
    embedding_deployment_id:  str          = None
    embedding_model:          str          = "text-embedding-ada-002"
    vector_table:             str          = "VECTOR_STORE"
    rag_top_k:                int          = 5
    rag_min_score:            float        = 0.5
    rag_source_filter:        Optional[str] = None

    # SQL
    enable_sql:         bool          = False
    sql_tables:         list          = field(default_factory=list)
    sql_schema:         Optional[str] = None

    # Persona
    system_prompt: str = (
        "You are a helpful SAP AI assistant. "
        "Answer clearly and concisely. "
        "If you don't know something, say so honestly."
    )
    bot_name: str = "SAP AI Assistant"

    def __post_init__(self):
        # Fall back to .env values if not explicitly passed
        if not self.llm_deployment_id:
            self.llm_deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
        if not self.embedding_deployment_id:
            self.embedding_deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID")
        if not self.vector_table:
            self.vector_table = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")

    def mode(self) -> str:
        """Return active mode string for display/logging."""
        parts = []
        if self.enable_rag: parts.append("RAG")
        if self.enable_sql: parts.append("SQL")
        return "+".join(parts) if parts else "GENERAL"


if __name__ == "__main__":
    # ── General chatbot config ────────────────────────────
    general = ChatbotConfig(
        system_prompt = "You are a helpful SAP Basis assistant.",
        memory_window = 10,
    )
    print(f"Mode: {general.mode()} | Model: {general.llm_model}")

    # ── RAG chatbot config ────────────────────────────────
    rag = ChatbotConfig(
        enable_rag    = True,
        vector_table  = "VECTOR_STORE",
        rag_top_k     = 5,
        rag_min_score = 0.5,
    )
    print(f"Mode: {rag.mode()} | Table: {rag.vector_table}")

    # ── SQL chatbot config ────────────────────────────────
    sql = ChatbotConfig(
        enable_sql  = True,
        sql_tables  = ["SALES_ORDERS", "CUSTOMERS"],
    )
    print(f"Mode: {sql.mode()} | Tables: {sql.sql_tables}")

    # ── Full chatbot config ───────────────────────────────
    full = ChatbotConfig(
        enable_rag  = True,
        enable_sql  = True,
        sql_tables  = ["SALES_ORDERS"],
        vector_table = "VECTOR_STORE",
    )
    print(f"Mode: {full.mode()}")
