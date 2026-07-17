"""
============================================================
MINI TEMPLATE — Shared Tool Definitions (framework-agnostic)
============================================================
Use this when: you want ONE set of plain Python functions that
can be exposed to an LLM through EITHER LangChain's bind_tools()
OR the raw OpenAI-compatible tools=[...] parameter — without
writing the JSON Schema twice.

How the schema gets generated from these functions:
  Both tool_calling_langchain.py and tool_calling_native.py use
  LangChain's `convert_to_openai_tool()` utility to turn a plain
  function into an OpenAI-format tool schema. It reads:
    - the function name          → schema "name"
    - the first docstring line   → schema "description"
    - the "Args:" section        → per-parameter descriptions
    - the type hints              → per-parameter JSON types
  This works whether the function is later bound via LangChain
  or passed straight to openai.chat.completions.create(tools=[...]).

Same demo tools as mcp_server_cloud_foundry/mcp_tools_common.py —
compare the two folders to see how the SAME business logic gets
exposed two different ways: as an MCP server (for Joule Studio /
external agents to discover over a network) vs. as direct LLM
tool/function calling (for a single Python process's own LLM call).
============================================================
"""


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between currencies using a fixed demo rate table.

    Args:
        amount: the numeric amount to convert.
        from_currency: three-letter source currency code, e.g. USD.
        to_currency: three-letter target currency code, e.g. EUR.
    """
    rates_to_usd = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012, "JPY": 0.0067}

    from_currency, to_currency = from_currency.upper(), to_currency.upper()
    if from_currency not in rates_to_usd or to_currency not in rates_to_usd:
        raise ValueError(f"Unsupported currency. Supported: {list(rates_to_usd)}")

    usd_value = amount * rates_to_usd[from_currency]
    converted = usd_value / rates_to_usd[to_currency]

    return {
        "amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": round(converted, 2),
    }


def get_material_stock(material_id: str, plant: str = "1010") -> dict:
    """Look up available stock quantity for a material at a plant.

    Args:
        material_id: the SAP material number, e.g. MAT-1001.
        plant: the four-digit plant code, defaults to 1010.
    """
    demo_stock_db = {
        "MAT-1001": {"1010": 250, "1020": 40},
        "MAT-1002": {"1010": 0, "1020": 900},
    }

    material_id = material_id.upper()
    if material_id not in demo_stock_db:
        return {"material_id": material_id, "plant": plant, "found": False}

    qty = demo_stock_db[material_id].get(plant, 0)
    return {"material_id": material_id, "plant": plant, "found": True, "quantity_available": qty}


# Name → callable lookup, used by the agent loop to execute whichever
# tool the LLM decided to call, purely from the string name it returns.
TOOL_REGISTRY = {
    "convert_currency": convert_currency,
    "get_material_stock": get_material_stock,
}


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why generate the JSON Schema from the function instead of
   hand-writing it?
A: Two sources of truth (the function's real signature and a
   hand-written schema) inevitably drift apart — someone adds a
   parameter and forgets to update the schema, and the LLM starts
   calling the function wrong. Deriving the schema from the
   function's own type hints and docstring makes drift impossible.

Q: Why does the docstring need an "Args:" section specifically?
A: convert_to_openai_tool() (via LangChain's docstring parser)
   looks for that section to extract PER-PARAMETER descriptions —
   without it, the LLM still gets parameter names and types (from
   the type hints) but no explanation of what each one means,
   which hurts the model's ability to fill them in correctly.

Q: What's TOOL_REGISTRY for, and why a dict instead of an if/elif chain?
A: When the LLM returns a tool_call with a string name, you need
   to map that string back to a real callable. A dict lookup is
   O(1) and, more importantly, doesn't need editing every time a
   tool is added — the registry and the tool list can even be
   derived from the same dict's keys.

Q: These functions raise/return dummy data — what would change for
   production use?
A: Nothing about the MCP/tool-calling plumbing — only the function
   bodies would change, e.g. convert_currency() calling a live FX
   API, get_material_stock() calling S/4HANA's OData API through a
   BTP Destination instead of reading a hardcoded dict.
------------------------------------------------------------
"""
