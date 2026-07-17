"""
============================================================
MINI TEMPLATE — Tool Calling in the Orchestration Service (v2 API)
============================================================
Use this when: you want tool/function calling INSIDE an
Orchestration Service pipeline (masking, filtering, grounding,
etc. can all still run alongside it) rather than on a raw LLM
proxy call — see ../gen_ai_hub_tool_calling/ for the non-
orchestration version of the same idea.

IMPORTANT — this file uses gen_ai_hub.orchestration_v2, NOT
gen_ai_hub.orchestration (v1) like every other file in this folder:
  Verified directly against the installed SDK (sap-ai-sdk-gen
  6.10.0): OrchestrationConfig in v1 (orchestration_setup.py,
  llm_module.py, orchestration_pipeline.py, etc.) has NO `tools`
  parameter anywhere — templating_module.py's Template class and
  llm_module.py's LLM class simply don't support it. Tool calling
  only exists in the newer v2 API, which also restructures how a
  config is built (nested ModuleConfig/PromptTemplatingModuleConfig
  objects instead of flat template=/llm= kwargs) and how a response
  is read (`response.final_result` instead of v1's
  `response.orchestration_result`). This module is therefore
  SELF-CONTAINED — it does not plug into orchestration_pipeline.py
  or orchestration_agent.py, which are still v1.

What tool calling adds to the pipeline:
  The LLM module config can list FunctionTool definitions. When the
  model decides a function should run, the response's
  final_result.choices[0].message.tool_calls tells you which
  function and with what (already-a-dict, no JSON parsing needed —
  see FunctionCall.parse_arguments()). Same as the raw proxy: the
  SDK does NOT run an agentic loop for you — see run_tool_calling_loop()
  below for that.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python tool_calling_module.py
============================================================
"""

import os
from dotenv import load_dotenv

from gen_ai_hub.orchestration_v2 import (
    OrchestrationService,
    OrchestrationConfig,
    ModuleConfig,
    PromptTemplatingModuleConfig,
    Template,
    LLMModelDetails,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolChatMessage,
    function_tool,
)

load_dotenv()


