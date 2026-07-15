"""
============================================================
MINI TEMPLATE — Full Orchestration Pipeline (all modules wired)
============================================================
Use this when: you want to see every module from this folder
combined into ONE OrchestrationConfig — this is what "orchestration"
actually means: several independent modules, one declarative config,
one API call.

Pipeline built here:
    Data Masking (pseudonymize PII)
        → Content Filtering (input, strict)
        → Templating (system + user message)
        → Document Grounding (optional — toggle with use_grounding)
        → LLM (gpt-4o-mini)
        → Content Filtering (output, strict)
        → Data Masking (un-pseudonymize in the final response)

This mirrors how sap_chatbot/chatbot_core.py wires together
llm_setup + prompt_builder + rag_retriever + sql_retriever in the
DIY-RAG templates — same idea, but every step here runs inside SAP
AI Core's orchestration deployment instead of in your own Python code.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python orchestration_pipeline.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.document_grounding import DocumentGrounding
from gen_ai_hub.orchestration.models.sap_data_privacy_integration import MaskingMethod, ProfileEntity

from orchestration_setup import get_orchestration_service
from llm_module import build_llm
from content_filtering_module import build_filtering, STRICT_FILTER
from data_masking_module import build_masking
from document_grounding_module import build_grounding


def build_full_config(
    system_prompt: str,
    use_grounding: bool = False,
    use_masking: bool = True,
    use_filtering: bool = True,
    model: str = "gpt-4o-mini",
    temperature: float = 0.0,
) -> OrchestrationConfig:
    """
    Assembles an OrchestrationConfig from the individual module builders
    defined in the other files of this folder. Each module is optional —
    toggle it off to see exactly what it contributes.
    """
    if use_grounding:
        user_message = "Question: {{?text}}\nContext: {{?groundingOutput}}"
        # NOTE: grounding module reads its query FROM the "text" placeholder
        # too — reuse the same placeholder name as the input_params below.
    else:
        user_message = "{{?text}}"

    template = Template(messages=[SystemMessage(system_prompt), UserMessage(user_message)])

    kwargs = {
        "template": template,
        "llm": build_llm(model=model, temperature=temperature),
    }

    if use_masking:
        kwargs["data_masking"] = build_masking(
            method=MaskingMethod.PSEUDONYMIZATION,
            entities=[ProfileEntity.PERSON, ProfileEntity.EMAIL, ProfileEntity.PHONE],
        )

    if use_filtering:
        kwargs["filtering"] = build_filtering(input_filter=STRICT_FILTER, output_filter=STRICT_FILTER)

    if use_grounding:
        kwargs["grounding"] = DocumentGrounding(
            module_config=build_grounding(input_placeholder="text", output_placeholder="groundingOutput")
        )

    return OrchestrationConfig(**kwargs)


def run_pipeline(orchestration_service, config: OrchestrationConfig, user_text: str) -> dict:
    """
    Runs the pipeline and returns a normalized result dict instead of
    the raw SDK response object — makes the caller's code simpler and
    easier to unit test.
    """
    try:
        result = orchestration_service.run(
            config=config,
            template_values=[TemplateValue(name="text", value=user_text)],
        )
        return {
            "ok": True,
            "answer": result.orchestration_result.choices[0].message.content,
            "raw": result,
        }
    except Exception as e:
        # Content filter blocks, masking errors, and model errors all
        # surface here — handle gracefully instead of crashing the app.
        return {"ok": False, "answer": None, "error": str(e)}


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    # ── Full pipeline: masking + filtering + LLM (no grounding) ──
    config = build_full_config(
        system_prompt="You are a helpful, professional support assistant.",
        use_grounding=False,
        use_masking=True,
        use_filtering=True,
    )

    outcome = run_pipeline(
        orchestration_service,
        config,
        "My name is Rahul Verma (rahul.verma@example.com). "
        "My invoice #INV-2024-8891 hasn't arrived, can you help?",
    )

    if outcome["ok"]:
        print("✅ Pipeline result:")
        print(outcome["answer"])
    else:
        print("❌ Pipeline blocked/failed:", outcome["error"])


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What is the execution ORDER of modules inside one orchestration
   call, and why does that order matter?
A: Masking → input filtering → templating (placeholder substitution)
   → grounding → LLM → output filtering → un-masking. Order matters
   because e.g. masking must run before the LLM sees the text (so PII
   never reaches the model), and un-masking must run after the LLM
   responds (so your app gets the real values back).

Q: Why build the config with small, composable builder functions
   (build_llm, build_masking, build_filtering, build_grounding)
   instead of one giant inline OrchestrationConfig?
A: Same reason you'd modularize any codebase — each module can be
   unit-tested, toggled, and reused independently (see how
   orchestration_agent.py reuses these same builders with different
   flags per chatbot mode).

Q: What should a production app do when run_pipeline() returns
   ok=False?
A: Log the error (without logging raw PII), show the user a graceful
   fallback message, and NOT retry blindly — a content-filter block is
   a policy decision, not a transient failure, so blind retries won't
   help.

Q: How would you extend this pipeline with a second LLM call (e.g.
   a cheaper model to triage before an expensive model answers)?
A: Chain two OrchestrationConfig calls — run a lightweight config to
   classify/triage in call 1, then branch to a second, differently
   configured call 2 based on that result. Orchestration composes at
   the pipeline level, not by nesting multiple LLM modules in one config.
------------------------------------------------------------
"""
