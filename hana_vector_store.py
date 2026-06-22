"""
============================================================
TEMPLATE 03 — SAP HANA Vector Engine: Embed & Store
============================================================
Loads documents from multiple input types, splits them into
chunks, generates embeddings via SAP Gen AI Hub, and stores
them in HANA Cloud's native Vector Engine (REAL_VECTOR).
Also provides cosine-similarity search over stored vectors.

Supported Input Types:
  - Plain text string
  - .txt  file
  - .pdf  file
  - .csv  file
  - URL   (web page)
  - .xlsx / .xls file (each row as a document)

Inputs:
  - conn     : hdbcli Connection        (from template_01 hana_connection.py)
  - conn_ctx : hana_ml ConnectionContext (from template_01 hana_connection.py)

Dependencies:
    pip install hdbcli hana-ml cfenv python-dotenv
                langchain langchain-community langchain-openai
                sap-ai-sdk-gen
                pypdf pandas openpyxl requests beautifulsoup4

Usage:
    python hana_vector_store.py
============================================================
"""

import os
import json
import uuid
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# ── LangChain document loaders ────────────────────────────
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# ── SAP Gen AI Hub ────────────────────────────────────────
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

# ── HANA connection (Template 01) ─────────────────────────
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
# 1. EMBEDDING MODEL SETUP
# ─────────────────────────────────────────────
#
# Model options via SAP Gen AI Hub:
#   "text-embedding-ada-002"    → 1536 dimensions  (most common)
#   "text-embedding-3-small"    → 1536 dimensions  (newer, faster)
#   "text-embedding-3-large"    → 3072 dimensions  (highest quality)
#
# !! IMPORTANT: VECTOR_DIMENSION below must match the model you choose !!

EMBEDDING_MODEL     = "text-embedding-ada-002"
VECTOR_DIMENSION    = 1536    # ← change to 3072 if using text-embedding-3-large


def get_embedding_model():
    """
    Returns a LangChain-compatible embedding model via SAP Gen AI Hub.

    ── To switch to plain OpenAI ────────────────────────────────────────
    from langchain_openai import OpenAIEmbeddings as DirectEmbeddings
    return DirectEmbeddings(model="text-embedding-ada-002",
                            api_key=os.getenv("OPENAI_API_KEY"))
    ─────────────────────────────────────────────────────────────────────
    """
    deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "EMBEDDING_DEPLOYMENT_ID not set.\n"
            "Add it to your .env file. Get it from SAP AI Core → Deployments."
        )

    proxy_client = get_proxy_client("gen-ai-hub")

    embeddings = OpenAIEmbeddings(
        proxy_model_name=EMBEDDING_MODEL,
        proxy_client=proxy_client,
        deployment_id=deployment_id,
    )
    log.info("Embedding model ready: %s (%d dims)", EMBEDDING_MODEL, VECTOR_DIMENSION)
    return embeddings


# ─────────────────────────────────────────────
# 2. MULTI-TYPE DOCUMENT LOADERS
# ─────────────────────────────────────────────

def load_from_text(text: str, source_name: str = "inline_text") -> list[Document]:
    """Load a plain Python string as a single Document."""
    return [Document(page_content=text, metadata={"source_type": "text", "source_name": source_name})]


def load_from_txt_file(file_path: str) -> list[Document]:
    """Load a .txt file."""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    log.info("Loaded .txt file: %s (%d chars)", path.name, len(content))
    return [Document(page_content=content, metadata={"source_type": "txt", "source_name": path.name})]


