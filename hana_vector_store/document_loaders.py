"""
============================================================
MINI TEMPLATE — Document Loaders (Multi-Type)
============================================================
Use this when: you need to load documents from different
sources before chunking and embedding them.

Supported input types (auto-detected):
  - Plain text string
  - .txt  file
  - .pdf  file
  - .csv  file  (each row → one Document)
  - .xlsx / .xls file (each row → one Document)
  - URL / web page

Setup:
  pip install langchain langchain-community pandas openpyxl pypdf beautifulsoup4 requests
============================================================
"""

import pandas as pd
from pathlib import Path
from langchain.schema import Document


# ─────────────────────────────────────────────
# Individual loaders — use directly if you know your input type
# ─────────────────────────────────────────────

def load_from_text(text: str, source_name: str = "inline_text") -> list[Document]:
    """Load a plain Python string as a single Document."""
    return [Document(
        page_content=text,
        metadata={"source_type": "text", "source_name": source_name}
    )]


def load_from_txt_file(file_path: str) -> list[Document]:
    """Load a .txt file as a single Document."""
    path    = Path(file_path)
    content = path.read_text(encoding="utf-8")
    print(f"Loaded .txt: {path.name} ({len(content)} chars)")
    return [Document(
        page_content=content,
        metadata={"source_type": "txt", "source_name": path.name}
    )]


def load_from_pdf(file_path: str) -> list[Document]:
    """Load a PDF — each page becomes a separate Document."""
    try:
        from langchain_community.document_loaders import PyPDFLoader
    except ImportError:
        raise ImportError("Run: pip install pypdf langchain-community")

    loader = PyPDFLoader(file_path)
    docs   = loader.load()
    for i, doc in enumerate(docs):
        doc.metadata.update({
            "source_type": "pdf",
            "source_name": Path(file_path).name,
            "page": i + 1
        })
    print(f"Loaded PDF: {Path(file_path).name} ({len(docs)} pages)")
    return docs


def load_from_csv(
    file_path: str,
    content_columns: list = None,
    metadata_columns: list = None
) -> list[Document]:
    """
    Load a CSV — each row becomes a Document.

    Args:
        content_columns  : columns to include in text content (default: all)
        metadata_columns : columns to store as metadata (default: none)
    """
    df = pd.read_csv(file_path)
    cols = content_columns if content_columns else df.columns.tolist()

    docs = []
    for idx, row in df.iterrows():
        content = " | ".join([f"{c}: {row[c]}" for c in cols if c in row])
        meta    = {"source_type": "csv", "source_name": Path(file_path).name, "row_index": idx}
        if metadata_columns:
            meta.update({c: str(row[c]) for c in metadata_columns if c in row})
        docs.append(Document(page_content=content, metadata=meta))

    print(f"Loaded CSV: {Path(file_path).name} ({len(docs)} rows)")
    return docs


def load_from_excel(
    file_path: str,
    sheet_name=0,
    content_columns: list = None
) -> list[Document]:
    """
    Load an Excel file — each row becomes a Document.

    Args:
        sheet_name      : sheet name or index (default: first sheet)
        content_columns : columns to include in text content (default: all)
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    if content_columns:
        df = df[content_columns]

    docs = []
    for idx, row in df.iterrows():
        content = " | ".join([f"{c}: {v}" for c, v in row.items() if pd.notna(v)])
        meta    = {"source_type": "excel", "source_name": Path(file_path).name, "row_index": idx}
        docs.append(Document(page_content=content, metadata=meta))

    print(f"Loaded Excel: {Path(file_path).name} ({len(docs)} rows)")
    return docs


def load_from_url(url: str) -> list[Document]:
    """Load text content from a web page URL (strips HTML)."""
    try:
        from langchain_community.document_loaders import WebBaseLoader
    except ImportError:
        raise ImportError("Run: pip install beautifulsoup4 requests langchain-community")

    loader = WebBaseLoader(url)
    docs   = loader.load()
    for doc in docs:
        doc.metadata.update({"source_type": "url", "source_name": url})
    print(f"Loaded URL: {url} ({len(docs)} document(s))")
    return docs


# ─────────────────────────────────────────────
# Universal loader — auto-detects input type
# ─────────────────────────────────────────────

def load_documents(input_source: str, **kwargs) -> list[Document]:
    """
    Auto-detect input type and load documents.

    Args:
        input_source : one of:
            "https://..."        → URL
            "file.pdf"           → PDF
            "file.csv"           → CSV
            "file.xlsx"          → Excel
            "file.txt"           → Text file
            "any other string"   → raw text content
        **kwargs : passed to the specific loader (e.g. content_columns for CSV)

    Returns:
        list of LangChain Document objects
    """
    src = input_source.strip()

    if src.startswith("http://") or src.startswith("https://"):
        return load_from_url(src)
    elif src.lower().endswith(".pdf"):
        return load_from_pdf(src)
    elif src.lower().endswith(".csv"):
        return load_from_csv(src, **kwargs)
    elif src.lower().endswith((".xlsx", ".xls")):
        return load_from_excel(src, **kwargs)
    elif src.lower().endswith(".txt"):
        return load_from_txt_file(src)
    else:
        return load_from_text(src)


if __name__ == "__main__":
    # ── Test the auto-loader with a raw text string ───────
    docs = load_documents("SAP HANA Cloud supports vector embeddings natively.")
    print(f"\nLoaded {len(docs)} document(s)")
    print("Content :", docs[0].page_content)
    print("Metadata:", docs[0].metadata)

    # Other examples (uncomment to try):
    # docs = load_documents("./data/report.pdf")
    # docs = load_documents("./data/products.csv", content_columns=["name", "description"])
    # docs = load_documents("https://help.sap.com/docs/hana-cloud")
