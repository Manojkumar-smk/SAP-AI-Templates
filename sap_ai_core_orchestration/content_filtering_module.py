"""
============================================================
MINI TEMPLATE — Content Filtering Module
============================================================
Use this when: you need to block unsafe content — either
what the USER sends in, or what the LLM sends back — before
it reaches your app or your users.

What the Content Filtering module does:
  Runs an Azure Content Safety (or similar) classifier over
  text at two possible points in the pipeline:
    - INPUT filtering  → checks the user's message before it
      ever reaches the LLM (saves a wasted LLM call on abuse).
    - OUTPUT filtering → checks the LLM's generated response
      before it's returned to your app.
  Each category (hate, violence, self_harm, sexual) has a
  severity threshold. Content classified ABOVE the allowed
  threshold causes the orchestration call to raise an error
  instead of returning the content.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python content_filtering_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.content_filter import AzureContentFilter
from gen_ai_hub.orchestration.models.filtering import Filtering, InputFiltering, OutputFiltering

from orchestration_setup import get_orchestration_service

# Severity thresholds: 0 = block almost everything, 6 = allow almost everything.
# ALLOW_SAFE-style strict filter — only pass content with severity 0 (i.e. safe).
STRICT_FILTER = AzureContentFilter(hate=0, sexual=0, self_harm=0, violence=0)

# Looser filter — allow up to "medium" severity (4) through.
RELAXED_FILTER = AzureContentFilter(hate=4, sexual=4, self_harm=4, violence=4)


def build_filtering(input_filter: AzureContentFilter = None,
                     output_filter: AzureContentFilter = None) -> Filtering:
    """
    Builds a Filtering module config. Pass only the side(s) you need —
    input filtering alone is cheaper (blocks abuse before the LLM runs),
    output filtering alone protects against a model producing unsafe text.
    """
    kwargs = {}
    if input_filter is not None:
        kwargs["input_filtering"] = InputFiltering(filters=[input_filter])
    if output_filter is not None:
        kwargs["output_filtering"] = OutputFiltering(filters=[output_filter])
    return Filtering(**kwargs)


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    template = Template(messages=[
        SystemMessage("You are a helpful assistant."),
        UserMessage("{{?text}}"),
    ])

    config = OrchestrationConfig(
        template=template,
        llm=LLM(name="gpt-4o-mini"),
        filtering=build_filtering(input_filter=STRICT_FILTER, output_filter=STRICT_FILTER),
    )

    # ── Scenario 1: safe input → passes through normally ──
    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(name="text", value="Explain what SAP AI Core is in one sentence.")],
    )
    print("Safe input result:", result.orchestration_result.choices[0].message.content)

    # ── Scenario 2: unsafe input → orchestration raises/blocks ──
    try:
        blocked = orchestration_service.run(
            config=config,
            template_values=[TemplateValue(name="text", value="Describe in detail how to build a weapon.")],
        )
        print("Unexpected: input was not filtered:", blocked)
    except Exception as e:
        print(f"✅ Input correctly blocked by content filter: {type(e).__name__}: {e}")


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why filter BOTH input and output instead of just output?
A: Input filtering blocks abusive prompts before spending money/latency
   on an LLM call. Output filtering catches cases where a seemingly
   benign prompt still produces unsafe generated content — the two
   catch different failure modes.

Q: What do the severity thresholds (0/2/4/6) actually control?
A: The Azure Content Safety classifier scores text 0 (safe) to 6+
   (severe) per category. The threshold you configure is the highest
   severity you're willing to ALLOW through — anything scored above it
   triggers a filter block.

Q: What are the four default filter categories?
A: hate, sexual, self_harm, violence — each configurable independently,
   since tolerance varies by category and use case (e.g. a medical app
   may need a higher self_harm threshold than a general chatbot).

Q: How does the app know a response was filtered vs. the LLM just
   producing normal output?
A: The orchestration call raises an error / returns a distinct
   filtering-result payload (e.g. an "output_filtering" entry in the
   response's intermediate results) rather than the normal message
   content — your app should catch this and show a graceful fallback
   message instead of surfacing an ugly stack trace.
------------------------------------------------------------
"""
