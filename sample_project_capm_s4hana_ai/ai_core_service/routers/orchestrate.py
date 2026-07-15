"""
============================================================
Router — POST /api/orchestrate
============================================================
The endpoint CAP calls for the main "AI Assistant" scenario.
Uses SAP AI Core's Orchestration Service (content filtering +
structured JSON output) instead of a plain LLM call — see
sap_ai_core_orchestration/ mini templates for the full module
breakdown. Two jobs in one call:
  1. Answer the user in plain English.
  2. Classify whether this message is a POSTING request
     (e.g. "create a sales order for ...") and, if so,
     extract the structured fields CAP needs to call the
     S/4HANA RAP action.
============================================================
"""

import json
from fastapi import APIRouter, HTTPException
from gen_ai_hub.orchestration.service import OrchestrationService
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.content_filter import AzureContentFilter
from gen_ai_hub.orchestration.models.filtering import Filtering, InputFiltering, OutputFiltering
from gen_ai_hub.orchestration.models.response_format import ResponseFormatJsonSchema
from schemas import OrchestrateRequest, OrchestrateResponse

router = APIRouter()

# JSON schema forces the model to always return this exact shape — safe to json.loads() directly.
INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string", "description": "plain-English reply to show the user"},
        "is_posting_intent": {"type": "boolean", "description": "true if user wants to CREATE/POST a sales order"},
        "customer": {"type": "string", "description": "customer name or ID, empty string if not mentioned"},
        "material": {"type": "string", "description": "material name or ID, empty string if not mentioned"},
        "quantity": {"type": "integer", "description": "quantity requested, 0 if not mentioned"},
    },
    "required": ["answer", "is_posting_intent", "customer", "material", "quantity"],
    "additionalProperties": False,
}

STRICT_FILTER = AzureContentFilter(hate=0, sexual=0, self_harm=0, violence=0)


@router.post("/api/orchestrate", response_model=OrchestrateResponse)
def orchestrate(req: OrchestrateRequest) -> OrchestrateResponse:
    try:
        service = OrchestrationService()   # auto-discovers the orchestration deployment (see orchestration_setup.py)

        template = Template(
            messages=[
                SystemMessage(
                    "You are an SAP sales assistant. Answer the user, and separately determine "
                    "if they are asking to CREATE or POST a new sales order. If so, extract the "
                    "customer, material, and quantity mentioned."
                ),
                UserMessage("{{?text}}"),
            ],
            response_format=ResponseFormatJsonSchema(name="assistant_result", schema=INTENT_SCHEMA, strict=True),
        )

        config = OrchestrationConfig(
            template=template,
            llm=LLM(name="gpt-4o-mini", parameters={"temperature": 0}),
            filtering=Filtering(                                    # input+output safety, see content_filtering_module.py
                input_filtering=InputFiltering(filters=[STRICT_FILTER]),
                output_filtering=OutputFiltering(filters=[STRICT_FILTER]),
            ),
        )

        result = service.run(config=config, template_values=[TemplateValue(name="text", value=req.message)])
        parsed = json.loads(result.orchestration_result.choices[0].message.content)

        posting_payload = None
        if parsed["is_posting_intent"]:
            posting_payload = {                                     # exactly what CAP needs for the RAP OData call
                "customer": parsed["customer"],
                "material": parsed["material"],
                "quantity": parsed["quantity"],
            }

        return OrchestrateResponse(
            answer=parsed["answer"],
            is_posting_intent=parsed["is_posting_intent"],
            posting_payload=posting_payload,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Orchestration call failed: {e}")
