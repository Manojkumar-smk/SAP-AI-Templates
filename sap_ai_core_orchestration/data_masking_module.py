"""
============================================================
MINI TEMPLATE — Data Masking Module
============================================================
Use this when: user input or grounding data may contain PII
(names, emails, phone numbers, IDs) that should never reach
the LLM provider's servers or your logs in raw form.

What the Data Masking module does:
  Runs SAP Data Privacy Integration (DPI) BEFORE the templating/
  LLM step, replacing sensitive entities with placeholders.
  Two methods:
    - ANONYMIZATION   → entity replaced with a generic label
                         (e.g. "John Smith" → "PERSON_1"). One-way —
                         the original value is never restored.
    - PSEUDONYMIZATION → entity replaced with a consistent fake
                         value for the duration of the call, and the
                         final LLM response is automatically UN-masked
                         back to the real value before it's returned
                         to your app. Two-way, within a single request.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python data_masking_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.data_masking import DataMasking
from gen_ai_hub.orchestration.models.sap_data_privacy_integration import (
    SAPDataPrivacyIntegration,
    MaskingMethod,
    ProfileEntity,
)

from orchestration_setup import get_orchestration_service


def build_masking(method: MaskingMethod = MaskingMethod.PSEUDONYMIZATION,
                   entities: list = None,
                   allowlist: list[str] = None) -> DataMasking:
    """
    Builds a DataMasking module config.

    Args:
        method    : MaskingMethod.ANONYMIZATION (irreversible) or
                    MaskingMethod.PSEUDONYMIZATION (reversible, auto-unmasked
                    in the final response)
        entities  : which PII categories to catch, e.g.
                    [ProfileEntity.PERSON, ProfileEntity.EMAIL, ProfileEntity.PHONE]
        allowlist : terms that should NEVER be masked even if they match an
                    entity pattern (e.g. your own product/company name)
    """
    entities = entities or [
        ProfileEntity.PERSON,
        ProfileEntity.EMAIL,
        ProfileEntity.PHONE,
        ProfileEntity.ORG,
    ]
    return DataMasking(
        providers=[
            SAPDataPrivacyIntegration(
                method=method,
                entities=entities,
                allowlist=allowlist or [],
            )
        ]
    )


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    template = Template(messages=[
        SystemMessage("Rewrite the message as a polite, professional email."),
        UserMessage("{{?text}}"),
    ])

    # Pseudonymization — the LLM only ever sees fake stand-ins, but your
    # app gets back the real name/email in the final response.
    config = OrchestrationConfig(
        template=template,
        llm=LLM(name="gpt-4o-mini"),
        data_masking=build_masking(method=MaskingMethod.PSEUDONYMIZATION),
    )

    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(
            name="text",
            value=(
                "Tell Dr. Emily Smith at emily.smith@healthclinic.com that "
                "I need to reschedule my 2024-12-15 appointment."
            ),
        )],
    )
    print("Pseudonymized round-trip result:")
    print(result.orchestration_result.choices[0].message.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Anonymization vs pseudonymization — what's the real difference?
A: Anonymization is one-way (original value discarded, replaced with a
   generic label) — used when the LLM truly never needs the real value
   back. Pseudonymization is reversible for the life of that single
   call — the LLM works with a consistent fake value, and orchestration
   automatically restores the real value in the response your app
   receives, so the provider's servers/logs never see the real PII.

Q: Where in the pipeline does masking run relative to templating and
   the LLM call?
A: Masking runs FIRST — before placeholders are substituted into the
   template and before the LLM call — so masked values are what
   actually get sent to the model.

Q: Why would you need an allowlist?
A: To stop the masking classifier from over-matching — e.g. your own
   product name might pattern-match as an ORG entity and get masked
   unnecessarily, breaking answers that legitimately need to mention it.

Q: How does this relate to GDPR / compliance requirements?
A: It lets you use a third-party hosted LLM while keeping raw personal
   data out of that provider's infrastructure and logs — a common
   requirement in regulated industries (finance, healthcare, HR).
------------------------------------------------------------
"""
