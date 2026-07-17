"""
============================================================
MINI TEMPLATE — Full Tool-Calling Agent Loop (the "project")
============================================================
Use this when: a single tool call isn't enough — you want a
runnable loop that keeps calling tools and feeding results back
to the LLM until it produces a final text answer. Neither
LangChain's bind_tools() nor the native OpenAI client run this
loop FOR you — this file IS the loop.

The loop, conceptually:
  1. Send the conversation so far to the LLM (tools bound).
  2. If the response has NO tool_calls → that's the final answer, stop.
  3. If it DOES have tool_calls → for each one:
       a. execute the real Python function
       b. append the result as a ToolMessage, tagged with the
          tool_call_id so the model knows which call it answers
  4. Go back to step 1 with the updated conversation.
  A max_turns cap prevents an infinite loop if the model keeps
  calling tools forever (e.g. arguing with a tool's error message).

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python tool_calling_agent.py
============================================================
"""

from langchain_core.messages import HumanMessage, ToolMessage

from llm_setup import get_langchain_llm
from tool_definitions import convert_currency, get_material_stock, TOOL_REGISTRY

TOOLS = [convert_currency, get_material_stock]


class ToolCallingAgent:
    """A minimal agent that runs the bind-call-feedback loop to completion."""

    def __init__(self, model: str = "gpt-4o-mini", max_turns: int = 5):
        self.llm = get_langchain_llm(model=model).bind_tools(TOOLS)
        self.max_turns = max_turns

    def run(self, question: str) -> str:
        messages = [HumanMessage(content=question)]

        for turn in range(self.max_turns):
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                # No more tools requested — this IS the final answer.
                return response.content

            for call in response.tool_calls:
                fn = TOOL_REGISTRY.get(call["name"])
                try:
                    if fn is None:
                        raise ValueError(f"Unknown tool: {call['name']}")
                    result = fn(**call["args"])
                    content = str(result)
                except Exception as e:
                    # Feed the ERROR back to the model instead of crashing —
                    # a well-behaved model can often recover (e.g. retry with
                    # corrected arguments, or apologize to the user) if it
                    # sees why the call failed.
                    content = f"Error calling {call['name']}: {e}"

                messages.append(ToolMessage(content=content, tool_call_id=call["id"]))

        return "⚠️ Max turns reached without a final answer — possible tool-call loop."


if __name__ == "__main__":
    agent = ToolCallingAgent()

    print("--- Single tool call ---")
    print(agent.run("How much is 250 GBP in INR?"))

    print("\n--- Multi-step: needs stock lookup then a currency question ---")
    print(agent.run(
        "Check the stock for MAT-1002 at plant 1020, then tell me what a "
        "purchase of 500 units at $12 each would cost in EUR."
    ))

    print("\n--- No tool needed ---")
    print(agent.run("In one sentence, what is SAP BTP?"))


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why append the FULL response object (messages.append(response))
   instead of just response.content?
A: The model needs to see its OWN prior tool_calls in the
   conversation history to correctly interpret the ToolMessage
   replies that follow — an AIMessage with tool_calls IS the
   thing a ToolMessage's tool_call_id correlates against. Only
   keeping .content would silently break multi-tool-call turns.

Q: Why try/except around the tool call instead of letting the
   agent crash on bad arguments?
A: A production agent talking to a real LLM WILL occasionally get
   malformed or nonsensical arguments — swallowing the error and
   feeding it back as a ToolMessage lets the model see "you asked
   for X, that failed because Y" and often self-correct on the
   next turn, which is strictly better UX than a stack trace.

Q: What actually stops this loop from running forever?
A: max_turns is the hard cap. In practice, well-behaved models
   converge in 1-3 turns for simple multi-step tasks; the cap
   exists purely as a safety net against a model that keeps
   re-calling a tool (e.g. one that keeps failing) instead of
   giving up and answering with what it has.

Q: How would you adapt this loop to also work with the ORCHESTRATION
   Service's tool calling (see sap_ai_core_orchestration/tool_calling_module.py)
   instead of the direct LangChain proxy?
A: The control flow is identical (detect tool_calls → execute →
   feed back → re-run) but the message types differ — Orchestration
   v2 uses its own AssistantMessage/ToolChatMessage pydantic models
   and a `history` list passed to service.run(), not LangChain's
   AIMessage/ToolMessage. The LOOP SHAPE transfers; the specific
   classes don't.
------------------------------------------------------------
"""
