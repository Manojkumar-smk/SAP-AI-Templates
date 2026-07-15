"""
============================================================
MINI TEMPLATE — Orchestration Service Setup (SAP AI Core)
============================================================
Use this when: you want to call the SAP AI Core Orchestration
Service instead of a single raw LLM. Every other file in this
folder builds on top of the client created here.

What is "Orchestration" in SAP AI Core?
  A managed workflow engine that sits in front of the LLM.
  One HTTP call to the orchestration deployment can run, in order:

      Data Masking (mask)  →  Content Filtering (input)
          →  Templating  →  Document Grounding  →  LLM
          →  Content Filtering (output)  →  Data Masking (unmask)

  You describe this pipeline declaratively as an OrchestrationConfig
  (Python objects here — same thing as the JSON config you'd build
  in AI Launchpad's "Orchestration" workbench). SAP AI Core executes
  every module server-side. Your app never sees the intermediate
  steps unless it asks for them.

Orchestration vs. a plain LLM proxy (see hana_ai_query/llm_setup.py):
  Plain proxy   → 1 model, 1 API call, YOU write masking/filtering/RAG
                  glue code yourself in Python.
  Orchestration → many models interchangeably, and masking/filtering/
                  grounding/translation run INSIDE the platform —
                  auditable, reusable, swappable without redeploying code.

Setup:
  1. pip install "sap-ai-sdk-gen[all]" python-dotenv
  2. An "orchestration" deployment must exist in SAP AI Core.
     SAP AI Core creates one automatically in the default resource
     group during onboarding — check AI Launchpad → ML Operations →
     Deployments → filter by scenario "orchestration".
  3. Fill in .env (see .env.example) with your AI Core service key
     values, OR use the ORCHESTRATION_DEPLOYMENT_URL directly.
  4. python orchestration_setup.py
============================================================
"""

import os
from dotenv import load_dotenv
from gen_ai_hub.orchestration.service import OrchestrationService

load_dotenv()


def get_orchestration_service(api_url: str = None) -> OrchestrationService:
    """
    Returns an OrchestrationService client pointed at your orchestration
    deployment. This client is reused by every module file — pass it
    into `.run(config=..., template_values=...)` once you've built a config.

    Args:
        api_url : full orchestration deployment URL, e.g.
                   "https://api.ai.<region>.aws.ml.hana.ondemand.com/v2/inference/deployments/<id>"
                   If omitted, reads ORCHESTRATION_DEPLOYMENT_URL from .env.
                   If that's also missing, the SDK auto-discovers the most
                   recently created RUNNING orchestration deployment in your
                   resource group (uses AICORE_* credentials from env/config).

    Credential resolution order used by the SDK under the hood:
        1. AICORE_CLIENT_ID / AICORE_CLIENT_SECRET / AICORE_AUTH_URL /
           AICORE_BASE_URL / AICORE_RESOURCE_GROUP  environment variables
        2. ~/.aicore/config.json  (AICORE_HOME + AICORE_PROFILE)
        3. VCAP_SERVICES  (when running on Cloud Foundry)
    """
    api_url = api_url or os.getenv("ORCHESTRATION_DEPLOYMENT_URL")

    if api_url:
        service = OrchestrationService(api_url=api_url)
    else:
        # No URL given → SDK auto-discovers a running orchestration
        # deployment using your AICORE_* credentials.
        service = OrchestrationService()

    print("✅ Orchestration Service client ready"
          f"{' → ' + api_url if api_url else ' (auto-discovered deployment)'}")
    return service


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What problem does the Orchestration Service solve that the plain
   Gen AI Hub proxy (ChatOpenAI via get_proxy_client) doesn't?
A: The proxy gives you one model behind one API. Orchestration adds a
   configurable PIPELINE around the model — templating, content safety,
   PII masking, RAG grounding, translation, and structured output — all
   executed server-side and defined declaratively, so app code doesn't
   need model-provider-specific glue logic and the pipeline can change
   without a redeploy.

Q: Is the Orchestration Service stateful (does it remember prior turns)?
A: No — every call is stateless. Conversation memory must be resent by
   the client on each call via `messages_history`
   (see conversation_history_module.py).

Q: What's the difference between a "model deployment" and an
   "orchestration deployment" in SAP AI Core?
A: A model deployment exposes ONE foundation model directly. An
   orchestration deployment exposes the orchestration SCENARIO — the
   actual model(s) used are chosen per-request inside your
   OrchestrationConfig's LLM module, not fixed at deployment time.

Q: Why prefer environment-variable credentials over ~/.aicore/config.json
   in a production app?
A: Env vars/secrets work cleanly with containerized deployments (Cloud
   Foundry / Kyma) and CI secrets managers; a local config file is
   convenient for laptop development but isn't portable.
------------------------------------------------------------
"""


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()
    print("Client type:", type(orchestration_service))
