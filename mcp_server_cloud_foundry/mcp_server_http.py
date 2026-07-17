"""
============================================================
MINI TEMPLATE — MCP Server over HTTP (Cloud Foundry-ready)
============================================================
Use this when: you need your MCP server reachable over a
network URL instead of spawned as a local subprocess — this
is the REQUIRED shape for anything Joule Studio, a remote AI
coding agent, or any client not running on the same machine
will connect to.

What changes vs. mcp_server_basic.py:
  1. Transport is "http" (Streamable HTTP) instead of "stdio".
  2. The port is read from $PORT — Cloud Foundry assigns this
     dynamically at container start; you never hardcode it.
  3. A /health custom route is added for CF's health-check
     monitor (and any load balancer) to poll.
  4. host="0.0.0.0" — CF containers must bind all interfaces,
     not just localhost, or the platform can't route to them.

This file is intentionally UNAUTHENTICATED — use it only for
local HTTP testing or throwaway lab environments. For anything
with real data behind it, deploy mcp_server_secured.py instead.

Setup:
  pip install fastmcp
  python mcp_server_http.py
  → served at http://localhost:8000/mcp (PORT defaults to 8000
    locally; Cloud Foundry overrides it automatically)
============================================================
"""

import os
from fastmcp import FastMCP
from starlette.responses import JSONResponse

# Re-use the exact same tool definitions as the stdio version —
# MCP tool logic never changes based on transport.
from mcp_server_basic import mcp


# ── Health check route ────────────────────────────────────
# Cloud Foundry pings this on the app's assigned route to decide
# if the container is healthy. Custom routes are NEVER covered
# by MCP auth middleware — that's correct here, since a health
# probe shouldn't need a token.
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "sap-demo-mcp-server"})


if __name__ == "__main__":
    # Cloud Foundry injects PORT into the container's environment
    # at runtime — you request a port, CF's Diego scheduler assigns
    # whatever is actually free and maps the app's public route to
    # it. Hardcoding a port here would fail deployment.
    port = int(os.environ.get("PORT", 8000))

    mcp.run(
        transport="http",   # Streamable HTTP — the modern remote MCP transport
        host="0.0.0.0",     # bind all interfaces; required inside a CF container
        port=port,
        path="/mcp",        # final endpoint: https://<route>/mcp
    )


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why must a Cloud Foundry app read its port from an
   environment variable instead of hardcoding it?
A: CF's scheduler (Diego) runs many containers on shared hosts
   and assigns each app instance whatever port is free on that
   host at that moment, then maps the platform's public route to
   it via the Gorouter — the app has no control over, or advance
   knowledge of, which port that will be.

Q: Why host="0.0.0.0" and not "127.0.0.1"?
A: 127.0.0.1 only accepts connections originating from inside
   the same container/process — CF's router sits outside the
   container and forwards traffic in over the network interface,
   so the app must listen on all interfaces to be reachable.

Q: What is "Streamable HTTP" and why did MCP move to it?
A: It's the current standard remote MCP transport — a single
   HTTP endpoint that supports both regular request/response and
   Server-Sent-Events-based streaming (for progress updates,
   long-running tools) over the same connection, replacing the
   older, more complex dual-endpoint SSE transport.

Q: Why is the /health route excluded from MCP auth by design?
A: Health checks are called by infrastructure (CF's health
   monitor, load balancers, Kubernetes probes) that doesn't hold
   an MCP client credential — requiring auth on it would make the
   platform unable to verify the app is alive, causing false
   "unhealthy" restarts.

Q: This file has zero authentication — what's the actual risk?
A: Anyone with the route URL can call every tool and read
   whatever data those tools expose — acceptable for a throwaway
   demo behind a private CF space, unacceptable the moment real
   business data or write actions are involved. See
   mcp_auth_jwt.py / mcp_server_secured.py for the fix.
------------------------------------------------------------
"""

