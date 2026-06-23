"""
============================================================
MINI TEMPLATE — Text Chunker
============================================================
Use this when: you have loaded documents and need to split
them into smaller pieces before generating embeddings.

Why chunk? Embedding models have token limits and smaller
chunks give more precise similarity search results.

Chunking strategy: RecursiveCharacterTextSplitter
  → tries to split on: paragraphs → lines → sentences → words

Setup:
  pip install langchain
============================================================
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """
    Split a list of Documents into smaller chunks.

    Args:
        docs          : list of Documents (from document_loaders.py)
        chunk_size    : max characters per chunk (default: 500)
                        → smaller = more precise search
                        → larger  = more context per result
        chunk_overlap : characters shared between adjacent chunks (default: 50)
                        → helps avoid losing context at chunk boundaries

    Returns:
        list of chunked Documents with chunk_index added to metadata
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(docs)

    # Add a sequential chunk_index per source document
    counter = {}
    for chunk in chunks:
        src = chunk.metadata.get("source_name", "unknown")
        counter[src] = counter.get(src, 0)
        chunk.metadata["chunk_index"] = counter[src]
        counter[src] += 1

    print(f"✅ {len(docs)} document(s) → {len(chunks)} chunks "
          f"(size={chunk_size}, overlap={chunk_overlap})")
    return chunks


if __name__ == "__main__":
    from document_loaders import load_documents

    # ── Load then chunk ───────────────────────────────────
    docs   = load_documents("SAP HANA Cloud is a cloud-native in-memory database. "
                            "It supports SQL, graph, spatial, and vector processing. "
                            "HANA Vector Engine stores high-dimensional embeddings "
                            "and enables cosine similarity search at scale.")

    chunks = chunk_documents(docs, chunk_size=100, chunk_overlap=20)

    print(f"\nTotal chunks: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"\n[Chunk {i}] index={c.metadata['chunk_index']}")
        print(f"  Content : {c.page_content}")
