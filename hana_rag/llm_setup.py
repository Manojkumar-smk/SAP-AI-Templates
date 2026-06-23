"""
============================================================
MINI TEMPLATE — LLM Setup for RAG (SAP Gen AI Hub)
============================================================
Use this when: you need a chat LLM to generate answers in
the RAG pipeline. Connects via SAP Gen AI Hub proxy.

Available models:
  "gpt-4o-mini"  → fast, cost-efficient (default)
  "gpt-4o"       → higher quality
  "gpt-4"        → maximum quality

For RAG, keep temperature low (0.0–0.2) so answers are
factual and grounded in the retrieved context.

Setup:
  1. Add LLM_DEPLOYMENT_ID to your .env
     (SAP AI Launchpad → AI Core → Deployments → chat model)
  2. pip install sap-ai-sdk-gen langchain-openai python-dotenv
  3. python llm_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()


def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.1):
    """
    Returns a LangChain ChatOpenAI via SAP Gen AI Hub.

    Args:
        model       : model name (default: "gpt-4o-mini")
        temperature : 0.0 = fully factual, 1.0 = creative (default: 0.1 for RAG)
    """
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID not set.\n"
            "Add it to .env. Get it from SAP AI Launchpad → AI Core → Deployments."
        )

    proxy_client = get_proxy_client("gen-ai-hub")
    llm = ChatOpenAI(
        proxy_model_name=model,
        proxy_client=proxy_client,
        deployment_id=deployment_id,
        temperature=temperature,
    )
    print(f"✅ LLM ready: {model} (temperature={temperature})")
    return llm


if __name__ == "__main__":
    llm = get_llm()

    from langchain.schema import HumanMessage
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print("LLM Response:", response.content)
