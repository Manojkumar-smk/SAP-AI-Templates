"""
============================================================
MINI TEMPLATE — Embedding Model Setup via SAP Gen AI Hub
============================================================
Use this when: you need an embedding model to convert text
into vectors (numbers) that HANA can store and compare.

Supported models via SAP Gen AI Hub:
  "text-embedding-ada-002"  → 1536 dimensions (default, most compatible)
  "text-embedding-3-small"  → 1536 dimensions (newer, faster)
  "text-embedding-3-large"  → 3072 dimensions (highest quality)

!! IMPORTANT: VECTOR_DIMENSION must match the model you use.
   If you change the model, also update VECTOR_DIMENSION in vector_table.py !!

Setup:
  1. Add EMBEDDING_DEPLOYMENT_ID to your .env file
     (SAP AI Launchpad → AI Core → Deployments)
  2. pip install sap-ai-sdk-gen langchain-openai python-dotenv
  3. python embedding_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()

# ── Change model and dimension together ───────────────────
EMBEDDING_MODEL  = "text-embedding-ada-002"
VECTOR_DIMENSION = 1536   # 3072 for text-embedding-3-large
# ─────────────────────────────────────────────────────────


def get_embedding_model():
    """
    Returns a LangChain-compatible OpenAIEmbeddings via SAP Gen AI Hub.

    Use the returned model to:
      - embed_documents(["text1", "text2"]) → list of vectors
      - embed_query("search question")      → single vector
    """
    deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "EMBEDDING_DEPLOYMENT_ID not set.\n"
            "Add it to .env. Get it from SAP AI Launchpad → AI Core → Deployments."
        )

    proxy_client = get_proxy_client("gen-ai-hub")

    model = OpenAIEmbeddings(
        proxy_model_name=EMBEDDING_MODEL,
        proxy_client=proxy_client,
        deployment_id=deployment_id,
    )
    print(f"✅ Embedding model ready: {EMBEDDING_MODEL} ({VECTOR_DIMENSION} dims)")
    return model


if __name__ == "__main__":
    model = get_embedding_model()

    # Quick test
    texts   = ["SAP HANA is a cloud database.", "Vectors enable semantic search."]
    vectors = model.embed_documents(texts)

    print(f"\nEmbedded {len(vectors)} texts")
    print(f"Vector dimension: {len(vectors[0])}")
    print(f"First 5 values:   {vectors[0][:5]}")
