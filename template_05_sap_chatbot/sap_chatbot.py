"""
============================================================
TEMPLATE 05 — SAP AI Chatbot (Fully Configurable)
============================================================
A production-ready chatbot backed by SAP Gen AI Hub.
Everything is driven by ChatbotConfig — pass different
configs to get different chatbot behaviours.

Modes (mix and match via config flags):
  ┌──────────────────────────────────────────────────────┐
  │  GENERAL  — LLM + memory only (no DB)               │
  │  RAG      — LLM + HANA Vector search + memory       │
  │  SQL      — LLM + HANA SQL query + memory           │
  │  FULL     — RAG + SQL + memory combined              │
  └──────────────────────────────────────────────────────┘

All parameters are inputs via ChatbotConfig dataclass.
HANA connection is passed in — reuses Template 01.

Dependencies:
    pip install hdbcli hana-ml cfenv python-dotenv sap-ai-sdk-gen
                langchain langchain-core langchain-openai

Usage:
    python sap_chatbot.py
============================================================
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# ── LangChain ─────────────────────────────────────────────
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ── SAP Gen AI Hub ────────────────────────────────────────
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

# ── Template 01: HANA Connection ──────────────────────────
import sys
sys.path.append(str(Path(__file__).parent.parent / "template_01_hana_connection"))
from hana_connection import get_hana_credentials, get_dbapi_connection

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. CHATBOT CONFIG  (all parameters here)
# ─────────────────────────────────────────────

@dataclass
class ChatbotConfig:
    """
    Single config object that drives the entire chatbot behaviour.
    Pass this to SAPChatbot() — no other setup needed.

    ── LLM ───────────────────────────────────────────────────────────
    llm_model          : SAP Gen AI Hub model name
                         Options: "gpt-4o-mini" | "gpt-4o" | "gpt-4"
    llm_deployment_id  : SAP AI Core deployment ID for the chat model
    temperature        : 0.0 = precise/factual, 1.0 = creative
    max_tokens         : max tokens in LLM response

    ── Memory ────────────────────────────────────────────────────────
    memory_window      : number of past conversation turns to keep
                         0 = no memory (stateless)

    ── RAG (HANA Vector Search) ──────────────────────────────────────
    enable_rag              : set True to enable RAG retrieval
    embedding_deployment_id : SAP AI Core deployment ID for embedding model
    embedding_model         : embedding model name
    vector_table            : HANA table that stores vectors (from Template 03)
    rag_top_k               : number of chunks to retrieve per query
    rag_min_score           : minimum cosine similarity score (0.0–1.0)
    rag_source_filter       : optional — limit search to one source file/URL

    ── SQL (HANA Query) ──────────────────────────────────────────────
    enable_sql         : set True to enable AI-generated SQL queries
    sql_tables         : list of HANA table names the chatbot can query
                         e.g. ["SALES_ORDERS", "CUSTOMERS"]
    sql_schema         : HANA schema name (optional)

    ── System Prompt ─────────────────────────────────────────────────
    system_prompt      : personality and rules for the chatbot
    bot_name           : display name (used in logs and responses)
    """

    # ── LLM
    llm_model:          str   = "gpt-4o-mini"
    llm_deployment_id:  str   = None          # reads LLM_DEPLOYMENT_ID from .env if None
    temperature:        float = 0.1
    max_tokens:         int   = 1024

    # ── Memory
    memory_window:      int   = 10            # 0 = stateless

    # ── RAG
    enable_rag:               bool  = False
    embedding_deployment_id:  str   = None    # reads EMBEDDING_DEPLOYMENT_ID from .env if None
    embedding_model:          str   = "text-embedding-ada-002"
    vector_table:             str   = "VECTOR_STORE"
    rag_top_k:                int   = 5
    rag_min_score:            float = 0.5
    rag_source_filter:        Optional[str] = None

    # ── SQL
    enable_sql:         bool          = False
    sql_tables:         list          = field(default_factory=list)
    sql_schema:         Optional[str] = None

    # ── Persona
    system_prompt: str = (
        "You are a helpful SAP AI assistant. "
        "Answer clearly and concisely based on the information available. "
        "If you don't know something, say so honestly."
    )
    bot_name: str = "SAP AI Assistant"

    def __post_init__(self):
        # Fall back to .env values if not explicitly set
        if self.llm_deployment_id is None:
            self.llm_deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
        if self.embedding_deployment_id is None:
            self.embedding_deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID")
        if not self.vector_table:
            self.vector_table = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")


# ─────────────────────────────────────────────
# 2. LLM + EMBEDDING SETUP
# ─────────────────────────────────────────────

def _build_llm(config: ChatbotConfig):
    """Initialise SAP Gen AI Hub chat model from config."""
    if not config.llm_deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID is not set.\n"
            "Set it in .env or pass llm_deployment_id in ChatbotConfig."
        )
    proxy_client = get_proxy_client("gen-ai-hub")
    llm = ChatOpenAI(
        proxy_model_name=config.llm_model,
        proxy_client=proxy_client,
        deployment_id=config.llm_deployment_id,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    log.info("LLM ready: %s (temp=%.1f)", config.llm_model, config.temperature)
    return llm


def _build_embedding_model(config: ChatbotConfig):
    """Initialise SAP Gen AI Hub embedding model from config."""
    if not config.embedding_deployment_id:
        raise EnvironmentError(
            "EMBEDDING_DEPLOYMENT_ID is not set.\n"
            "Set it in .env or pass embedding_deployment_id in ChatbotConfig."
        )
    from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
    proxy_client = get_proxy_client("gen-ai-hub")
    embedder = OpenAIEmbeddings(
        proxy_model_name=config.embedding_model,
        proxy_client=proxy_client,
        deployment_id=config.embedding_deployment_id,
    )
    log.info("Embedding model ready: %s", config.embedding_model)
    return embedder


# ─────────────────────────────────────────────
# 3. HANA VECTOR SEARCH  (RAG retrieval)
# ─────────────────────────────────────────────

def _rag_retrieve(conn, user_message: str, config: ChatbotConfig, embedder) -> tuple[str, list]:
    """
    Runs a similarity search in HANA and returns formatted context + sources.

    Returns:
        context_text : str  — formatted context block for the prompt
        sources      : list — list of source dicts for the response
    """
    sys.path.append(str(Path(__file__).parent.parent / "template_03_hana_vector_store"))
    from hana_vector_store import similarity_search

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
        chunks = [c for c in chunks if c["score"] >= config.rag_min_score]

    if not chunks:
        return "", []

    lines = []
    for c in chunks:
        lines.append(f"[{c['rank']}] {c['source_name']} (score: {c['score']})\n{c['content']}")
    context_text = "\n\n".join(lines)

    sources = [
        {"rank": c["rank"], "source_name": c["source_name"],
         "source_type": c["source_type"], "score": c["score"]}
        for c in chunks
    ]
    log.info("RAG: retrieved %d chunks for query: '%s'", len(chunks), user_message[:50])
    return context_text, sources


# ─────────────────────────────────────────────
# 4. HANA SQL QUERY  (structured data retrieval)
# ─────────────────────────────────────────────

def _sql_retrieve(conn, user_message: str, config: ChatbotConfig, llm) -> tuple[str, str]:
    """
    Fetches table schema, generates SQL via LLM, executes it, returns
    a formatted result string and the SQL used.

    Returns:
        sql_result : str — table results as readable text
        sql_used   : str — the generated SQL query
    """
    sys.path.append(str(Path(__file__).parent.parent / "template_02_hana_ai_query"))
    from hana_ai_query import build_schema_context, generate_sql, execute_sql

    # Build schema context from configured tables
    tables = []
    for t in config.sql_tables:
        if isinstance(t, str):
            tables.append({"table": t, "schema": config.sql_schema} if config.sql_schema else t)
        else:
            tables.append(t)

    schema_ctx = build_schema_context(conn, tables)
    sql        = generate_sql(user_message, schema_ctx, llm)

    try:
        df         = execute_sql(conn, sql)
        sql_result = df.to_string(index=False) if not df.empty else "Query returned no rows."
        log.info("SQL: executed query, %d rows returned", len(df))
    except Exception as e:
        sql_result = f"SQL execution error: {e}"
        log.warning("SQL error: %s", e)

    return sql_result, sql


# ─────────────────────────────────────────────
# 5. PROMPT BUILDER
# ─────────────────────────────────────────────

def _build_prompt(config: ChatbotConfig, has_rag: bool, has_sql: bool) -> ChatPromptTemplate:
    """
    Dynamically builds the chat prompt based on which features are enabled.
    The system prompt in ChatbotConfig is always the base.
    """
    system_parts = [config.system_prompt]

    if has_rag:
        system_parts.append(
            "\n\nYou have access to a knowledge base. "
            "Relevant context is provided below under 'KNOWLEDGE BASE CONTEXT'. "
            "Use it to answer the user's question. "
            "If the context doesn't contain the answer, say you don't have that information."
        )

    if has_sql:
        system_parts.append(
            "\n\nYou also have access to structured data from a database. "
            "Query results are provided below under 'DATABASE RESULTS'. "
            "Use them to give precise, data-backed answers."
        )

    full_system = "".join(system_parts)

    # Build message template
    messages = [("system", full_system)]

    if has_rag:
        messages.append(("system", "KNOWLEDGE BASE CONTEXT:\n{rag_context}"))

    if has_sql:
        messages.append(("system", "DATABASE RESULTS (SQL: {sql_used}):\n{sql_result}"))

    messages.append(MessagesPlaceholder(variable_name="history"))
    messages.append(("human",  "{user_message}"))

    return ChatPromptTemplate.from_messages(messages)


# ─────────────────────────────────────────────
# 6. MAIN CHATBOT CLASS
# ─────────────────────────────────────────────

class SAPChatbot:
    """
    Fully configurable SAP AI chatbot.

    Pass a ChatbotConfig to enable/disable features.
    Pass a HANA connection (from Template 01) if RAG or SQL is enabled.

    ── Quick start ───────────────────────────────────────────────────

    # General chatbot (no DB)
    config = ChatbotConfig(
        llm_deployment_id = "your-llm-id",
        system_prompt     = "You are a helpful SAP Basis assistant.",
    )
    bot = SAPChatbot(config)
    response = bot.chat("What is SAP HANA?")

    # RAG chatbot (with vector search)
    config = ChatbotConfig(
        llm_deployment_id       = "your-llm-id",
        embedding_deployment_id = "your-embedding-id",
        enable_rag              = True,
        vector_table            = "VECTOR_STORE",
        rag_top_k               = 5,
        rag_min_score           = 0.5,
    )
    bot = SAPChatbot(config, conn=hana_conn)
    response = bot.chat("What does our refund policy say?")

    # SQL chatbot (HANA structured data)
    config = ChatbotConfig(
        llm_deployment_id = "your-llm-id",
        enable_sql        = True,
        sql_tables        = ["SALES_ORDERS", "CUSTOMERS"],
    )
    bot = SAPChatbot(config, conn=hana_conn)
    response = bot.chat("Show top 5 customers by revenue this year")

    # Full chatbot (RAG + SQL + memory)
    config = ChatbotConfig(
        llm_deployment_id       = "your-llm-id",
        embedding_deployment_id = "your-embedding-id",
        enable_rag              = True,
        enable_sql              = True,
        sql_tables              = ["SALES_ORDERS"],
        vector_table            = "VECTOR_STORE",
        memory_window           = 10,
    )
    bot = SAPChatbot(config, conn=hana_conn)
    """

    def __init__(self, config: ChatbotConfig, conn=None):
        """
        Args:
            config : ChatbotConfig — all chatbot parameters
            conn   : hdbcli Connection (required if enable_rag or enable_sql is True)
        """
        self.config  = config
        self.conn    = conn
        self._history: list = []   # internal conversation history

        # Validate DB connection if needed
        if (config.enable_rag or config.enable_sql) and conn is None:
            raise ValueError(
                "A HANA connection (conn) is required when enable_rag or enable_sql is True.\n"
                "Pass conn=get_dbapi_connection(creds) when creating SAPChatbot."
            )

        # Build LLM
        self._llm = _build_llm(config)

        # Build embedding model (only if RAG is enabled)
        self._embedder = None
        if config.enable_rag:
            self._embedder = _build_embedding_model(config)

        # Validate SQL tables
        if config.enable_sql and not config.sql_tables:
            raise ValueError(
                "sql_tables must not be empty when enable_sql is True.\n"
                "Example: sql_tables=['SALES_ORDERS', 'CUSTOMERS']"
            )

        mode = []
        if config.enable_rag: mode.append("RAG")
        if config.enable_sql: mode.append("SQL")
        if not mode:          mode.append("GENERAL")
        log.info("%s ready | Mode: %s | Memory: %d turns",
                 config.bot_name, "+".join(mode), config.memory_window)

    # ── Core chat method ──────────────────────────────────
    def chat(self, user_message: str) -> dict:
        """
        Send a message and get a response.

        Args:
            user_message : the user's input text

        Returns:
            {
                "answer"      : str   — chatbot response
                "sources"     : list  — RAG source citations (empty if RAG disabled)
                "sql_used"    : str   — SQL query run (empty if SQL disabled)
                "mode"        : str   — which mode was active for this turn
                "turn"        : int   — conversation turn number
            }
        """
        log.info("[%s] User: %s", self.config.bot_name, user_message[:80])

        rag_context = ""
        sql_result  = ""
        sql_used    = ""
        sources     = []
        mode_parts  = []

        # ── RAG retrieval ────────────────────────────────
        if self.config.enable_rag and self._embedder:
            rag_context, sources = _rag_retrieve(
                self.conn, user_message, self.config, self._embedder
            )
            if rag_context:
                mode_parts.append("RAG")

        # ── SQL retrieval ────────────────────────────────
        if self.config.enable_sql:
            sql_result, sql_used = _sql_retrieve(
                self.conn, user_message, self.config, self._llm
            )
            if sql_result:
                mode_parts.append("SQL")

        if not mode_parts:
            mode_parts.append("GENERAL")

        # ── Build prompt dynamically ─────────────────────
        has_rag = bool(rag_context)
        has_sql = bool(sql_result)
        prompt  = _build_prompt(self.config, has_rag, has_sql)

        # ── Assemble prompt variables ────────────────────
        prompt_vars = {
            "user_message": user_message,
            "history":      self._get_history_window(),
        }
        if has_rag:
            prompt_vars["rag_context"] = rag_context
        if has_sql:
            prompt_vars["sql_result"]  = sql_result
            prompt_vars["sql_used"]    = sql_used

        # ── Call LLM ─────────────────────────────────────
        chain  = prompt | self._llm | StrOutputParser()
        answer = chain.invoke(prompt_vars).strip()

        # ── Update memory ────────────────────────────────
        self._history.append(HumanMessage(content=user_message))
        self._history.append(AIMessage(content=answer))

        turn = len(self._history) // 2
        log.info("[%s] Turn %d | Mode: %s | Answer: %s...",
                 self.config.bot_name, turn, "+".join(mode_parts), answer[:60])

        return {
            "answer":   answer,
            "sources":  sources,
            "sql_used": sql_used,
            "mode":     "+".join(mode_parts),
            "turn":     turn,
        }

    # ── Memory helpers ────────────────────────────────────
    def _get_history_window(self) -> list:
        """Returns the last N turns of history based on memory_window config."""
        if self.config.memory_window == 0:
            return []
        max_messages = self.config.memory_window * 2   # each turn = 2 messages
        return self._history[-max_messages:]

    def reset(self) -> None:
        """Clears conversation history — starts a fresh session."""
        self._history = []
        log.info("[%s] Conversation reset.", self.config.bot_name)

    def get_history(self) -> list[dict]:
        """
        Returns the full conversation history as a list of dicts.
        Useful for displaying chat logs or saving sessions.
        """
        result = []
        for msg in self._history:
            role    = "user"      if isinstance(msg, HumanMessage) else "assistant"
            result.append({"role": role, "content": msg.content})
        return result

    def get_turn_count(self) -> int:
        """Returns number of completed conversation turns."""
        return len(self._history) // 2

    def print_history(self) -> None:
        """Prints the full conversation history to console."""
        print(f"\n── Conversation History: {self.config.bot_name} ──")
        for entry in self.get_history():
            prefix = "You      " if entry["role"] == "user" else "Assistant"
            print(f"{prefix} : {entry['content']}")
        print()


# ─────────────────────────────────────────────
# 7. PRESET FACTORY FUNCTIONS
#    Convenience wrappers for common use cases
# ─────────────────────────────────────────────

def create_general_chatbot(
    llm_deployment_id: str,
    system_prompt:     str = "You are a helpful SAP AI assistant.",
    llm_model:         str = "gpt-4o-mini",
    temperature:       float = 0.1,
    memory_window:     int = 10,
) -> SAPChatbot:
    """
    General-purpose chatbot — no HANA DB required.
    Good for FAQ bots, support bots, general assistants.
    """
    config = ChatbotConfig(
        llm_deployment_id = llm_deployment_id,
        llm_model         = llm_model,
        temperature       = temperature,
        memory_window     = memory_window,
        system_prompt     = system_prompt,
        enable_rag        = False,
        enable_sql        = False,
    )
    return SAPChatbot(config)


def create_rag_chatbot(
    conn,
    llm_deployment_id:       str,
    embedding_deployment_id: str,
    vector_table:            str   = "VECTOR_STORE",
    system_prompt:           str   = "You are a helpful SAP AI assistant. Answer based only on the provided context.",
    llm_model:               str   = "gpt-4o-mini",
    rag_top_k:               int   = 5,
    rag_min_score:           float = 0.5,
    memory_window:           int   = 10,
    rag_source_filter:       str   = None,
) -> SAPChatbot:
    """
    RAG chatbot — answers from documents stored in HANA Vector Store.
    Requires conn from Template 01 and vectors loaded via Template 03.
    """
    config = ChatbotConfig(
        llm_deployment_id       = llm_deployment_id,
        embedding_deployment_id = embedding_deployment_id,
        llm_model               = llm_model,
        system_prompt           = system_prompt,
        enable_rag              = True,
        vector_table            = vector_table,
        rag_top_k               = rag_top_k,
        rag_min_score           = rag_min_score,
        rag_source_filter       = rag_source_filter,
        memory_window           = memory_window,
        enable_sql              = False,
    )
    return SAPChatbot(config, conn=conn)


def create_sql_chatbot(
    conn,
    llm_deployment_id: str,
    sql_tables:        list,
    system_prompt:     str   = "You are a data analyst assistant. Answer based on database query results.",
    llm_model:         str   = "gpt-4o-mini",
    sql_schema:        str   = None,
    memory_window:     int   = 10,
) -> SAPChatbot:
    """
    SQL chatbot — answers questions by querying HANA tables.
    Requires conn from Template 01. Uses Template 02 for SQL generation.
    """
    config = ChatbotConfig(
        llm_deployment_id = llm_deployment_id,
        llm_model         = llm_model,
        system_prompt     = system_prompt,
        enable_sql        = True,
        sql_tables        = sql_tables,
        sql_schema        = sql_schema,
        memory_window     = memory_window,
        enable_rag        = False,
    )
    return SAPChatbot(config, conn=conn)


def create_full_chatbot(
    conn,
    llm_deployment_id:       str,
    embedding_deployment_id: str,
    sql_tables:              list,
    vector_table:            str   = "VECTOR_STORE",
    system_prompt:           str   = (
        "You are a comprehensive SAP AI assistant with access to both "
        "a knowledge base and live database data. Use both to give the best answer."
    ),
    llm_model:               str   = "gpt-4o-mini",
    rag_top_k:               int   = 5,
    rag_min_score:           float = 0.5,
    sql_schema:              str   = None,
    memory_window:           int   = 10,
) -> SAPChatbot:
    """
    Full chatbot — RAG + SQL + memory combined.
    The most powerful mode: answers from both documents and structured DB data.
    """
    config = ChatbotConfig(
        llm_deployment_id       = llm_deployment_id,
        embedding_deployment_id = embedding_deployment_id,
        llm_model               = llm_model,
        system_prompt           = system_prompt,
        enable_rag              = True,
        vector_table            = vector_table,
        rag_top_k               = rag_top_k,
        rag_min_score           = rag_min_score,
        enable_sql              = True,
        sql_tables              = sql_tables,
        sql_schema              = sql_schema,
        memory_window           = memory_window,
    )
    return SAPChatbot(config, conn=conn)


# ─────────────────────────────────────────────
# 8. MAIN — run standalone (interactive CLI)
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SAP AI Chatbot — Interactive Demo")
    print("=" * 60)

    # ── Step 1: Connect to HANA (only needed for RAG / SQL modes) ─
    creds = get_hana_credentials()
    conn  = get_dbapi_connection(creds)

    # ── Step 2: Choose your chatbot mode ─────────────────────────

    # ── Option A: General chatbot (no DB needed) ──────────────────
    bot = create_general_chatbot(
        llm_deployment_id = os.getenv("LLM_DEPLOYMENT_ID"),
        system_prompt     = "You are a helpful SAP technical assistant.",
        memory_window     = 10,
    )

    # ── Option B: RAG chatbot ─────────────────────────────────────
    # bot = create_rag_chatbot(
    #     conn                    = conn,
    #     llm_deployment_id       = os.getenv("LLM_DEPLOYMENT_ID"),
    #     embedding_deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID"),
    #     vector_table            = "VECTOR_STORE",
    #     rag_top_k               = 5,
    #     rag_min_score           = 0.5,
    # )

    # ── Option C: SQL chatbot ─────────────────────────────────────
    # bot = create_sql_chatbot(
    #     conn              = conn,
    #     llm_deployment_id = os.getenv("LLM_DEPLOYMENT_ID"),
    #     sql_tables        = ["CUST_TICKETS", "SALES_ORDERS"],
    # )

    # ── Option D: Full chatbot (RAG + SQL) ────────────────────────
    # bot = create_full_chatbot(
    #     conn                    = conn,
    #     llm_deployment_id       = os.getenv("LLM_DEPLOYMENT_ID"),
    #     embedding_deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID"),
    #     sql_tables              = ["CUST_TICKETS"],
    #     vector_table            = "VECTOR_STORE",
    # )

    # ── Option E: Custom config ───────────────────────────────────
    # config = ChatbotConfig(
    #     llm_deployment_id       = "your-id",
    #     embedding_deployment_id = "your-embedding-id",
    #     llm_model               = "gpt-4o",
    #     temperature             = 0.2,
    #     memory_window           = 5,
    #     enable_rag              = True,
    #     vector_table            = "MY_DOCS",
    #     rag_top_k               = 3,
    #     rag_min_score           = 0.6,
    #     enable_sql              = True,
    #     sql_tables              = ["ORDERS"],
    #     system_prompt           = "You are an order management assistant.",
    #     bot_name                = "OrderBot",
    # )
    # bot = SAPChatbot(config, conn=conn)

    # ── Step 3: Interactive chat loop ────────────────────────────
    print(f"\nChatbot: {bot.config.bot_name} is ready.")
    print("Type your message. Commands: /reset | /history | /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue
        if user_input.lower() == "/quit":
            break
        elif user_input.lower() == "/reset":
            bot.reset()
            print("Bot: Conversation cleared. Starting fresh!\n")
            continue
        elif user_input.lower() == "/history":
            bot.print_history()
            continue

        response = bot.chat(user_input)

        print(f"\nBot [{response['mode']}]: {response['answer']}")

        if response["sources"]:
            print("Sources:", [s["source_name"] for s in response["sources"]])
        if response["sql_used"]:
            print(f"SQL: {response['sql_used']}")
        print()

    # ── Clean up ──────────────────────────────────────────────────
    conn.close()
    print("\nGoodbye!")
    print("=" * 60 + "\n")
