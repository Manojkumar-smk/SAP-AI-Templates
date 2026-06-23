"""
============================================================
MINI TEMPLATE — LLM + Embedding Setup from ChatbotConfig
============================================================
Use this when: you need to build the LLM and/or embedding
model instances driven by a ChatbotConfig object.

Two functions:
  build_llm()            → chat model for answer generation
  build_embedding_model()→ embedding model for RAG (only if enable_rag=True)

Setup:
  pip install sap-ai-sdk-gen langchain-openai python-dotenv
============================================================
"""

from chatbot_config import ChatbotConfig
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client


def build_llm(config: ChatbotConfig):
    """
    Build a LangChain ChatOpenAI via SAP Gen AI Hub using config settings.

    Args:
        config : ChatbotConfig with llm_deployment_id, llm_model, temperature, max_tokens

    Returns:
        LangChain ChatOpenAI instance
    """
    if not config.llm_deployment_id:
        raise EnvironmentError(
            "llm_deployment_id is not set.\n"
            "Add LLM_DEPLOYMENT_ID to .env or set it in ChatbotConfig."
        )

    proxy_client = get_proxy_client("gen-ai-hub")
    llm = ChatOpenAI(
        proxy_model_name=config.llm_model,
        proxy_client=proxy_client,
        deployment_id=config.llm_deployment_id,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )
    print(f"✅ LLM ready: {config.llm_model} (temp={config.temperature})")
    return llm


def build_embedding_model(config: ChatbotConfig):
    """
    Build an OpenAIEmbeddings model via SAP Gen AI Hub for RAG retrieval.
    Only needed when config.enable_rag = True.

    Args:
        config : ChatbotConfig with embedding_deployment_id, embedding_model

    Returns:
        LangChain OpenAIEmbeddings instance
    """
    if not config.embedding_deployment_id:
        raise EnvironmentError(
            "embedding_deployment_id is not set.\n"
            "Add EMBEDDING_DEPLOYMENT_ID to .env or set it in ChatbotConfig."
        )

    from gen_ai_hub.proxy.langchain.openai import OpenAIEmbeddings
    proxy_client = get_proxy_client("gen-ai-hub")
    embedder = OpenAIEmbeddings(
        proxy_model_name=config.embedding_model,
        proxy_client=proxy_client,
        deployment_id=config.embedding_deployment_id,
    )
    print(f"✅ Embedding model ready: {config.embedding_model}")
    return embedder


if __name__ == "__main__":
    config = ChatbotConfig()

    llm = build_llm(config)
    print("LLM:", llm.model_name if hasattr(llm, "model_name") else "ready")

    # Test embedding (only if EMBEDDING_DEPLOYMENT_ID is in .env)
    if config.embedding_deployment_id:
        embedder = build_embedding_model(config)
        vector   = embedder.embed_query("test")
        print(f"Embedding dim: {len(vector)}")
