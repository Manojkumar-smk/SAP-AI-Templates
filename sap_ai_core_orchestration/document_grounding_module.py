"""
============================================================
MINI TEMPLATE — Document Grounding Module
============================================================
Use this when: you want RAG (retrieval-augmented generation)
WITHOUT hand-building the retrieval pipeline yourself.

What the Document Grounding module does:
  Given a user question, orchestration retrieves relevant
  chunks from a configured data repository (a vector store —
  SAP's managed Document Grounding service, or your own
  repository registered with AI Core) and injects the
  retrieved text into the prompt automatically, via two
  linked placeholders:
    input  → the placeholder holding the user's question
             (what gets embedded and searched with)
    output → the placeholder that gets filled with the
             retrieved context chunks

Compare with the hand-rolled RAG in ../hana_rag/rag_pipeline.py:
  hana_rag/          → YOU call the embedding model, YOU query
                        HANA Vector Engine, YOU build the prompt.
                        Full control, more code to maintain.
  This module         → SAP AI Core does retrieval + injection
                        for you as one pipeline step. Less code,
                        less control over the exact retrieval logic.
  Use orchestration grounding for standard RAG; use the hana_rag/
  manual pipeline when you need custom retrieval logic (hybrid
  search, re-ranking, multi-table joins, etc.).

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  A grounding data repository must already exist and have documents
  ingested (via AI Launchpad → Document Grounding, or the HANA Vector
  Engine grounding connector).
  python document_grounding_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig
from gen_ai_hub.orchestration.models.document_grounding import (
    DocumentGrounding,
    DocumentGroundingFilter,
    GroundingModule,
)

from orchestration_setup import get_orchestration_service


def build_grounding(
    input_placeholder: str = "groundingRequest",
    output_placeholder: str = "groundingOutput",
    data_repositories: list[str] = None,
) -> GroundingModule:
    """
    Builds a grounding module config.

    Args:
        input_placeholder  : name of the placeholder that holds the query
                              orchestration should search with
        output_placeholder : name of the placeholder that gets filled
                              with retrieved context chunks
        data_repositories   : which repositories to search — "*" searches
                              every repository visible to the resource group
    """
    return GroundingModule(
        input_params=[input_placeholder],
        output_param=output_placeholder,
        filters=[
            DocumentGroundingFilter(
                id="default_filter",
                data_repositories=data_repositories or ["*"],
            )
        ],
    )


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()

    template = Template(messages=[
        SystemMessage(
            "Answer the user's question using ONLY the provided context. "
            "If the context doesn't contain the answer, say you don't know."
        ),
        UserMessage("Question: {{?groundingRequest}}\nContext: {{?groundingOutput}}"),
    ])

    config = OrchestrationConfig(
        template=template,
        llm=LLM(name="gpt-4o-mini", parameters={"temperature": 0}),
        grounding=DocumentGrounding(module_config=build_grounding()),
    )

    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(
            name="groundingRequest",
            value="What is SAP AI Core's Orchestration Service used for?",
        )],
    )
    print("Grounded answer:", result.orchestration_result.choices[0].message.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: How does grounding wire retrieved context into the prompt?
A: Via two linked placeholders — the module reads the query from an
   `input_params` placeholder, runs retrieval, and writes the result
   into an `output_param` placeholder. Your Template references BOTH
   placeholders in the UserMessage so the model sees question + context.

Q: When would you use orchestration's managed grounding vs a manual
   pipeline like hana_rag/rag_pipeline.py?
A: Managed grounding: faster to stand up, no retrieval code to
   maintain, works well for standard document Q&A. Manual pipeline:
   needed when you require custom retrieval logic — hybrid keyword +
   vector search, re-ranking, joining retrieval with live SQL data,
   or fine-grained control over chunk scoring thresholds.

Q: How does grounding interact with data masking?
A: Masking can optionally be applied to grounding input/output too
   (mask_grounding_input flag on the masking provider) so retrieved
   document text is also scrubbed of PII before hitting the LLM.

Q: What happens if no relevant documents are found?
A: The output placeholder is filled with empty/near-empty context —
   your system prompt should explicitly instruct the model to say
   "I don't know" rather than hallucinate an answer, as shown above.
------------------------------------------------------------
"""
