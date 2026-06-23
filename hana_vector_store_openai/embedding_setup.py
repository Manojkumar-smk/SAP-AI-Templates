"""
============================================================
MINI TEMPLATE — Embedding Model Setup via OpenAI API (Direct)
============================================================
Use this when: you want to generate text embeddings using
OpenAI API directly instead of SAP Gen AI Hub.

Difference from hana_vector_store/embedding_setup.py:
  SAP version  → uses gen_ai_hub proxy + deployment_id
  This version → uses OPENAI_API_KEY directly (no proxy)

Available embedding models:
  "text-embedding-3-small"  → 1536 dims (fast, cheap — good for learning)
  "text-embedding-3-large"  → 3072 dims (highest quality)
  "text-embedding-ada-002"  → 1536 dims (legacy, still works)

!! VECTOR_DIMENSION must match the model:
   text-embedding-3-small / ada-002 → 1536
   text-embedding-3-large           → 3072 !!

Setup:
  1. Add OPENAI_API_KEY to your .env
  2. pip install langchain-openai python-dotenv
  3. python embedding_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# ── Change model and dimension together ───────────────────
EMBEDDING_MODEL  = "text-embedding-3-small"
VECTOR_DIMENSION = 1536   # 3072 for text-embedding-3-large
# ─────────────────────────────────────────────────────────


def get_embedding_model():
    """
    Returns a LangChain OpenAIEmbeddings connected directly to OpenAI API.

    Use to:
      - embed_documents(["text1", "text2"]) → list of vectors
      - embed_query("search question")      → single vector
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set.\n"
            "Add it to .env. Get it from: platform.openai.com → API Keys."
        )

    model = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key,
    )
    print(f"✅ Embedding model ready: {EMBEDDING_MODEL} ({VECTOR_DIMENSION} dims, OpenAI direct)")
    return model


if __name__ == "__main__":
    model = get_embedding_model()

    texts   = ["SAP HANA is a cloud database.", "Vectors enable semantic search."]
    vectors = model.embed_documents(texts)

    print(f"\nEmbedded {len(vectors)} texts")
    print(f"Vector dimension : {len(vectors[0])}")
    print(f"First 5 values   : {vectors[0][:5]}")
