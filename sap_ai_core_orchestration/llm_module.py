"""
============================================================
MINI TEMPLATE — LLM Module
============================================================
Use this when: you need to pick/configure the language model
that the orchestration pipeline will call.

What the LLM module does:
  Wraps a model name + version + generation parameters behind
  a single harmonized interface. Because orchestration
  normalizes the request/response shape across providers, you
  can swap "gpt-4o-mini" for "gemini-1.5-pro" or an
  Anthropic/Claude model on SAP AI Core by changing ONE line —
  no provider-specific SDK code to rewrite.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python llm_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.llm import LLM


def build_llm(
    model: str = "gpt-4o-mini",
    version: str = "latest",
    temperature: float = 0.0,
    max_tokens: int = 500,
    top_p: float = 1.0,
    frequency_penalty: float = 0.0,
    presence_penalty: float = 0.0,
) -> LLM:
    """
    Returns an LLM module config for use inside an OrchestrationConfig.

    Args:
        model             : model name as registered in SAP AI Core's
                             harmonized model catalog, e.g.
                             "gpt-4o-mini", "gpt-4o", "gpt-4",
                             "gemini-1.5-pro", "anthropic--claude-3.5-sonnet"
        version           : model version, "latest" unless pinning is required
        temperature       : 0 = deterministic, higher = more creative
        max_tokens        : hard cap on completion length
        top_p             : nucleus sampling — alternative to temperature
        frequency_penalty : discourages repeating the same tokens
        presence_penalty  : discourages repeating the same topics
    """
    return LLM(
        name=model,
        version=version,
        parameters={
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        },
    )


# Quick-reference: common model choices and when to use them
MODEL_GUIDE = {
    "gpt-4o-mini":                      "default choice — fast, cheap, good enough for most tasks",
    "gpt-4o":                           "higher quality reasoning, multimodal (images)",
    "gpt-4":                            "maximum quality, higher cost/latency",
    "gemini-1.5-pro":                   "very large context window, good for long documents",
    "anthropic--claude-3.5-sonnet":     "strong at structured/careful reasoning and coding",
}


if __name__ == "__main__":
    llm = build_llm(model="gpt-4o-mini", temperature=0.2, max_tokens=300)
    print("✅ LLM module configured:", llm.name, llm.version)
    print("Params:", llm.parameters)

    print("\nModel guide:")
    for name, note in MODEL_GUIDE.items():
        print(f"  {name:<32} → {note}")


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What is the "harmonized API" benefit of the LLM module?
A: All providers (OpenAI, Google, Anthropic, AWS Bedrock models, etc.)
   are exposed through the same request/response schema, so switching
   models is a config change, not a code rewrite.

Q: temperature vs top_p — when would you tune one over the other?
A: Both control randomness; convention is to tune ONE, not both.
   temperature scales the whole probability distribution; top_p
   truncates to the smallest set of tokens covering probability mass p.
   Use temperature=0 for deterministic tasks like SQL/JSON generation.

Q: Why set max_tokens explicitly in production instead of leaving it
   unset?
A: Cost control and latency predictability — an unbounded completion
   can run long and blow up both.

Q: How would you A/B test two different models in orchestration?
A: Orchestration supports a list of fallback configs — SAP AI Core's
   Python SDK, and the JS/Java SDKs, accept multiple OrchestrationConfig
   objects and can fall back automatically if the first model/config
   errors or times out (also usable for progressive model rollout).
------------------------------------------------------------
"""
