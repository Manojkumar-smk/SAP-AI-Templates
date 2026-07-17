"""
============================================================
MINI TEMPLATE — Tool Calling via the Native OpenAI-Compatible Client
============================================================
Use this when: you want zero LangChain dependency, or you're
already writing raw OpenAI-SDK-style code and want tool calling
to look exactly like the vanilla `openai` package's API — because
gen_ai_hub.proxy.native.openai IS that package, routed through
SAP AI Core instead of straight to OpenAI/Azure.

Key difference from the LangChain path:
  The response's tool call arguments arrive as a JSON STRING
  (`call.function.arguments`), not a pre-parsed dict — you must
  json.loads() it yourself. This matches the real OpenAI API
  exactly, which is the point of using the native client.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python tool_calling_native.py
============================================================
"""

import json
from langchain_core.utils.function_calling import convert_to_openai_tool

from llm_setup import get_native_chat_client
from tool_definitions import convert_currency, get_material_stock, TOOL_REGISTRY

# Reuse LangChain's schema-generation utility to build the raw
# OpenAI tools=[...] array from the SAME plain functions used in
# tool_calling_langchain.py — no hand-written JSON Schema, no
# second source of truth to keep in sync.
TOOLS_SCHEMA = [
    convert_to_openai_tool(convert_currency),
    convert_to_openai_tool(get_material_stock),
]


def ask_with_tools(question: str):
    """Sends one question through the native client with tools attached."""
    chat = get_native_chat_client()

    messages = [{"role": "user", "content": question}]
    response = chat.completions.create(
        model_name="gpt-4o-mini",
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_choice="auto",  # "auto" (default) | "required" | "none" | {"type": "function", "function": {"name": "..."}}
    )
    return response


if __name__ == "__main__":
    print("--- Question that SHOULD trigger a tool call ---")
    response = ask_with_tools("What's the stock for MAT-1001 at plant 1010?")
    message = response.choices[0].message

    if message.tool_calls:
        for call in message.tool_calls:
            args = json.loads(call.function.arguments)  # <-- manual parse, unlike LangChain's pre-parsed dict
            print(f"Model wants to call: {call.function.name}({args})")
            fn = TOOL_REGISTRY[call.function.name]
            result = fn(**args)
            print("Tool result:", result)
    else:
        print("Model answered directly:", message.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why json.loads(call.function.arguments) here but NOT in
   tool_calling_langchain.py?
A: LangChain's ChatOpenAI wrapper parses the raw OpenAI response
   into its own AIMessage.tool_calls representation and does the
   JSON parsing for you as part of that conversion. The native
   client returns the OpenAI API's response verbatim, where
   function arguments are always a JSON-encoded string — parsing
   is the caller's responsibility.

Q: What does tool_choice="required" change, versus the default "auto"?
A: "auto" lets the model choose freely (including not calling any
   tool). "required" forces it to call at least one of the
   provided tools no matter what — useful when you're using tool
   calling purely as a structured-output mechanism and a plain
   text answer would be a bug, not a valid response.

Q: Why reuse convert_to_openai_tool() from LangChain here, given
   this file's whole point is avoiding a LangChain dependency for
   the CALL itself?
A: It's a schema-generation utility, not a client — using it to
   build TOOLS_SCHEMA once at import time doesn't add LangChain
   to your runtime request path, it just avoids hand-duplicating
   JSON Schema that tool_calling_langchain.py already derives the
   same way from the same functions.

Q: What happens if you omit tool_choice entirely?
A: Same behavior as "auto" — it's the OpenAI API's default, so
   passing it explicitly here is a documentation choice (makes
   the available values visible in the code) rather than a
   functional necessity.
------------------------------------------------------------
"""
