"""
============================================================
TEMPLATE 04 — SAP HANA RAG: Retrieval-Augmented Generation
============================================================
Retrieves relevant context chunks from HANA Vector Store
(Template 03), builds a grounded prompt, calls the LLM,
and returns an answer with cited sources.

Flow:
  User Query
      │
      ▼
  Embed Query (SAP Gen AI Hub — text-embedding-ada-002)
      │
      ▼
  HANA Similarity Search  ←── Vector Store (Template 03)
      │
      ▼
  Build Context Prompt
      │
      ▼
  LLM Answer (SAP Gen AI Hub — gpt-4o-mini)
      │
      ▼
  Grounded Answer + Sources

Inputs:
  - conn            : hdbcli Connection        (from Template 01)
  - user_query      : str — the user's question
  - table_name      : HANA vector table to search (from Template 03)

Dependencies:
    pip install hdbcli hana-ml cfenv python-dotenv sap-ai-sdk-gen
                langchain langchain-core langchain-openai

Usage:
    python hana_rag.py
============================================================
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── LangChain ─────────────────────────────────────────────
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage

# ── SAP Gen AI Hub ────────────────────────────────────────
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

# ── Template 01: HANA Connection ──────────────────────────
import sys
sys.path.append(str(Path(__file__).parent.parent / "template_01_hana_connection"))
from hana_connection import get_hana_credentials, get_dbapi_connection

# ── Template 03: Vector Store ─────────────────────────────
sys.path.append(str(Path(__file__).parent.parent / "template_03_hana_vector_store"))
from hana_vector_store import HANAVectorStore, similarity_search, get_embedding_model

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 1. LLM SETUP
# ─────────────────────────────────────────────

def get_llm():
    """
    Returns a LangChain ChatOpenAI via SAP Gen AI Hub.

    Supported models via SAP Gen AI Hub:
      "gpt-4o-mini"   — fast, cost-efficient (default)
      "gpt-4o"        — higher quality
      "gpt-4"         — maximum quality
    Change proxy_model_name below to switch models.
    """
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID not set in .env.\n"
            "Get it from: SAP AI Core → Deployments (chat model)."
        )
    proxy_client = get_proxy_client("gen-ai-hub")
    llm = ChatOpenAI(
        proxy_model_name="gpt-4o-mini",
        proxy_client=proxy_client,
        deployment_id=deployment_id,
        temperature=0.1,    # low = factual, high = creative
    )
    log.info("LLM ready: gpt-4o-mini via SAP Gen AI Hub")
    return llm


# ─────────────────────────────────────────────
# 2. RAG PROMPTS
# ─────────────────────────────────────────────

# ── Standard RAG prompt ───────────────────────────────────
RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful assistant. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is clearly present in the context, answer directly and concisely.
- If the context does not contain enough information, say: "I don't have enough information to answer this."
- Do NOT make up facts. Do NOT use any knowledge outside the provided context.
- Keep your answer clear and to the point.

Context:
{context}

User Question:
{user_query}

Answer:
""")

# ── Conversational RAG prompt (with chat history) ─────────
CONVERSATIONAL_RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful assistant in an ongoing conversation. Answer the user's question
using ONLY the context provided below.

Rules:
- Use the chat history only to understand references like "it", "that", "the above".
- Answer based ONLY on the provided context — do not make up information.
- If the context does not contain the answer, say: "I don't have enough information to answer this."

Chat History:
{chat_history}

Context:
{context}

User Question:
{user_query}

Answer:
""")


# ─────────────────────────────────────────────
# 3. CONTEXT RETRIEVAL
# ─────────────────────────────────────────────

def retrieve_context(
    conn,
    user_query: str,
    embedding_model,
    table_name: str,
    top_k: int = 5,
    source_filter: str = None,
    min_score: float = 0.0,
) -> list[dict]:
    """
    Fetches the most relevant chunks from HANA Vector Store for the query.

    Args:
        conn            : hdbcli Connection
        user_query      : user's natural language question
        embedding_model : same model used when storing vectors
        table_name      : HANA vector table name
        top_k           : number of chunks to retrieve
        source_filter   : optional — limit search to one source file/URL
        min_score       : optional — filter out chunks below this similarity score (0.0–1.0)

    Returns:
        List of context chunk dicts (from similarity_search in Template 03)
    """
    results = similarity_search(
        conn=conn,
        query=user_query,
        embedding_model=embedding_model,
        table_name=table_name,
        top_k=top_k,
        source_filter=source_filter,
    )

    if min_score > 0.0:
        results = [r for r in results if r["score"] >= min_score]
        log.info("After min_score filter (%.2f): %d chunks retained", min_score, len(results))

    return results


def format_context(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a readable context block for the prompt.

    Each chunk is numbered and includes its source for transparency.

    Example output:
        [1] Source: report.pdf (chunk 3)
        SAP HANA Cloud supports vector embeddings via REAL_VECTOR...

        [2] Source: help.sap.com (chunk 0)
        The cosine similarity function compares two vectors...
    """
    if not chunks:
        return "No relevant context found."

    parts = []
    for chunk in chunks:
        header = f"[{chunk['rank']}] Source: {chunk['source_name']} (chunk {chunk['chunk_index']})"
        parts.append(f"{header}\n{chunk['content']}")

    return "\n\n".join(parts)