def load_from_pdf(file_path: str) -> list[Document]:
    """Load a PDF file — each page becomes a Document."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError:
        raise ImportError("Install pypdf: pip install pypdf")

    loader = PyPDFLoader(file_path)
    docs   = loader.load()
    for i, doc in enumerate(docs):
        doc.metadata.update({"source_type": "pdf", "source_name": Path(file_path).name, "page": i + 1})
    log.info("Loaded PDF: %s — %d pages", Path(file_path).name, len(docs))
    return docs


def load_from_csv(file_path: str, content_columns: list = None, metadata_columns: list = None) -> list[Document]:
    """
    Load a CSV file. Each row becomes a Document.

    Args:
        file_path        : path to CSV file
        content_columns  : columns to include in page_content (default: all)
        metadata_columns : columns to keep as metadata (default: none)
    """
    df = pd.read_csv(file_path)

    if content_columns:
        df_content = df[content_columns]
    else:
        df_content = df

    docs = []
    for idx, row in df.iterrows():
        content = " | ".join([f"{col}: {val}" for col, val in row[df_content.columns].items()])
        meta    = {"source_type": "csv", "source_name": Path(file_path).name, "row_index": idx}
        if metadata_columns:
            meta.update({col: str(row[col]) for col in metadata_columns if col in row})
        docs.append(Document(page_content=content, metadata=meta))

    log.info("Loaded CSV: %s — %d rows", Path(file_path).name, len(docs))
    return docs


def load_from_excel(file_path: str, sheet_name=0, content_columns: list = None) -> list[Document]:
    """
    Load an Excel file (.xlsx / .xls). Each row becomes a Document.

    Args:
        file_path       : path to Excel file
        sheet_name      : sheet name or index (default: first sheet)
        content_columns : columns to include in page_content (default: all)
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    if content_columns:
        df = df[content_columns]

    docs = []
    for idx, row in df.iterrows():
        content = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
        meta    = {"source_type": "excel", "source_name": Path(file_path).name, "row_index": idx}
        docs.append(Document(page_content=content, metadata=meta))

    log.info("Loaded Excel: %s — %d rows", Path(file_path).name, len(docs))
    return docs


def load_from_url(url: str) -> list[Document]:
    """
    Load text content from a URL (web page).
    Strips HTML and returns clean text as a single Document.
    """
    try:
        from langchain_community.document_loaders import WebBaseLoader
    except ImportError:
        raise ImportError("Install beautifulsoup4: pip install beautifulsoup4 requests")

    loader = WebBaseLoader(url)
    docs   = loader.load()
    for doc in docs:
        doc.metadata.update({"source_type": "url", "source_name": url})
    log.info("Loaded URL: %s — %d document(s)", url, len(docs))
    return docs


def load_documents(input_source, **kwargs) -> list[Document]:
    """
    Universal loader — detects input type automatically.

    Args:
        input_source : one of:
            - str starting with "http"       → URL
            - str ending with ".pdf"         → PDF file
            - str ending with ".csv"         → CSV file
            - str ending with ".xlsx/.xls"   → Excel file
            - str ending with ".txt"         → Text file
            - any other str                  → raw text content
        **kwargs     : passed through to the specific loader

    Returns:
        list of LangChain Document objects
    """
    if not isinstance(input_source, str):
        raise TypeError(f"input_source must be a string. Got: {type(input_source)}")

    src = input_source.strip()

    if src.startswith("http://") or src.startswith("https://"):
        return load_from_url(src, **kwargs)
    elif src.lower().endswith(".pdf"):
        return load_from_pdf(src, **kwargs)
    elif src.lower().endswith(".csv"):
        return load_from_csv(src, **kwargs)
    elif src.lower().endswith((".xlsx", ".xls")):
        return load_from_excel(src, **kwargs)
    elif src.lower().endswith(".txt"):
        return load_from_txt_file(src, **kwargs)
    else:
        # Treat as raw text
        return load_from_text(src, **kwargs)


# ─────────────────────────────────────────────
# 3. TEXT CHUNKING
# ─────────────────────────────────────────────

