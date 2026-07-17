"""
============================================================
MINI TEMPLATE — Shared Tool Logic (framework-agnostic)
============================================================
Use this when: you want to see the production-grade pattern
for structuring MCP tools — plain, undecorated Python functions
that contain the actual business logic, kept separate from any
particular FastMCP server instance.

Why keep these UNDECORATED here:
  @mcp.tool binds a function to ONE specific FastMCP server
  object. This project needs the same three tools available on
  TWO different servers (the unsecured demo in mcp_server_basic.py
  and the authenticated production server in mcp_server_secured.py).
  Keeping the logic here and registering it separately on each
  server (via mcp.tool(fn) in each entrypoint) avoids duplicating
  the function bodies and avoids any ambiguity about registering
  an already-decorated tool object onto a second server.
============================================================
"""


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """
    Convert an amount between currencies using a fixed demo rate table.
    In a real deployment this would call an S/4HANA or market-data API
    instead of a hardcoded dict.
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
    """
    Look up available stock quantity for a material at a plant.
    Demo data only — in production this would call the S/4HANA
    OData API (e.g. API_MATERIAL_STOCK_SRV) through a BTP Destination.
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


def search_sap_notes(keyword: str, max_results: int = 3) -> list:
    """Search a demo knowledge base of SAP Notes by keyword (dummy data)."""
    demo_notes = [
        {"note_id": "2926224", "title": "HANA Cloud connection troubleshooting"},
        {"note_id": "3089828", "title": "AI Core deployment stuck in UNKNOWN state"},
        {"note_id": "3142233", "title": "XSUAA JWT validation errors on Cloud Foundry"},
    ]
    keyword = keyword.lower()
    matches = [n for n in demo_notes if keyword in n["title"].lower()]
    return matches[:max_results]


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why not just put @mcp.tool directly on these functions and
   import the decorated versions into the secured server too?
A: A decorator like @mcp.tool typically binds/registers the
   function against the specific server instance it was applied
   to at decoration time. Needing the same logic exposed by two
   different server objects (unsecured demo vs. authenticated
   production) is exactly the case where you keep the logic
   framework-agnostic and register it explicitly per instance,
   rather than fighting the decorator's binding behavior.

Q: Isn't this just the standard "separate business logic from
   framework glue" principle?
A: Yes — same reasoning as keeping Flask/FastAPI route handlers
   thin and calling into plain service functions. MCP tool
   registration is glue code; what the tool actually DOES
   shouldn't need to know or care which server object exposes it.

Q: What would you change here before this touched real SAP data?
A: Replace the demo dicts with actual calls to S/4HANA OData
   services or HANA Cloud queries, add input validation beyond
   the currency whitelist, and add structured logging so a
   security review can trace which caller invoked which tool
   with which arguments.
------------------------------------------------------------
"""
