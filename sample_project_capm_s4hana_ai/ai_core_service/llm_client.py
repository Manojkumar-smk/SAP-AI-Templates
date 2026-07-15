"""
============================================================
LLM Client — thin wrapper around SAP AI Core (Gen AI Hub proxy)
============================================================
Use this when: any router needs an LLM or embedding model.
Same pattern as the hana_ai_query/llm_setup.py mini template —
kept here as a single shared helper so every router in this
service gets its model the same way.
============================================================
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI, OpenAIEmbeddings
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()


@lru_cache()   # build the client once per process, reuse across every request — avoids re-auth per call
def get_llm(model: str = "gpt-4o-mini", temperature: float = 0.1) -> ChatOpenAI:
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError("LLM_DEPLOYMENT_ID not set — check your .env or bound service.")
    proxy_client = get_proxy_client("gen-ai-hub")
    return ChatOpenAI(
        proxy_model_name=model,
        proxy_client=proxy_client,
        deployment_id=deployment_id,
        temperature=temperature,
    )


@lru_cache()
def get_embedding_model() -> OpenAIEmbeddings:
    deployment_id = os.getenv("EMBEDDING_DEPLOYMENT_ID")
    proxy_client = get_proxy_client("gen-ai-hub")
    return OpenAIEmbeddings(
        proxy_model_name="text-embedding-ada-002",
        proxy_client=proxy_client,
        deployment_id=deployment_id,
    )
