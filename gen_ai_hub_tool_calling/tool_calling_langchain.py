"""
============================================================
MINI TEMPLATE — Tool Calling via LangChain bind_tools()
============================================================
Use this when: you're already in a LangChain codebase (chains,
LCEL, agents) and want the LLM to be able to call your Python
functions, using LangChain's own tool-call representation.

What bind_tools() actually does:
  It does NOT call your functions. It returns a NEW llm object
  that, on invoke(), includes each bound function's JSON Schema
  in the request to the model. If the model decides a function
  should be called, the response's .tool_calls list describes
  WHICH function and WITH WHAT arguments — executing the function
  and feeding the result back is still your job (see
  tool_calling_agent.py for the full loop).

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python tool_calling_langchain.py
============================================================
"""

from langchain.schema import HumanMessage

from llm_setup import get_langchain_llm
from tool_definitions import convert_currency, get_material_stock, TOOL_REGISTRY


def ask_with_tools(question: str):
    """
    Sends one question to the LLM with tools bound, and returns
    the raw response — showing whether the model chose to answer
    directly or call a tool.
    """
    llm = get_langchain_llm()

    # bind_tools() accepts plain functions directly — LangChain
    # internally calls the same convert_to_openai_tool() schema
    # generation used explicitly in tool_calling_native.py.
    llm_with_tools = llm.bind_tools([convert_currency, get_material_stock])

    response = llm_with_tools.invoke([HumanMessage(content=question)])
    return response


if __name__ == "__main__":
    print("--- Question that SHOULD trigger a tool call ---")
    response = ask_with_tools("How much is 100 USD in EUR?")

    if response.tool_calls:
        for call in response.tool_calls:
            print(f"Model wants to call: {call['name']}({call['args']})")
            # Execute it ourselves — bind_tools() never does this part.
            fn = TOOL_REGISTRY[call["name"]]
            result = fn(**call["args"])
            print("Tool result:", result)
    else:
        print("Model answered directly (no tool call):", response.content)

    print("\n--- Question that should NOT trigger a tool call ---")
    response = ask_with_tools("What's the capital of France?")
    if response.tool_calls:
        print("Unexpected tool call:", response.tool_calls)
    else:
        print("Model answered directly:", response.content)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Does bind_tools() FORCE the model to call a tool?
A: No, by default the model decides — it can answer directly, call
   one tool, or call several in parallel. Forcing a specific tool
   (or forcing SOME tool call) is a separate setting, usually
   `tool_choice`, which most LangChain chat models also expose.

Q: What's actually inside response.tool_calls?
A: A list of dicts, each with 'name' (the function name string),
   'args' (already-parsed keyword arguments as a dict — LangChain
   parses the JSON for you here, unlike the native path), and 'id'
   (needed later to correlate a ToolMessage back to this specific call).

Q: Why does the second example question ("capital of France") matter
   as a test case?
A: It proves the binding is advisory, not mandatory — a good tool
   integration test always includes a question with NO relevant
   tool, to confirm the model doesn't hallucinate a tool call it
   doesn't need (which would silently break a production agent).

Q: If the model calls a tool with a typo'd or missing argument, where
   does that fail — this file, or LangChain itself?
A: Neither, cleanly — call['args'] would just contain whatever
   the model generated, and fn(**call['args']) would raise a plain
   Python TypeError for a missing required argument. Production
   code should catch that and feed the error back to the model as
   the tool result, rather than crashing the whole request.
------------------------------------------------------------
"""
