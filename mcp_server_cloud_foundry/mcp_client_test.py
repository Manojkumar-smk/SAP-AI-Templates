"""
============================================================
MINI TEMPLATE — MCP Client (test / debug your own server)
============================================================
Use this when: you want to verify your server actually works —
list its tools and call one — WITHOUT setting up Joule Studio
or any other full MCP client. This is what you'd run right
after `cf push` to sanity-check a deployment, or run locally
against mcp_server_basic.py / mcp_server_http.py during dev.

This file has two modes, chosen by which MCP_SERVER_URL you set:
  - No URL set              → connects to mcp_server_basic.py
                               over stdio (spawns it as a subprocess)
  - MCP_SERVER_URL set      → connects over HTTP to a running
                               server (local or deployed on CF)
  - MCP_AUTH_TOKEN also set → sends it as a Bearer token, for
                               testing mcp_server_secured.py

Setup:
  pip install fastmcp
  python mcp_client_test.py                       # stdio, local
  MCP_SERVER_URL=http://localhost:8000/mcp \\
    python mcp_client_test.py                      # HTTP, local
  MCP_SERVER_URL=https://your-app.cfapps.../mcp \\
  MCP_AUTH_TOKEN=eyJhbGciOi... \\
    python mcp_client_test.py                       # HTTP + auth, CF
============================================================
"""

import asyncio
import os
from fastmcp import Client


async def main():
    server_url = os.environ.get("MCP_SERVER_URL")
    auth_token = os.environ.get("MCP_AUTH_TOKEN")

    if server_url:
        # Remote/HTTP mode — the Client auto-detects Streamable HTTP
        # from the URL and, if a token is provided, attaches it as
        # a standard "Authorization: Bearer <token>" header on every
        # request, which is exactly what JWTVerifier expects to see.
        print(f"Connecting over HTTP to {server_url} ...")
        client = Client(server_url, auth=auth_token)
    else:
        # Local/stdio mode — the Client spawns mcp_server_basic.py
        # itself as a subprocess and talks to it over stdin/stdout.
        # No network, no auth — matches how a local AI coding agent
        # would launch your server.
        print("Connecting over stdio to mcp_server_basic.py ...")
        client = Client("mcp_server_basic.py")

    async with client:
        # 1. Discovery — this is what populates a tool picker UI
        #    (Claude Desktop's tool list, Joule Studio's "Add MCP
        #    Server" dialog) after you point it at your server.
        tools = await client.list_tools()
        print(f"\nDiscovered {len(tools)} tool(s):")
        for t in tools:
            print(f"  - {t.name}: {t.description}")

        # 2. Invocation — call one tool with structured arguments,
        #    exactly like an LLM client would after deciding (from
        #    the tool's schema + description) that this tool answers
        #    the user's request.
        print("\nCalling convert_currency(100, 'USD', 'EUR') ...")
        result = await client.call_tool(
            "convert_currency",
            {"amount": 100, "from_currency": "USD", "to_currency": "EUR"},
        )
        print("Result:", result.data)

        print("\nCalling get_material_stock('MAT-1001', plant='1010') ...")
        result = await client.call_tool(
            "get_material_stock",
            {"material_id": "MAT-1001", "plant": "1010"},
        )
        print("Result:", result.data)


if __name__ == "__main__":
    asyncio.run(main())


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why test with a raw MCP client instead of just testing through
   Joule Studio directly?
A: Joule Studio adds several layers (BTP Destination, agent
   config, LLM tool-selection) between you and the server — if
   something's broken, a raw client isolates whether the FAULT is
   in your server (schema, auth, logic) or in the Joule-side wiring,
   which is much faster to debug than guessing through the UI.

Q: What's actually different between the stdio and HTTP code paths
   in this file, from the client's perspective?
A: Almost nothing at the call-site — list_tools() and call_tool()
   look identical either way. FastMCP's Client abstracts the
   transport entirely; only the constructor argument (a script path
   vs. a URL) changes, which is exactly the point of MCP standardizing
   the protocol layer above the transport.

Q: How does the client authenticate against mcp_server_secured.py?
A: It sends the token as a standard HTTP Authorization: Bearer
   header — the same mechanism any REST API client would use. The
   MCP protocol doesn't invent a new auth scheme; it rides on
   existing OAuth 2.1 Bearer token conventions.

Q: If list_tools() succeeds but call_tool() fails with a scope
   error, what does that tell you about the token?
A: The token passed authentication (valid signature, issuer,
   audience — otherwise list_tools() would have failed with a 401
   too) but failed authorization — it's missing the specific scope
   required_scopes enforces, which is a permissions problem, not an
   identity problem.
------------------------------------------------------------
"""
