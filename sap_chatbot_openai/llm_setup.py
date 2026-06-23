"""
============================================================
MINI TEMPLATE — LLM & Embedding Setup for OpenAI (Direct API)
============================================================
Use this when: you need ChatOpenAI and OpenAIEmbeddings for
the chatbot, without SAP Gen AI Hub deployment IDs.

Difference from sap_chatbot/llm_setup.py:
  SAP version  → from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
                  requires llm_deployment_id + embedding_deployment_id
  This version → from langchain_openai import ChatOpenAI, OpenAIEmbeddings
                  only needs OPENAI_API_KEY in .env

Setup:
  pip install langchain-openai python-dotenv
============================================================
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Direct OpenAI imports (no SAP Gen AI Hub) ────────────
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# ─────────────────────────────────────────────────────────

from chatbot_config import ChatbotConfig


def build_llm(config: ChatbotConfig) -> ChatOpenAI:
    """
    Build a ChatOpenAI LLM from a ChatbotConfig.

    Args:
        config: ChatbotConfig with llm_model, temperature, max_tokens

    Returns:
        ChatOpenAI instance ready for use in chains
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not found in environment. "
            "Add it to your .env file: OPENAI_API_KEY=sk-..."
        )

    return ChatOpenAI(
        model=config.llm_model,
        api_key=api_key,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )


def build_embedding_model(config: ChatbotConfig) -> OpenAIEmbeddings:
    """
    Build an OpenAIEmbeddings model from a ChatbotConfig.

    Args:
        config: ChatbotConfig with embedding_model

    Returns:
        OpenAIEmbeddings instance ready for use in vector search
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not found in environment. "
            "Add it to your .env file: OPENAI_API_KEY=sk-..."
        )

    return OpenAIEmbeddings(
        model=config.embedding_model,
        api_key=api_key,
    )


if __name__ == "__main__":
    config = ChatbotConfig(llm_model="gpt-4o-mini", temperature=0.1)
    llm = build_llm(config)
    print(f"✅ LLM ready: {config.llm_model}")

    embedding = build_embedding_model(config)
    print(f"✅ Embedding ready: {config.embedding_model}")

    # Quick test
    from langchain_core.messages import HumanMessage
    resp = llm.invoke([HumanMessage(content="Say hello in one word.")])
    print(f"LLM response: {resp.content}")
