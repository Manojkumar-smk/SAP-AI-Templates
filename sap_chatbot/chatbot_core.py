"""
============================================================
MINI TEMPLATE — SAPChatbot Core
============================================================
Use this when: you want the main chatbot class that ties
everything together — config, LLM, RAG, SQL, memory.

Methods:
  bot.chat("message")   → send a message, get a response dict
  bot.reset()           → clear conversation history
  bot.get_history()     → list of {"role", "content"} dicts
  bot.print_history()   → print conversation to console
  bot.get_turn_count()  → how many turns so far

Response dict from chat():
  {
    "answer"   : str  — the chatbot's reply
    "sources"  : list — RAG citations (empty if RAG disabled)
    "sql_used" : str  — SQL query run (empty if SQL disabled)
    "mode"     : str  — "GENERAL" | "RAG" | "SQL" | "RAG+SQL"
    "turn"     : int  — conversation turn number
  }

Setup:
  pip install -r requirements.txt
============================================================
"""

import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_vector_store"))
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_ai_query"))

from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from hdbcli import dbapi

from chatbot_config import ChatbotConfig
from llm_setup import build_llm, build_embedding_model
from prompt_builder import build_prompt
from rag_retriever import rag_retrieve
from sql_retriever import sql_retrieve


class SAPChatbot:
    """
    Fully configurable SAP AI chatbot.

    Usage:
        from connect_env import connect
        from chatbot_config import ChatbotConfig
        from chatbot_core import SAPChatbot

        conn   = connect()
        config = ChatbotConfig(
            enable_rag = True,
            enable_sql = True,
            sql_tables = ["SALES_ORDERS"],
        )
        bot = SAPChatbot(config, conn=conn)

        response = bot.chat("Show me top 5 customers by revenue")
        print(response["answer"])
        print(response["sources"])
        print(response["sql_used"])
    """

    def __init__(self, config: ChatbotConfig, conn: dbapi.Connection = None):
        """
        Args:
            config : ChatbotConfig — all settings
            conn   : hdbcli Connection (required if enable_rag or enable_sql is True)
        """
        self.config   = config
        self.conn     = conn
        self._history = []   # list of HumanMessage / AIMessage

        if (config.enable_rag or config.enable_sql) and conn is None:
            raise ValueError(
                "A HANA connection is required when enable_rag or enable_sql is True.\n"
                "Pass conn=connect() when creating SAPChatbot."
            )

        self._llm      = build_llm(config)
        self._embedder = build_embedding_model(config) if config.enable_rag else None

        if config.enable_sql and not config.sql_tables:
            raise ValueError("sql_tables must not be empty when enable_sql is True.")

        print(f"✅ {config.bot_name} ready | Mode: {config.mode()} | Memory: {config.memory_window} turns")

    def chat(self, user_message: str) -> dict:
        """
        Send a message and receive a response.

        Returns:
            {
                "answer"   : chatbot reply text
                "sources"  : RAG source citations (empty list if RAG disabled)
                "sql_used" : SQL query that was run (empty string if SQL disabled)
                "mode"     : active mode for this turn
                "turn"     : conversation turn number
            }
        """
        rag_context = ""
        sql_result  = ""
        sql_used    = ""
        sources     = []
        mode_parts  = []

        # RAG retrieval
        if self.config.enable_rag and self._embedder:
            rag_context, sources = rag_retrieve(self.conn, user_message, self.config, self._embedder)
            if rag_context:
                mode_parts.append("RAG")

        # SQL retrieval
        if self.config.enable_sql:
            sql_result, sql_used = sql_retrieve(self.conn, user_message, self.config, self._llm)
            if sql_result:
                mode_parts.append("SQL")

        if not mode_parts:
            mode_parts.append("GENERAL")

        # Build prompt dynamically
        prompt = build_prompt(self.config, has_rag=bool(rag_context), has_sql=bool(sql_result))

        prompt_vars = {
            "user_message": user_message,
            "history":      self._get_history_window(),
        }
        if rag_context:
            prompt_vars["rag_context"] = rag_context
        if sql_result:
            prompt_vars["sql_result"]  = sql_result
            prompt_vars["sql_used"]    = sql_used

        # Generate answer
        chain  = prompt | self._llm | StrOutputParser()
        answer = chain.invoke(prompt_vars).strip()

        # Save to memory
        self._history.append(HumanMessage(content=user_message))
        self._history.append(AIMessage(content=answer))

        return {
            "answer":   answer,
            "sources":  sources,
            "sql_used": sql_used,
            "mode":     "+".join(mode_parts),
            "turn":     len(self._history) // 2,
        }

    def _get_history_window(self) -> list:
        """Return the last N turns of history based on memory_window."""
        if self.config.memory_window == 0:
            return []
        return self._history[-(self.config.memory_window * 2):]

    def reset(self) -> None:
        """Clear conversation history — start a fresh session."""
        self._history = []
        print(f"🗑️  {self.config.bot_name}: conversation cleared.")

    def get_history(self) -> list[dict]:
        """Return conversation history as list of {"role", "content"} dicts."""
        return [
            {
                "role":    "user"      if isinstance(m, HumanMessage) else "assistant",
                "content": m.content,
            }
            for m in self._history
        ]

    def get_turn_count(self) -> int:
        """Return number of completed conversation turns."""
        return len(self._history) // 2

    def print_history(self) -> None:
        """Print full conversation to console."""
        print(f"\n── {self.config.bot_name} Conversation ──")
        for entry in self.get_history():
            prefix = "You      " if entry["role"] == "user" else "Assistant"
            print(f"{prefix} : {entry['content']}")
        print()


if __name__ == "__main__":
    from connect_env import connect

    conn = connect()

    config = ChatbotConfig(
        system_prompt = "You are a helpful SAP technical assistant.",
        memory_window = 5,
        # enable_rag  = True,   # uncomment to add RAG
        # enable_sql  = True,   # uncomment to add SQL
        # sql_tables  = ["CUST_TICKETS"],
    )

    bot = SAPChatbot(config, conn=conn)

    # Test a conversation
    r1 = bot.chat("What is SAP HANA Cloud?")
    print(f"[Turn {r1['turn']}] {r1['answer']}\n")

    r2 = bot.chat("How is it different from SAP HANA on-premise?")
    print(f"[Turn {r2['turn']}] {r2['answer']}\n")

    bot.print_history()
    conn.close()
