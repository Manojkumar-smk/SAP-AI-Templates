"""
============================================================
MINI TEMPLATE — Chatbot Preset Factory Functions
============================================================
Use this when: you want a ready-made chatbot for a common
use case without manually building a ChatbotConfig.

Four presets:
  create_general_chatbot() → LLM + memory, no DB
  create_rag_chatbot()     → answers from documents in HANA
  create_sql_chatbot()     → answers from HANA table data
  create_full_chatbot()    → RAG + SQL + memory combined

Each returns a ready SAPChatbot instance.

Setup:
  pip install -r requirements.txt
============================================================
"""

from chatbot_config import ChatbotConfig
from chatbot_core import SAPChatbot


def create_general_chatbot(
    llm_deployment_id: str = None,
    system_prompt:     str   = "You are a helpful SAP AI assistant.",
    llm_model:         str   = "gpt-4o-mini",
    temperature:       float = 0.1,
    memory_window:     int   = 10,
    bot_name:          str   = "SAP General Assistant",
) -> SAPChatbot:
    """
    General-purpose chatbot — LLM + memory, no database required.
    Good for: FAQ bots, support assistants, general Q&A.

    Args:
        llm_deployment_id : SAP AI Core deployment ID (reads from .env if None)
        system_prompt     : chatbot personality and rules
        llm_model         : model name (default: gpt-4o-mini)
        temperature       : 0.0 = factual, 1.0 = creative (default: 0.1)
        memory_window     : conversation turns to remember (default: 10)
        bot_name          : display name for logs
    """
    config = ChatbotConfig(
        llm_deployment_id = llm_deployment_id,
        llm_model         = llm_model,
        temperature       = temperature,
        memory_window     = memory_window,
        system_prompt     = system_prompt,
        bot_name          = bot_name,
        enable_rag        = False,
        enable_sql        = False,
    )
    return SAPChatbot(config)


def create_rag_chatbot(
    conn,
    llm_deployment_id:       str   = None,
    embedding_deployment_id: str   = None,
    vector_table:            str   = "VECTOR_STORE",
    system_prompt:           str   = "You are a helpful SAP AI assistant. Answer based only on the provided knowledge base.",
    llm_model:               str   = "gpt-4o-mini",
    rag_top_k:               int   = 5,
    rag_min_score:           float = 0.5,
    rag_source_filter:       str   = None,
    memory_window:           int   = 10,
    bot_name:                str   = "SAP RAG Assistant",
) -> SAPChatbot:
    """
    RAG chatbot — answers from documents stored in HANA Vector Store.
    Requires: HANA connection + documents already embedded (via hana_vector_store/).

    Args:
        conn                    : hdbcli Connection
        llm_deployment_id       : SAP AI Core chat model deployment ID
        embedding_deployment_id : SAP AI Core embedding model deployment ID
        vector_table            : HANA table with stored vectors
        rag_top_k               : chunks to retrieve per query
        rag_min_score           : minimum similarity score (0.0–1.0)
        rag_source_filter       : optional — limit search to one source file/URL
    """
    config = ChatbotConfig(
        llm_deployment_id       = llm_deployment_id,
        embedding_deployment_id = embedding_deployment_id,
        llm_model               = llm_model,
        system_prompt           = system_prompt,
        bot_name                = bot_name,
        memory_window           = memory_window,
        enable_rag              = True,
        vector_table            = vector_table,
        rag_top_k               = rag_top_k,
        rag_min_score           = rag_min_score,
        rag_source_filter       = rag_source_filter,
        enable_sql              = False,
    )
    return SAPChatbot(config, conn=conn)


def create_sql_chatbot(
    conn,
    sql_tables:        list,
    llm_deployment_id: str   = None,
    system_prompt:     str   = "You are a data analyst assistant. Answer based on database query results.",
    llm_model:         str   = "gpt-4o-mini",
    sql_schema:        str   = None,
    memory_window:     int   = 10,
    bot_name:          str   = "SAP SQL Assistant",
) -> SAPChatbot:
    """
    SQL chatbot — answers from live HANA table data via AI-generated SQL.
    Requires: HANA connection + tables listed in sql_tables.

    Args:
        conn              : hdbcli Connection
        sql_tables        : list of table names the chatbot can query
                            e.g. ["SALES_ORDERS", "CUSTOMERS"]
        llm_deployment_id : SAP AI Core chat model deployment ID
        sql_schema        : HANA schema name (optional)
    """
    config = ChatbotConfig(
        llm_deployment_id = llm_deployment_id,
        llm_model         = llm_model,
        system_prompt     = system_prompt,
        bot_name          = bot_name,
        memory_window     = memory_window,
        enable_sql        = True,
        sql_tables        = sql_tables,
        sql_schema        = sql_schema,
        enable_rag        = False,
    )
    return SAPChatbot(config, conn=conn)


def create_full_chatbot(
    conn,
    sql_tables:              list,
    llm_deployment_id:       str   = None,
    embedding_deployment_id: str   = None,
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
    bot_name:                str   = "SAP Full Assistant",
) -> SAPChatbot:
    """
    Full chatbot — RAG + SQL + memory combined.
    The most powerful mode: answers from both documents and live structured data.

    Args:
        conn                    : hdbcli Connection
        sql_tables              : list of HANA table names
        llm_deployment_id       : SAP AI Core chat model deployment ID
        embedding_deployment_id : SAP AI Core embedding model deployment ID
        vector_table            : HANA vector table name
        rag_top_k               : chunks to retrieve per query
        rag_min_score           : minimum similarity score
        sql_schema              : HANA schema name (optional)
    """
    config = ChatbotConfig(
        llm_deployment_id       = llm_deployment_id,
        embedding_deployment_id = embedding_deployment_id,
        llm_model               = llm_model,
        system_prompt           = system_prompt,
        bot_name                = bot_name,
        memory_window           = memory_window,
        enable_rag              = True,
        vector_table            = vector_table,
        rag_top_k               = rag_top_k,
        rag_min_score           = rag_min_score,
        enable_sql              = True,
        sql_tables              = sql_tables,
        sql_schema              = sql_schema,
    )
    return SAPChatbot(config, conn=conn)


if __name__ == "__main__":
    # Preview available presets
    print("Available preset factory functions:")
    print("  create_general_chatbot() → GENERAL mode")
    print("  create_rag_chatbot()     → RAG mode")
    print("  create_sql_chatbot()     → SQL mode")
    print("  create_full_chatbot()    → RAG + SQL mode")
    print("\nSee chatbot_core.py or USER_MANUAL.md for usage examples.")