# ── Tools, defined the orchestration-v2 way ───────────────
# @function_tool reads the type hints + docstring, same principle
# as gen_ai_hub_tool_calling/tool_definitions.py, but produces a
# FunctionTool object (a pydantic model) instead of a plain dict.
@function_tool
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between currencies using a fixed demo rate table."""
    rates_to_usd = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012, "JPY": 0.0067}
    from_currency, to_currency = from_currency.upper(), to_currency.upper()
    if from_currency not in rates_to_usd or to_currency not in rates_to_usd:
        raise ValueError(f"Unsupported currency. Supported: {list(rates_to_usd)}")
    converted = (amount * rates_to_usd[from_currency]) / rates_to_usd[to_currency]
    return {"converted_amount": round(converted, 2), "to_currency": to_currency.upper()}


@function_tool
def get_material_stock(material_id: str, plant: str = "1010") -> dict:
    """Look up available stock quantity for a material at a plant."""
    demo_stock_db = {"MAT-1001": {"1010": 250, "1020": 40}, "MAT-1002": {"1010": 0, "1020": 900}}
    material_id = material_id.upper()
    if material_id not in demo_stock_db:
        return {"material_id": material_id, "plant": plant, "found": False}
    return {"material_id": material_id, "plant": plant, "found": True,
            "quantity_available": demo_stock_db[material_id].get(plant, 0)}


TOOLS = [convert_currency, get_material_stock]
TOOL_REGISTRY = {t.function.name: t for t in TOOLS}


def get_orchestration_service_v2() -> OrchestrationService:
    """
    Builds a v2 OrchestrationService client. Deliberately separate from
    orchestration_setup.py's get_orchestration_service() — the v1 and
    v2 clients are different classes from different modules and are
    not interchangeable, even though both auto-discover a running
    orchestration deployment the same way (AICORE_* env vars).
    """
    api_url = os.getenv("ORCHESTRATION_DEPLOYMENT_URL")
    return OrchestrationService(api_url=api_url) if api_url else OrchestrationService()


def build_tool_calling_config(question: str) -> OrchestrationConfig:
    """Builds a v2 OrchestrationConfig with tools attached to the prompt template."""
    template = Template(
        template=[
            SystemMessage(content="You are a helpful SAP business assistant."),
            UserMessage(content=question),
        ],
        tools=TOOLS,
    )
    return OrchestrationConfig(
        modules=ModuleConfig(
            prompt_templating=PromptTemplatingModuleConfig(
                prompt=template,
                model=LLMModelDetails(name="gpt-4o-mini"),
            )
        )
    )


def run_tool_calling_loop(question: str, max_turns: int = 5) -> str:
    """
    The agentic loop for orchestration-v2 tool calling — structurally
    identical to gen_ai_hub_tool_calling/tool_calling_agent.py's loop,
    but built from v2's own message classes (AssistantMessage,
    ToolChatMessage) and passed via the `history` parameter of
    service.run(), not LangChain messages.
    """
    service = get_orchestration_service_v2()
    config = build_tool_calling_config(question)
    history = []

    for turn in range(max_turns):
        response = service.run(config=config, history=history or None)
        message = response.final_result.choices[0].message

        if not message.tool_calls:
            return message.content

        # The model's own tool-call turn must go into history so the
        # ToolChatMessage replies below have something to correlate against.
        history.append(AssistantMessage(content=message.content, tool_calls=message.tool_calls))

        for call in message.tool_calls:
            tool = TOOL_REGISTRY.get(call.function.name)
            try:
                if tool is None:
                    raise ValueError(f"Unknown tool: {call.function.name}")
                args = call.function.parse_arguments()
                result = tool.execute(**args)
                content = str(result)
            except Exception as e:
                content = f"Error calling {call.function.name}: {e}"

            history.append(ToolChatMessage(tool_call_id=call.id, content=content))

    return "⚠️ Max turns reached without a final answer."


if __name__ == "__main__":
    print("--- Single tool call ---")
    print(run_tool_calling_loop("How much is 250 GBP in INR?"))

    print("\n--- No tool needed ---")
    print(run_tool_calling_loop("In one sentence, what is SAP BTP?"))


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why can't tool calling be added to the OTHER files in this
   folder (orchestration_pipeline.py, orchestration_agent.py)
   just by importing FunctionTool into them?
A: Those files build v1 OrchestrationConfig/Template/LLM objects,
   which have no `tools` field at all (confirmed by reading the
   installed SDK's source) — tool calling is a v2-only capability
   with a different, incompatible object model. Mixing v1 and v2
   classes in one config isn't supported; you'd need to port the
   whole pipeline to v2 to add tool calling to it.

Q: What's structurally different about v2's config compared to v1's
   flat `OrchestrationConfig(template=..., llm=...)`?
A: v2 nests everything inside `ModuleConfig.prompt_templating`
   (a `PromptTemplatingModuleConfig` holding both the `Template`
   AND the `LLMModelDetails` together), and `tools` lives on the
   `Template` itself, not on the LLM config — a v1 developer's
   first instinct to look for a `tools=` kwarg on the LLM class
   will be wrong for v2.

Q: How do you read the model's answer in v2 vs v1?
A: v1: `response.orchestration_result.choices[0].message.content`.
   v2: `response.final_result.choices[0].message.content`. Different
   attribute name on the response object — another incompatibility
   between the two generations of the SDK.

Q: Why does the history list use AssistantMessage + ToolChatMessage
   pairs instead of just appending the tool RESULT as a new
   UserMessage?
A: The model needs to see, structurally, that a specific tool_call_id
   was answered — a plain UserMessage loses that correlation and
   risks the model re-requesting the same tool call, or misreading
   whose turn it is in a multi-tool-call response.

Q: This module hardcodes "gpt-4o-mini" — how would you make the model
   configurable without breaking tool calling?
A: Pass a different LLMModelDetails(name=...) into
   build_tool_calling_config() — tool calling is a Template-level
   concern (the `tools` list), completely orthogonal to which model
   the LLMModelDetails names, as long as that model supports function
   calling.
------------------------------------------------------------
"""
