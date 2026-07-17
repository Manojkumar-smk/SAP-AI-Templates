"""
============================================================
MINI TEMPLATE — Production MCP Server (HTTP + JWT Auth)
============================================================
Use this when: this is the file you actually `cf push` for
anything with real data behind it. It combines:
  - the tools from mcp_server_basic.py
  - the Cloud Foundry HTTP wiring from mcp_server_http.py
  - the XSUAA/IAS JWT verification from mcp_auth_jwt.py
into one deployable entrypoint. This is also the file
manifest.yml points at by default.

Why auth is passed to FastMCP() instead of added as middleware:
  FastMCP's `auth=` parameter wires the verifier directly into
  the MCP protocol handling layer, so a rejected token returns a
  spec-compliant 401 with the right WWW-Authenticate header,
  before your tool code ever runs — you don't write any
  if-not-authenticated checks yourself.

Setup:
  pip install fastmcp
  cp .env.example .env   # fill in XSUAA_URL + XSUAA_XSAPPNAME
  python mcp_server_secured.py
============================================================
"""

import os
from fastmcp import FastMCP
from starlette.responses import JSONResponse

from mcp_auth_jwt import build_verifier_from_env
from mcp_tools_common import convert_currency, get_material_stock, search_sap_notes

# ── Build the authenticated server ────────────────────────
# Passing `auth=` here builds a SEPARATE FastMCP instance from the
# one in mcp_server_basic.py — auth is a property of the server
# object, not of an individual tool, so a production deployment
# needs its own instance with the verifier attached at construction.
verifier = build_verifier_from_env()
mcp = FastMCP("SAP Demo Tools (Secured)", auth=verifier)

# Register the SAME plain functions from mcp_tools_common.py onto
# this server. Because the logic lives in undecorated functions
# (not tool objects already bound to mcp_server_basic.py's server),
# registering it here is unambiguous — no duplicated business logic,
# no coupling to the unsecured demo server.
mcp.tool(convert_currency)
mcp.tool(get_material_stock)
mcp.tool(search_sap_notes)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    # Unauthenticated by design — see mcp_server_http.py for why.
    return JSONResponse({"status": "healthy", "service": "sap-demo-mcp-server-secured"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=port,
        path="/mcp",
        # Once deployed behind a real CF route, add it here so
        # FastMCP's Host/Origin protection trusts requests aimed
        # at your actual domain instead of only localhost:
        # allowed_hosts=["your-app.cfapps.eu10.hana.ondemand.com"],
    )


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why is auth wired via FastMCP(..., auth=verifier) instead of
   a hand-written "if no valid header, return 401" check inside
   each tool function?
A: Centralizing it means every tool is protected uniformly with
   zero chance of forgetting the check on a new tool, the
   rejection happens before your business logic runs (saving
   compute on invalid callers), and the 401 response is already
   MCP/OAuth spec-compliant (correct status code and headers)
   without you having to implement that by hand.

Q: Why does this file build a brand-new FastMCP instance instead
   of just running mcp_server_http.py with auth bolted on after
   the fact?
A: The `auth` verifier is passed into FastMCP's constructor — it's
   part of how the server object is built, not something you can
   attach to an already-created instance. Needing an authenticated
   and an unauthenticated server means needing two instances, which
   is why tool logic lives in mcp_tools_common.py and gets
   registered onto whichever instance needs it.

Q: What actually happens on the wire when an unauthenticated
   client hits POST /mcp on this server?
A: FastMCP's auth layer intercepts the request before it reaches
   the MCP session handler, finds no valid Bearer token, and
   returns an HTTP 401 with a WWW-Authenticate header — the
   client never gets far enough to see the tool list, let alone
   call one.

Q: Why does /health stay unauthenticated even on the secured server?
A: Same reasoning as the unsecured version — CF's platform-level
   health monitor has no MCP credential and isn't calling a tool;
   it just needs to confirm the process is alive and serving HTTP.
------------------------------------------------------------
"""
