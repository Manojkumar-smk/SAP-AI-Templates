"""
============================================================
MINI TEMPLATE — Structured Output Module
============================================================
Use this when: the LLM's answer needs to be consumed by CODE,
not read by a human — e.g. writing a result back into an SAP
table, calling another API with extracted fields, or driving
an if/else branch in your app.

What structured output does:
  Constrains the LLM's response to conform to a JSON Schema you
  define. Instead of parsing free text with regex (fragile),
  you get back a JSON string guaranteed to match your schema's
  fields and types — safe to `json.loads()` and use directly.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python structured_output_module.py
============================================================
"""

import json
from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.response_format import ResponseFormatJsonSchema

from orchestration_setup import get_orchestration_service


# Example schema: extract structured fields from a free-text support ticket
TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "category":    {"type": "string", "enum": ["BUG", "FEATURE_REQUEST", "QUESTION", "COMPLAINT"]},
        "urgency":     {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "summary":     {"type": "string", "description": "one-sentence summary of the issue"},
        "customer_sentiment": {"type": "string", "enum": ["POSITIVE", "NEUTRAL", "NEGATIVE"]},
    },
    "required": ["category", "urgency", "summary", "customer_sentiment"],
    "additionalProperties": False,
}


def build_structured_template(schema: dict, schema_name: str = "extraction_result") -> Template:
    """
    Builds a Template whose response_format enforces the given JSON Schema.

    Args:
        schema      : JSON Schema dict describing the required output shape
        schema_name : label for the schema (shows up in API traces/logs)
    """
    return Template(
        messages=[
            SystemMessage(
                "Extract structured information from the user's support ticket text. "
                "Respond ONLY with JSON matching the given schema."
            ),
            UserMessage("{{?ticket_text}}"),
        ],
        response_format=ResponseFormatJsonSchema(
            name=schema_name,
            description="Structured extraction of a support ticket",
            schema=schema,
            strict=True,
        ),
    )


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    template = build_structured_template(TICKET_SCHEMA)
    config = OrchestrationConfig(template=template, llm=LLM(name="gpt-4o-mini", parameters={"temperature": 0}))

    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(
            name="ticket_text",
            value=(
                "This is the third time the export button has crashed the app this week. "
                "I'm losing an hour of work every time. Please fix this ASAP."
            ),
        )],
    )

    raw_json = result.orchestration_result.choices[0].message.content
    parsed = json.loads(raw_json)
    print("✅ Structured output (parsed dict):")
    for key, value in parsed.items():
        print(f"  {key:<20} = {value}")


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why is schema-constrained JSON output more reliable than asking
   the model to "please respond in JSON" via prompt instructions alone?
A: Prompt instructions are a suggestion the model can drift from
   (extra prose, markdown fences, missing fields). A response_format
   with `strict: true` constrains the token generation itself so the
   output is guaranteed to validate against the schema — no manual
   regex/string cleanup needed downstream.

Q: What's a realistic enterprise use case for structured output on
   SAP AI Core?
A: Classifying/triaging inbound tickets or emails and writing the
   result directly into a table (category, urgency, sentiment) for a
   downstream workflow — no human parsing needed, and it's safe to
   `json.loads()` straight into your business logic.

Q: What happens if the input doesn't clearly map to the schema
   (e.g. an ambiguous enum choice)?
A: The model still must pick a valid enum value that satisfies the
   schema — it cannot emit a stray/unexpected value under `strict`
   mode — but that means correctness of the field's MEANING still
   depends on prompt quality even though its structure is guaranteed.

Q: additionalProperties: false — why include it?
A: Prevents the model from tacking on extra, unexpected keys — keeps
   the contract with downstream code exact.
------------------------------------------------------------
"""
