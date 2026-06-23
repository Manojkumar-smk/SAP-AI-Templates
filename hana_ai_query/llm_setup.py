"""
============================================================
MINI TEMPLATE — LLM Setup via SAP Gen AI Hub
============================================================
Use this when: you need an LLM instance connected to SAP AI Core
via the Gen AI Hub proxy (LangChain-compatible).

Setup:
  1. Add LLM_DEPLOYMENT_ID to your .env file
     (get it from SAP AI Core → Deployments in AI Launchpad)
  2. pip install sap-ai-sdk-gen python-dotenv
  3. python llm_setup.py

Available models via SAP Gen AI Hub:
  "gpt-4o-mini"  → fast, cost-efficient (default)
  "gpt-4o"       → higher quality
  "gpt-4"        → maximum quality
============================================================
"""

import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0):
    """
    Returns a LangChain-compatible ChatOpenAI LLM via SAP Gen AI Hub.

    Args:
        model       : model name to use (default: "gpt-4o-mini")
        temperature : 0 = deterministic, 1 = creative (default: 0)
    """
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID not set.\n"
            "Add it to your .env file. Get it from SAP AI Launchpad → Deployments."
        )

    proxy_client = get_proxy_client("gen-ai-hub")

    llm = ChatOpenAI(
        proxy_model_name=model,
        proxy_client=proxy_client,
        deployment_id=deployment_id,
        temperature=temperature,
    )
    print(f"✅ LLM ready: {model} via SAP Gen AI Hub")
    return llm


if __name__ == "__main__":
    llm = get_llm()

    # Quick test — send a simple message
    from langchain.schema import HumanMessage
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print("LLM Response:", response.content)
