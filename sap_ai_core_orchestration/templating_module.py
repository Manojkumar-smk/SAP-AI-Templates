"""
============================================================
MINI TEMPLATE — Templating Module
============================================================
Use this when: you need reusable prompt templates with
placeholders instead of hardcoding f-strings into your app.

What the Templating module does:
  Defines the SHAPE of the conversation sent to the LLM —
  a list of SystemMessage / UserMessage / AssistantMessage
  objects. Any message can contain "{{?variable_name}}"
  placeholders that get substituted at call-time via
  TemplateValue, so the template itself stays fixed while
  the inputs change per request.

Why not just use an f-string?
  - The template is a first-class object the platform can log,
    version, and reuse (even store centrally in the Prompt
    Registry and reference by name/version).
  - Placeholder substitution happens in the orchestration
    pipeline itself — AFTER data masking and BEFORE the LLM —
    so masked values are what actually get filled in, not raw PII.
  - Keeps prompt engineering separate from application code.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python templating_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage, AssistantMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig

from orchestration_setup import get_orchestration_service


def build_template(system_prompt: str, user_prompt: str = "{{?text}}") -> Template:
    """
    Basic single-turn template with one placeholder.

    Args:
        system_prompt : fixed instruction that sets the LLM's behaviour
        user_prompt   : the user turn — usually just "{{?text}}"
    """
    return Template(
        messages=[
            SystemMessage(system_prompt),
            UserMessage(user_prompt),
        ]
    )


def build_few_shot_template(system_prompt: str, examples: list[tuple[str, str]]) -> Template:
    """
    Template with few-shot examples baked in before the real question.
    Improves output consistency for classification / extraction tasks
    without needing to fine-tune a model.

    Args:
        system_prompt : fixed instruction
        examples      : list of (user_text, assistant_text) example pairs
    """
    messages = [SystemMessage(system_prompt)]
    for user_text, assistant_text in examples:
        messages.append(UserMessage(user_text))
        messages.append(AssistantMessage(assistant_text))
    messages.append(UserMessage("{{?text}}"))   # the real question goes last
    return Template(messages=messages)


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    # ── Scenario 1: simple placeholder template ────────────
    template = build_template(
        system_prompt="You are a concise assistant. Answer in one sentence.",
    )
    config = OrchestrationConfig(template=template, llm=LLM(name="gpt-4o-mini"))
    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(name="text", value="What is SAP AI Core?")],
    )
    print("Simple template:", result.orchestration_result.choices[0].message.content)

    # ── Scenario 2: few-shot template (sentiment tagging) ──
    fewshot = build_few_shot_template(
        system_prompt="Classify the sentiment of the input as POSITIVE, NEGATIVE, or NEUTRAL. Reply with one word.",
        examples=[
            ("The deployment went smoothly and on time.", "POSITIVE"),
            ("The API kept timing out all day.", "NEGATIVE"),
            ("The release is scheduled for next Tuesday.", "NEUTRAL"),
        ],
    )
    config2 = OrchestrationConfig(template=fewshot, llm=LLM(name="gpt-4o-mini"))
    result2 = orchestration_service.run(
        config=config2,
        template_values=[TemplateValue(name="text", value="Support tickets doubled after the last patch.")],
    )
    print("Few-shot template:", result2.orchestration_result.choices[0].message.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What placeholder syntax does the templating module use, and when
   is it substituted?
A: "{{?variable_name}}" — substituted server-side inside the
   orchestration pipeline, after masking, before the LLM call.

Q: Why store templates in the Prompt Registry instead of in app code?
A: Central versioning, review/approval workflow for prompts, and the
   ability to update a prompt for all consuming apps without a
   redeploy — just reference by name + version (template_ref).

Q: How do few-shot examples fit into a Template object?
A: As alternating UserMessage/AssistantMessage pairs placed before the
   final real UserMessage — the model conditions on them as prior
   "turns" in the conversation.

Q: What's the risk of building prompts via raw string concatenation
   instead of the templating module?
A: No central audit trail, higher prompt-injection risk if user input
   is concatenated before masking/filtering can inspect it, and no
   reuse across services.
------------------------------------------------------------
"""
