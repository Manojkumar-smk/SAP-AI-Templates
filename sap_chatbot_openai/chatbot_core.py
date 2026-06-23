"""
============================================================
MINI TEMPLATE — SAPChatbot Core (OpenAI version)
============================================================
Use this when: you want the full chatbot (GENERAL/RAG/SQL/FULL
modes) using OpenAI API instead of SAP Gen AI Hub.

Difference from sap_chatbot/chatbot_core.py:
  - Imports build_llm / build_embedding_model from THIS folder
  - sys.path points to hana_vector_store_openai/ (not hana_vector_store/)
    so RAG mode uses the OpenAI embedding stored in HANA
  - Everything else (modes, memory, routing, history) is identical

Usage:
    from chatbot_config import ChatbotConfig
    from chatbot_core import SAPChatbot

    config = ChatbotConfig(enable_rag=True, vector_table="VECTOR_STORE")
    bot = SAPChatbot(conn, config)
    result = bot.chat("What is SAP HANA?")
    print(result["answer"])
============================================================
"""

import os
import sys
import pathlib

# ── Cross-folder imports ──────────────────────────────────
#    hana_db_connection → for HANA connection utilities
#    hana_vector_store_openai → OpenAI embeddings stored in HANA
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store_openai"))  # ← KEY: OpenAI version
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_ai_query_openai"))
# ─────────────────────────────────────────────────────────

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

from chatbot_config import ChatbotConfig
from llm_setup import build_llm, build_embedding_model
from prompt_builder import build_prompt
from rag_retriever import rag_retrieve
from sql_retriever import sql_retrieve

load_dotenv()


class SAPChatbot:
    """
    Multi-mode chatbot — OpenAI API version.

    Modes (set via ChatbotConfig):
      GENERAL  → plain LLM conversation
      RAG      → LLM + HANA vector search for document context
      SQL      → LLM + AI-generated HANA SQL for structured data
      RAG+SQL  → all three combined

    Args:
        conn   : hdbcli dbapi.Connection to HANA
        config : ChatbotConfig instance

    Returns from chat():
        {
          "answer"   : str,
          "sources"  : list[dict],  # RAG sources
          "sql_used" : str | None,  # SQL query if mode=SQL
          "mode"     : str,         # GENERAL / RAG / SQL / RAG+SQL
          "turn"     : int,
        }
    """

    def __init__(self, conn, config: ChatbotConfig = None):
        self.conn   = conn
        self.config = config or ChatbotConfig()

        self.llm             = build_llm(self.config)
        self.embedding_model = build_embedding_model(self.config) if self.config.enable_rag else None
        self.history         = []     # list of (human_msg, ai_msg) tuples
        self.turn            = 0

        print(f"✅ SAPChatbot (OpenAI) ready | mode={self.config.mode()} | model={self.config.llm_model}")

    # ── Public API ────────────────────────────────────────

    def chat(self, user_message: str) -> dict:
        """
        Send a message and get a response.

        Returns dict with answer, sources, sql_used, mode, turn.
        """
        self.turn += 1

        # ── RAG retrieval ────────────────────────────────
        rag_context = ""
        sources     = []
        if self.config.enable_rag and self.embedding_model:
            rag_context, sources = rag_retrieve(
                conn=self.conn,
                user_query=user_message,
                embedding_model=self.embedding_model,
                table_name=self.config.vector_table,
                top_k=self.config.rag_top_k,
                min_score=self.config.rag_min_score,
                source_filter=self.config.rag_source_filter,
            )

        # ── SQL retrieval ─────────────────────────────────
        sql_result = ""
        sql_used   = None
        if self.config.enable_sql and self.config.sql_tables:
            sql_result, sql_used = sql_retrieve(
                conn=self.conn,
                user_query=user_message,
                llm=self.llm,
                tables=self.config.sql_tables,
                schema=self.config.sql_schema,
            )

        # ── Prompt + chain ────────────────────────────────
        has_rag = bool(rag_context)
        has_sql = bool(sql_result)
        prompt  = build_prompt(self.config, has_rag=has_rag, has_sql=has_sql)
        chain   = prompt | self.llm | StrOutputParser()

        invoke_args = {
            "system_prompt": self.config.system_prompt,
            "chat_history":  self._get_history_window(),
            "user_message":  user_message,
        }
        if has_rag: invoke_args["rag_context"] = rag_context
        if has_sql: invoke_args["sql_result"]  = sql_result

        answer = chain.invoke(invoke_args).strip()

        # ── Save history ──────────────────────────────────
        self.history.append((user_message, answer))

        return {
            "answer":   answer,
            "sources":  sources,
            "sql_used": sql_used,
            "mode":     self.config.mode(),
            "turn":     self.turn,
        }

    def reset(self) -> None:
        """Clear conversation history."""
        self.history = []
        self.turn    = 0
        print("🔄 Conversation reset.")

    def get_history(self) -> list:
        """Return full conversation history as list of (human, ai) tuples."""
        return self.history.copy()

    def print_history(self) -> None:
        """Pretty-print conversation history."""
        if not self.history:
            print("(no history)")
            return
        for i, (human, ai) in enumerate(self.history, 1):
            print(f"\n[Turn {i}]")
            print(f"  You: {human}")
            print(f"  Bot: {ai}")

    # ── Private helpers ───────────────────────────────────

    def _get_history_window(self) -> list:
        """Return last N turns as LangChain message objects."""
        window = self.history[-self.config.memory_window:]
        messages = []
        for human, ai in window:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))
        return messages


if __name__ == "__main__":
    # ── Quick smoke test ──────────────────────────────────
    import sys
    sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
    from connect_env import connect

    conn   = connect()
    config = ChatbotConfig(
        llm_model="gpt-4o-mini",
        memory_window=5,
    )
    bot = SAPChatbot(conn, config)

    r = bot.chat("What is SAP HANA Cloud?")
    print(f"\nAnswer: {r['answer']}")
    print(f"Mode: {r['mode']} | Turn: {r['turn']}")

    conn.close()