def chunk_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> list[Document]:
    """
    Splits documents into smaller chunks for embedding.
    Smaller chunks = more precise retrieval.
    Larger chunks = more context per result.

    Args:
        docs          : list of Documents from any loader
        chunk_size    : max characters per chunk (default: 500)
        chunk_overlap : overlap between consecutive chunks (default: 50)

    Returns:
        list of chunked Documents with chunk_index added to metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(docs)

    # Add chunk index per source
    source_counter = {}
    for chunk in chunks:
        src = chunk.metadata.get("source_name", "unknown")
        source_counter[src] = source_counter.get(src, 0)
        chunk.metadata["chunk_index"] = source_counter[src]
        source_counter[src] += 1

    log.info("Chunked %d document(s) → %d chunks (size=%d, overlap=%d)",
             len(docs), len(chunks), chunk_size, chunk_overlap)
    return chunks


# ─────────────────────────────────────────────
# 4. HANA VECTOR TABLE SETUP
# ─────────────────────────────────────────────

# Default table name — change to match your use case
VECTOR_TABLE = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")


def create_vector_table(conn, table_name: str = VECTOR_TABLE) -> None:
    """
    Creates the HANA Vector Engine table if it doesn't already exist.

    Schema:
        ID           : unique chunk ID (UUID)
        SOURCE_TYPE  : type of input (text / pdf / csv / excel / url / txt)
        SOURCE_NAME  : file name or URL
        CHUNK_INDEX  : position of chunk within its source document
        CONTENT      : raw text of the chunk (used for retrieval)
        METADATA     : full metadata as JSON string
        EMBEDDING    : REAL_VECTOR — the vector embedding of CONTENT
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS "{table_name}" (
        "ID"          NVARCHAR(100)  NOT NULL PRIMARY KEY,
        "SOURCE_TYPE" NVARCHAR(50),
        "SOURCE_NAME" NVARCHAR(500),
        "CHUNK_INDEX" INTEGER,
        "CONTENT"     NCLOB,
        "METADATA"    NCLOB,
        "EMBEDDING"   REAL_VECTOR({VECTOR_DIMENSION})
    )
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        log.info("Vector table ready: %s (dimension=%d)", table_name, VECTOR_DIMENSION)
    except Exception as e:
        log.error("Failed to create vector table: %s", e)
        raise
    finally:
        cursor.close()


def clear_vector_table(conn, table_name: str = VECTOR_TABLE, source_name: str = None) -> int:
    """
    Clears vectors from the table.

    Args:
        conn        : hdbcli Connection
        table_name  : target table
        source_name : if provided, only deletes rows from this source.
                      If None, deletes ALL rows (full reset).

    Returns:
        Number of rows deleted.
    """
    cursor = conn.cursor()
    try:
        if source_name:
            cursor.execute(f'DELETE FROM "{table_name}" WHERE "SOURCE_NAME" = ?', (source_name,))
            log.info("Cleared vectors for source: %s", source_name)
        else:
            cursor.execute(f'DELETE FROM "{table_name}"')
            log.info("Cleared ALL vectors from table: %s", table_name)

        count = cursor.rowcount
        conn.commit()
        return count
    finally:
        cursor.close()


# ─────────────────────────────────────────────
# 5. EMBED AND STORE
# ─────────────────────────────────────────────

def embed_and_store(
    conn,
    chunks: list[Document],
    embedding_model,
    table_name: str = VECTOR_TABLE,
    batch_size: int = 50,
) -> int:
    """
    Generates embeddings for each chunk and inserts them into HANA.

    Args:
        conn            : hdbcli Connection
        chunks          : list of chunked Documents
        embedding_model : LangChain embedding model (from get_embedding_model())
        table_name      : target HANA table
        batch_size      : number of chunks to embed per API call (reduce if hitting rate limits)

    Returns:
        Number of chunks stored.
    """
    if not chunks:
        log.warning("No chunks to embed — skipping.")
        return 0

    cursor = conn.cursor()
    insert_sql = f"""
        INSERT INTO "{table_name}"
            ("ID", "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA", "EMBEDDING")
        VALUES (?, ?, ?, ?, ?, ?, TO_REAL_VECTOR(?))
    """

    total_stored = 0

    # Process in batches to avoid rate-limit / memory issues
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        texts = [c.page_content for c in batch]

        log.info("Embedding batch %d–%d of %d ...",
                 batch_start + 1, batch_start + len(batch), len(chunks))

        # Generate embeddings — returns list of float lists
        vectors = embedding_model.embed_documents(texts)

        rows = []
        for chunk, vector in zip(batch, vectors):
            rows.append((
                str(uuid.uuid4()),                            # ID
                chunk.metadata.get("source_type", "unknown"),# SOURCE_TYPE
                chunk.metadata.get("source_name", "unknown"),# SOURCE_NAME
                chunk.metadata.get("chunk_index", 0),        # CHUNK_INDEX
                chunk.page_content,                          # CONTENT
                json.dumps(chunk.metadata),                  # METADATA
                str(vector),                                 # EMBEDDING as string → TO_REAL_VECTOR
            ))

        cursor.executemany(insert_sql, rows)
        conn.commit()
        total_stored += len(rows)
        log.info("Stored %d chunks (total so far: %d)", len(rows), total_stored)

    cursor.close()
    log.info("Embedding complete. Total stored: %d", total_stored)
    return total_stored


