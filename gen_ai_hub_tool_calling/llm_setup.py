"""
============================================================
MINI TEMPLATE — LLM Setup for Tool Calling (Gen AI Hub proxy)
============================================================
Use this when: you need an LLM handle connected to SAP AI Core
via the Gen AI Hub proxy, in either of the two shapes tool
calling can use — a LangChain ChatOpenAI object, or the raw
OpenAI-compatible native client.

Why import gen_ai_hub.proxy.langchain.openai EAGERLY LOADS
Amazon/Google submodules:
  The proxy.langchain package's __init__.py imports its Amazon
  (Bedrock) and Google (GenAI) integrations up front, even if you
  only want the OpenAI-backed ChatOpenAI class. That means
  `pip install sap-ai-sdk-gen` alone is NOT enough for this file
  to import cleanly — you need the `[all]` extra (or at least
  boto3 + langchain-aws + google-genai + langchain-google-genai
  installed) or you'll hit a ModuleNotFoundError on an unrelated
  provider. This is a real, verified gotcha — not theoretical.

Setup:
  1. Add LLM_DEPLOYMENT_ID to your .env file
     (get it from SAP AI Core → Deployments in AI Launchpad)
  2. pip install "sap-ai-sdk-gen[all]" python-dotenv
  3. python llm_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.langchain.openai import ChatOpenAI

load_dotenv()


def get_langchain_llm(model: str = "gpt-4o-mini", temperature: float = 0):
    """
    Returns a LangChain-compatible ChatOpenAI LLM via SAP Gen AI Hub.
    This is what tool_calling_langchain.py and tool_calling_agent.py
    call .bind_tools() on.
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
    print(f"✅ LangChain LLM ready: {model} via SAP Gen AI Hub")
    return llm


def get_native_chat_client():
    """
    Returns the native, OpenAI-SDK-compatible `chat` module via SAP Gen
    AI Hub. This is what tool_calling_native.py calls
    .completions.create(tools=[...]) on — same method signature as
    the real openai package, because it IS an openai.OpenAI() client
    under the hood, just routed through the Gen AI Hub proxy.
    """
    deployment_id = os.getenv("LLM_DEPLOYMENT_ID")
    if not deployment_id:
        raise EnvironmentError(
            "LLM_DEPLOYMENT_ID not set.\n"
            "Add it to your .env file. Get it from SAP AI Launchpad → Deployments."
        )

    from gen_ai_hub.proxy.native.openai import chat
    print("✅ Native OpenAI-compatible client ready via SAP Gen AI Hub")
    return chat


if __name__ == "__main__":
    llm = get_langchain_llm()

    from langchain.schema import HumanMessage
    response = llm.invoke([HumanMessage(content="Say hello in one sentence.")])
    print("LLM Response:", response.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What's the practical difference between the LangChain path and
   the native path for tool calling?
A: LangChain's ChatOpenAI.bind_tools() returns tool calls as
   parsed AIMessage.tool_calls (a clean list of {name, args, id}
   dicts) and plugs into LangChain's broader ecosystem (agents,
   chains, LCEL). The native path returns the raw OpenAI response
   object with choices[0].message.tool_calls, where each call's
   arguments are a JSON STRING you parse yourself — lower-level,
   but zero LangChain dependency if you don't need the rest of it.

Q: Why does get_native_chat_client() import `chat` lazily inside
   the function instead of at module top-level like the LangChain
   import?
A: Importing gen_ai_hub.proxy.native.openai eagerly constructs a
   real OpenAI() client, which validates that AI Core credentials
   are resolvable at IMPORT time — doing that at module load would
   crash any script that imports this file just to use
   get_langchain_llm(), even if it never touches the native path.

Q: Why does deployment_id matter here, and what happens without it?
A: SAP AI Core deployments are per-model, per-resource-group
   endpoints — deployment_id tells the proxy exactly which running
   deployment to route the call to. Omitting it works ONLY if the
   SDK can unambiguously auto-discover a single matching deployment
   for that model name in your resource group; with multiple
   deployments of the same model, you must specify it explicitly.

Q: Does constructing ChatOpenAI(...) itself make a network call, or
   only llm.invoke()?
A: Construction itself calls out — ChatOpenAI's validate_environment
   step calls proxy_client.select_deployment(), which authenticates
   against AI Core and queries running deployments to resolve the
   right one, BEFORE you ever call .invoke(). Verified directly:
   building this object with unreachable/fake credentials fails
   immediately at construction with an auth error, not later at
   invoke time — so a bad .env is caught early, not on first use.
------------------------------------------------------------
"""
