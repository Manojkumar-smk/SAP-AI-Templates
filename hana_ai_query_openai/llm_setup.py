"""
============================================================
MINI TEMPLATE — LLM Setup via OpenAI API (Direct)
============================================================
Use this when: you want to use OpenAI API directly instead
of SAP Gen AI Hub (e.g. learning with a personal API key).

Difference from hana_ai_query/llm_setup.py:
  SAP version  → uses gen_ai_hub proxy + deployment_id
  This version → uses OPENAI_API_KEY directly (no proxy)

Available models:
  "gpt-4o-mini"  → fast, cost-efficient (default)
  "gpt-4o"       → higher quality
  "gpt-4-turbo"  → maximum quality

Setup:
  1. Add OPENAI_API_KEY to your .env
     (platform.openai.com → API Keys → Create new key)
  2. pip install langchain-openai python-dotenv
  3. python llm_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0):
    """
    Returns a LangChain ChatOpenAI connected directly to OpenAI API.

    Args:
        model       : OpenAI model name (default: "gpt-4o-mini")
        temperature : 0 = deterministic, 1 = creative (default: 0)
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
    print(f"✅ LLM ready: {model} (OpenAI direct)")
    return llm


if __name__ == "__main__":
    llm = get_llm()

    from langchain.schema import HumanMessage
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print("LLM Response:", response.content)
