"""
============================================================
MINI TEMPLATE — LLM Setup for RAG via OpenAI API (Direct)
============================================================
Use this when: you want RAG answers using OpenAI API directly
instead of SAP Gen AI Hub.

Difference from hana_rag/llm_setup.py:
  SAP version  → uses gen_ai_hub proxy + deployment_id
  This version → uses OPENAI_API_KEY directly (no proxy)

For RAG, keep temperature low (0.0–0.2) for factual answers.

Setup:
  1. Add OPENAI_API_KEY to your .env
  2. pip install langchain-openai python-dotenv
  3. python llm_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Returns a LangChain ChatOpenAI connected directly to OpenAI API.

    Args:
        model       : OpenAI model name (default: "gpt-4o-mini")
        temperature : 0.0 = fully factual, 1.0 = creative (keep low for RAG)
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set.\n"
            "Add it to .env. Get it from: platform.openai.com → API Keys."
        )

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=temperature,
    )
    print(f"✅ LLM ready: {model} (OpenAI direct, temperature={temperature})")
    return llm


if __name__ == "__main__":
    llm = get_llm()

    from langchain.schema import HumanMessage
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print("LLM Response:", response.content)