# ─────────────────────────────────────────────
# 4. RAG PIPELINE
# ─────────────────────────────────────────────

def rag_query(
    conn,
    user_query: str,
    embedding_model,
    llm,
    table_name: str,
    top_k: int = 5,
    source_filter: str = None,
    min_score: float = 0.0,
) -> dict:
    """
    Single-turn RAG pipeline: query → retrieve → generate → return.

    Args:
        conn            : hdbcli Connection
        user_query      : user's question
        embedding_model : embedding model (from Template 03)
        llm             : LangChain LLM
        table_name      : HANA vector table
        top_k           : number of context chunks to use
        source_filter   : optional — limit search to one source
        min_score       : optional — minimum similarity score threshold

    Returns:
        {
            "answer":   "<LLM answer>",
            "context":  "<formatted context string>",
            "sources":  [{"source_name": ..., "score": ..., "chunk_index": ...}, ...],
            "chunks":   [<full chunk dicts>]
        }
    """
    log.info("RAG query: '%s'", user_query[:80])

    # Step 1: Retrieve context chunks from HANA
    chunks = retrieve_context(
        conn, user_query, embedding_model, table_name,
        top_k, source_filter, min_score
    )

    # Step 2: Format context for prompt
    context = format_context(chunks)

    # Step 3: Run LLM chain
    chain  = RAG_PROMPT | llm | StrOutputParser()
    answer = chain.invoke({"context": context, "user_query": user_query})

    # Step 4: Build source citations
    sources = [
        {
            "rank":         c["rank"],
            "source_name":  c["source_name"],
            "source_type":  c["source_type"],
            "chunk_index":  c["chunk_index"],
            "score":        c["score"],
        }
        for c in chunks
    ]

    log.info("RAG answer generated. Sources used: %d", len(sources))

    return {
        "answer":  answer.strip(),
        "context": context,
        "sources": sources,
        "chunks":  chunks,
    }


# ─────────────────────────────────────────────
# 5. MAIN RAG AGENT CLASS
# ─────────────────────────────────────────────

