"""
============================================================
MINI TEMPLATE — MCP Server Fundamentals (stdio, local)
============================================================
Use this when: you're learning MCP itself — no BTP, no HTTP,
no auth. Just Python functions turned into LLM-callable tools,
run locally over stdio (the transport an AI coding assistant
like Claude Code / Cline / Cursor uses to launch your server
as a subprocess).

What MCP actually is:
  A protocol (JSON-RPC based) that lets an LLM-driven client
  discover a server's "tools" (functions), read their schemas
  (auto-generated from type hints + docstrings), and call them
  with structured arguments — instead of you hand-writing a
  custom function-calling integration per LLM provider.

Setup:
  pip install fastmcp
  python mcp_server_basic.py
  (then, separately: python mcp_client_test.py  to call it)
============================================================
"""

from fastmcp import FastMCP
from mcp_tools_common import convert_currency, get_material_stock, search_sap_notes

# ── The server object ─────────────────────────────────────
# The string name shows up in MCP client UIs (Claude Desktop,
# Joule Studio's tool picker, etc.) as the server's identity.
mcp = FastMCP("SAP Demo Tools 🛠️")

# ── Register the shared tool functions on THIS server ─────
# mcp.tool(fn) is the direct-call form of the same decorator you'll
# see written as "@mcp.tool" elsewhere — used here (instead of the
# decorator syntax) because these functions are defined once in
# mcp_tools_common.py and registered on two separate FastMCP server
# objects (this unsecured one, and the authenticated one in
# mcp_server_secured.py). FastMCP inspects each function's type
# hints + docstring to auto-generate its JSON Schema at registration time.
mcp.tool(convert_currency)
mcp.tool(get_material_stock)
mcp.tool(search_sap_notes)


if __name__ == "__main__":
    # Default transport is "stdio" — the server reads/writes MCP
    # JSON-RPC messages over stdin/stdout. This is what desktop
    # MCP clients (and CLI coding agents) expect when they spawn
    # your script as a subprocess. There is no network port here.
    mcp.run()


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What is MCP, in one sentence?
A: An open, JSON-RPC-based protocol that standardizes how an
   LLM client discovers and calls external "tools" (functions),
   "resources" (readable data), and "prompts" (reusable templates)
   exposed by a server — so you write one server instead of one
   custom integration per LLM vendor's function-calling format.

Q: How does FastMCP turn a Python function into an MCP tool?
A: The @mcp.tool decorator inspects the function's type hints
   and docstring to auto-generate a JSON Schema describing its
   name, parameters, and description — that schema is what the
   LLM actually "sees" when deciding whether/how to call it.

Q: Why does mcp.run() with no arguments use stdio and not HTTP?
A: stdio is the default because MCP's original and most common
   use case is a local client (e.g. an IDE AI assistant) spawning
   your script as a child process and talking to it over its
   stdin/stdout pipes — zero network config, zero auth needed,
   perfect for local dev and desktop tools.

Q: What's the difference between a "tool" and a "resource" in MCP?
A: A tool is an action the LLM can invoke with arguments (like a
   function call) and that may have side effects; a resource is
   read-only data the client can fetch (like a GET endpoint) —
   this file only shows tools, since that's what Joule Studio's
   agent builder consumes.

Q: Why keep get_material_stock() returning dummy data instead of
   calling S/4HANA directly in this file?
A: Separation of concerns for teaching purposes — the MCP
   plumbing (schema generation, protocol handling) is identical
   whether the function body calls a dict or a live OData
   service; swapping in the real API call doesn't change
   anything about how MCP works.
------------------------------------------------------------
"""