# ─────────────────────────────────────────────
# 6. SIMILARITY SEARCH
# ─────────────────────────────────────────────

def similarity_search(
    conn,
    query: str,
    embedding_model,
    table_name: str = VECTOR_TABLE,
    top_k: int = 5,
    source_filter: str = None,
) -> list[dict]:
    """
    Finds the top-K most relevant chunks for a query using COSINE_SIMILARITY.

    Args:
        conn            : hdbcli Connection
        query           : user's search question / sentence
        embedding_model : same model used during storage
        table_name      : HANA table to search
        top_k           : number of results to return (default: 5)
        source_filter   : optional — limit search to a specific source_name

    Returns:
        List of dicts:
        [
            {
                "rank":        1,
                "score":       0.92,
                "content":     "chunk text ...",
                "source_type": "pdf",
                "source_name": "report.pdf",
                "chunk_index": 3,
                "metadata":    {...}
            },
            ...
        ]
    """
    # Embed the query
    query_vector = embedding_model.embed_query(query)
    query_vector_str = str(query_vector)

    cursor = conn.cursor()

    if source_filter:
        sql = f"""
            SELECT TOP {top_k}
                "ID", "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA",
                COSINE_SIMILARITY("EMBEDDING", TO_REAL_VECTOR(?)) AS SCORE
            FROM "{table_name}"
            WHERE "SOURCE_NAME" = ?
            ORDER BY SCORE DESC
        """
        cursor.execute(sql, (query_vector_str, source_filter))
    else:
        sql = f"""
            SELECT TOP {top_k}
                "ID", "SOURCE_TYPE", "SOURCE_NAME", "CHUNK_INDEX", "CONTENT", "METADATA",
                COSINE_SIMILARITY("EMBEDDING", TO_REAL_VECTOR(?)) AS SCORE
            FROM "{table_name}"
            ORDER BY SCORE DESC
        """
        cursor.execute(sql, (query_vector_str,))

    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()

    results = []
    for rank, row in enumerate(rows, start=1):
        record = dict(zip(columns, row))
        results.append({
            "rank":        rank,
            "score":       round(float(record["SCORE"]), 4),
            "content":     record["CONTENT"],
            "source_type": record["SOURCE_TYPE"],
            "source_name": record["SOURCE_NAME"],
            "chunk_index": record["CHUNK_INDEX"],
            "metadata":    json.loads(record["METADATA"]) if record["METADATA"] else {},
        })

    log.info("Similarity search → %d results for query: '%s'", len(results), query[:60])
    return results


# ─────────────────────────────────────────────
# 7. MAIN VECTOR STORE CLASS
# ─────────────────────────────────────────────