class HANARagAgent:
    """
    Conversational RAG agent backed by HANA Vector Store.

    Supports:
      - Single-turn Q&A
      - Multi-turn conversation with memory
      - Source citations for every answer
      - Optional source/score filtering

    Usage:
        from hana_connection import get_hana_credentials, get_dbapi_connection
        from hana_rag import HANARagAgent

        creds = get_hana_credentials()
        conn  = get_dbapi_connection(creds)

        agent = HANARagAgent(conn, table_name="VECTOR_STORE")

        # Simple Q&A
        result = agent.ask("What is SAP HANA Cloud?")
        print(result["answer"])
        print(result["sources"])

        # Multi-turn conversation
        agent.chat("What is the refund policy?")
        agent.chat("And what about international orders?")   # uses history
    """

    def __init__(
        self,
        conn,
        table_name: str = None,
        llm=None,
        embedding_model=None,
        top_k: int = 5,
        memory_window: int = 5,
        min_score: float = 0.0,
    ):
        """
        Args:
            conn            : hdbcli Connection (from Template 01)
            table_name      : HANA vector table to search (from Template 03)
            llm             : optional custom LLM. Defaults to SAP Gen AI Hub.
            embedding_model : optional custom embedding model. Defaults to SAP Gen AI Hub.
            top_k           : number of context chunks per query (default: 5)
            memory_window   : number of past conversation turns to keep (default: 5)
            min_score       : minimum similarity score to include a chunk (0.0 = no filter)
        """
        self.conn            = conn
        self.table_name      = table_name or os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
        self.llm             = llm or get_llm()
        self.embedding_model = embedding_model or get_embedding_model()
        self.top_k           = top_k
        self.min_score       = min_score

        # Conversation memory — keeps last N turns
        self.memory = ConversationBufferWindowMemory(
            k=memory_window,
            return_messages=True
        )

        log.info("HANARagAgent ready. Table: %s | top_k: %d", self.table_name, self.top_k)

    # ── Single-turn Q&A ───────────────────────────────────
    def ask(
        self,
        user_query: str,
        source_filter: str = None,
        top_k: int = None,
    ) -> dict:
        """
        One-shot RAG query — no conversation history used.

        Args:
            user_query    : user's question
            source_filter : optional — limit to a specific source file/URL
            top_k         : override default top_k for this query

        Returns:
            {
                "answer":   "<answer text>",
                "sources":  [{"rank", "source_name", "score", ...}],
                "context":  "<full context string used>",
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
        Conversational RAG — uses rolling chat history for follow-up questions.
        Automatically stores each turn in memory.

        Args:
            user_query    : user's question
            source_filter : optional — limit to a specific source file/URL
            top_k         : override default top_k for this query

        Returns:
            {
                "answer":       "<answer text>",
                "sources":      [{"rank", "source_name", "score", ...}],
                "chat_history": "<formatted history string>"
            }
        """
        # Step 1: Load chat history from memory
        history_messages = self.memory.load_memory_variables({})["history"]
        chat_history     = self._format_history(history_messages)

        log.info("Chat query: '%s' | History turns: %d",
                 user_query[:60], len(history_messages))

        # Step 2: Retrieve context
        chunks  = retrieve_context(
            self.conn, user_query, self.embedding_model, self.table_name,
            top_k or self.top_k, source_filter, self.min_score
        )
        context = format_context(chunks)

        # Step 3: Run conversational LLM chain
        chain  = CONVERSATIONAL_RAG_PROMPT | self.llm | StrOutputParser()
        answer = chain.invoke({
            "chat_history": chat_history,
            "context":      context,
            "user_query":   user_query,
        })
        answer = answer.strip()

        # Step 4: Save turn to memory
        self.memory.save_context(
            {"input": user_query},
            {"output": answer}
        )

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
        """Resets the conversation history (start a new session)."""
        self.memory.clear()
        log.info("Conversation memory cleared.")

    def get_history(self) -> list:
        """Returns current chat history messages."""
        return self.memory.load_memory_variables({})["history"]

    @staticmethod
    def _format_history(messages: list) -> str:
        """Formats LangChain message objects into a readable string."""
        if not messages:
            return "No previous conversation."
        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"Assistant: {msg.content}")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# 6. MAIN — run standalone
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SAP HANA RAG Agent — Demo")
    print("=" * 60)

    # ── Step 1: Connect ──────────────────────────────────────────
    creds = get_hana_credentials()
    conn  = get_dbapi_connection(creds)

    # ── Step 2: (Optional) Ingest documents if vector store is empty ─
    # Uncomment to add documents before querying:
    #
    # store = HANAVectorStore(conn, table_name="VECTOR_STORE")
    # store.add("./data/your_document.pdf")
    # store.add("https://help.sap.com/docs/hana-cloud")

    # ── Step 3: Init RAG agent ───────────────────────────────────
    agent = HANARagAgent(
        conn=conn,
        table_name="VECTOR_STORE",  # ← must match what Template 03 created
        top_k=5,
        min_score=0.5,              # only use chunks with similarity >= 0.5
        memory_window=5,            # remember last 5 conversation turns
    )

    # ── Example A: Single-turn Q&A ───────────────────────────────
    print("\n── Single-turn Q&A ──")
    result = agent.ask("What is SAP HANA Cloud?")

    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources used ({len(result['sources'])}):")
    for s in result["sources"]:
        print(f"  [{s['rank']}] {s['source_name']} | score: {s['score']}")

    # ── Example B: Multi-turn conversation ───────────────────────
    print("\n── Multi-turn Conversation ──")

    turns = [
        "What are the key features of SAP HANA Vector Engine?",
        "How does cosine similarity work in this context?",   # follow-up using "this context"
        "Give me a summary of what we discussed.",
    ]

    for question in turns:
        print(f"\nUser: {question}")
        response = agent.chat(question)
        print(f"Assistant: {response['answer']}")
        print(f"Sources: {[s['source_name'] for s in response['sources']]}")

    # ── Example C: Filter to a specific document ─────────────────
    print("\n── Source-filtered Q&A ──")
    result = agent.ask(
        "What are the main points?",
        source_filter="your_document.pdf",   # only search in this file
        top_k=3
    )
    print(f"Answer: {result['answer']}")

    # ── Clean up ─────────────────────────────────────────────────
    conn.close()
    print("\n" + "=" * 60 + "\n")