class HANAVectorStore:
    """
    All-in-one class for embedding, storing, and searching vectors in HANA.

    Usage:
        from hana_connection import get_hana_credentials, get_dbapi_connection
        from hana_vector_store import HANAVectorStore

        creds = get_hana_credentials()
        conn  = get_dbapi_connection(creds)

        store = HANAVectorStore(conn, table_name="MY_VECTORS")

        # Store from any source
        store.add("path/to/document.pdf")
        store.add("path/to/data.csv")
        store.add("https://example.com/article")
        store.add("This is some raw text I want to embed.")

        # Search
        results = store.search("What is the refund policy?", top_k=3)
        for r in results:
            print(r["score"], r["content"])
    """

    def __init__(self, conn, table_name: str = VECTOR_TABLE, embedding_model=None):
        self.conn            = conn
        self.table_name      = table_name
        self.embedding_model = embedding_model or get_embedding_model()

        # Ensure the vector table exists
        create_vector_table(conn, table_name)

    def add(
        self,
        input_source,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        clear_existing: bool = False,
        **loader_kwargs
    ) -> int:
        """
        Load → chunk → embed → store pipeline for any input type.

        Args:
            input_source   : file path, URL, or raw text string
            chunk_size     : characters per chunk
            chunk_overlap  : overlap between chunks
            clear_existing : if True, clears existing vectors for this source first

        Returns:
            Number of chunks stored
        """
        # Step 1: Load
        docs = load_documents(input_source, **loader_kwargs)

        # Step 2: Clear existing (optional)
        if clear_existing:
            source_name = docs[0].metadata.get("source_name") if docs else None
            if source_name:
                cleared = clear_vector_table(self.conn, self.table_name, source_name)
                log.info("Cleared %d existing vectors for: %s", cleared, source_name)

        # Step 3: Chunk
        chunks = chunk_documents(docs, chunk_size, chunk_overlap)

        # Step 4: Embed & store
        stored = embed_and_store(self.conn, chunks, self.embedding_model, self.table_name)
        return stored

    def search(self, query: str, top_k: int = 5, source_filter: str = None) -> list[dict]:
        """
        Semantic similarity search against all stored vectors.

        Args:
            query         : natural language question or sentence
            top_k         : number of results
            source_filter : optional — limit to a specific source file/URL

        Returns:
            List of result dicts with score, content, source info
        """
        return similarity_search(
            self.conn, query, self.embedding_model,
            self.table_name, top_k, source_filter
        )

    def get_stats(self) -> dict:
        """Returns basic stats about the vector table."""
        cursor = self.conn.cursor()
        cursor.execute(f'SELECT COUNT(*), COUNT(DISTINCT "SOURCE_NAME") FROM "{self.table_name}"')
        row = cursor.fetchone()
        cursor.close()
        return {
            "table":        self.table_name,
            "total_chunks": row[0],
            "total_sources": row[1],
        }


# ─────────────────────────────────────────────
# 8. MAIN — run standalone
# ─────────────────────────────────────────────

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SAP HANA Vector Store — Multi-Type Embedding Demo")
    print("=" * 60)

    # ── Step 1: Connect ──────────────────────────────────────────
    creds = get_hana_credentials()
    conn  = get_dbapi_connection(creds)

    # ── Step 2: Init store ───────────────────────────────────────
    store = HANAVectorStore(conn, table_name="VECTOR_STORE")

    # ── Step 3: Add documents from different sources ─────────────

    # Option A: raw text
    store.add("SAP HANA Cloud is a cloud-native database platform from SAP.")

    # Option B: .txt file
    # store.add("./data/employee.txt")

    # Option C: PDF
    # store.add("./data/report.pdf")

    # Option D: CSV  (embed all columns)
    # store.add("./data/products.csv")

    # Option E: CSV  (embed specific columns only)
    # store.add("./data/products.csv", content_columns=["product_name", "description"])

    # Option F: Excel
    # store.add("./data/Sales_Data.xlsx")

    # Option G: URL
    # store.add("https://help.sap.com/docs/hana-cloud")

    # ── Step 4: Stats ────────────────────────────────────────────
    stats = store.get_stats()
    print(f"\nVector Table Stats:")
    print(f"  Table         : {stats['table']}")
    print(f"  Total chunks  : {stats['total_chunks']}")
    print(f"  Total sources : {stats['total_sources']}")

    # ── Step 5: Search ───────────────────────────────────────────
    query = "What is SAP HANA Cloud?"
    print(f"\nSimilarity Search: '{query}'")
    results = store.search(query, top_k=3)

    for r in results:
        print(f"\n  Rank {r['rank']} | Score: {r['score']}")
        print(f"  Source : {r['source_type']} → {r['source_name']}")
        print(f"  Content: {r['content'][:200]}...")

    # ── Step 6: Clean up ─────────────────────────────────────────
    conn.close()
    print("\n" + "=" * 60 + "\n")
