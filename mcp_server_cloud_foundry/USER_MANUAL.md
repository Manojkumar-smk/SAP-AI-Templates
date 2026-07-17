# Python MCP Server on Cloud Foundry — User Manual

Mini templates for building a Python **MCP (Model Context Protocol)**
server with FastMCP, deploying it to **SAP BTP Cloud Foundry**, and
wiring it up as a tool provider for **Joule Studio** agents or any
other MCP-compatible AI coding assistant (Cline, Claude Code, etc.).

> **Library note:** built on `fastmcp` (the standalone, actively
> maintained project — FastMCP 1.0 was absorbed into the official MCP
> Python SDK). API surface moves fast; if an import fails, check
> [gofastmcp.com](https://gofastmcp.com) for your installed version.

---

## Folder Structure

```
mcp_server_cloud_foundry/
├── mcp_tools_common.py     ← Plain tool functions (framework-agnostic)
├── mcp_server_basic.py     ← MCP fundamentals — stdio transport, local only
├── mcp_server_http.py      ← Same tools over HTTP, Cloud Foundry-ready, NO auth
├── mcp_auth_jwt.py         ← XSUAA / IAS JWT verifier builders
├── mcp_server_secured.py   ← Production entrypoint: HTTP + JWT auth (what you cf push)
├── mcp_client_test.py      ← Test client — list & call tools (stdio or HTTP, with/without auth)
├── manifest.yml            ← Cloud Foundry deployment config
├── requirements.txt        ← pip dependencies
├── .env.example            ← Template for your .env file
└── USER_MANUAL.md          ← This file
```

---

## How the Pieces Fit Together

```
                    mcp_tools_common.py
              (plain functions — no MCP, no auth)
                    │                    │
                    ▼                    ▼
        mcp_server_basic.py      mcp_server_secured.py
        (stdio, unsecured,       (HTTP + XSUAA/IAS auth via
         teaching file)           mcp_auth_jwt.py — deployable)
                    │                    │
                    ▼                    ▼
        mcp_server_http.py        manifest.yml → cf push
        (same tools, HTTP,               │
         no auth — LAB ONLY)             ▼
                    │              running on Cloud Foundry
                    ▼                    │
            mcp_client_test.py ──────────┘
       (connects to ANY of the above to verify it works)
```

Read `mcp_server_basic.py` first to understand MCP itself with zero
deployment noise. Then `mcp_server_http.py` to see the CF-specific
adaptations. Then `mcp_auth_jwt.py` + `mcp_server_secured.py` for the
production-shaped version you'd actually ship.

---

## Quick Decision Guide

| I want to... | Use this file |
|------------|--------------|
| Understand what MCP tools/schemas actually are | `mcp_server_basic.py` |
| See the Cloud Foundry-specific HTTP wiring (PORT, health check) | `mcp_server_http.py` |
| Understand XSUAA vs IAS JWT validation for MCP | `mcp_auth_jwt.py` |
| Get the file to actually deploy for real data | `mcp_server_secured.py` + `manifest.yml` |
| Sanity-check a server without Joule Studio | `mcp_client_test.py` |
| See the shared business logic tools call | `mcp_tools_common.py` |

---

## Setup (One-Time)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Try it locally over stdio (no BTP needed yet)
```bash
python mcp_client_test.py
```
This spawns `mcp_server_basic.py` as a subprocess, lists its tools,
and calls two of them. If this works, MCP itself is working.

### 3. Try it locally over HTTP
```bash
# terminal 1
python mcp_server_http.py
# terminal 2
MCP_SERVER_URL=http://localhost:8000/mcp python mcp_client_test.py
```

### 4. Set up your `.env` for auth testing
```bash
cp .env.example .env
```
Fill in `XSUAA_URL` + `XSUAA_XSAPPNAME` from **BTP Cockpit → your
XSUAA service instance → Service Keys** (or the `IAS_*` pair if using
Identity Authentication Service instead).

---

## Deploying to Cloud Foundry

```bash
# One-time setup
cf login -a <api-endpoint>
cf target -o <your-org> -s <your-space>

# Deploy (reads manifest.yml automatically from this folder)
cf push

# Watch logs while it starts
cf logs sap-demo-mcp-server --recent
```

Your server is now reachable at
`https://sap-demo-mcp-server.<your-domain>/mcp`. Confirm it's alive:

```bash
curl https://sap-demo-mcp-server.<your-domain>/health
```

To test the deployed server end-to-end (auth included):
```bash
MCP_SERVER_URL=https://sap-demo-mcp-server.<your-domain>/mcp \
MCP_AUTH_TOKEN=<a real token from your XSUAA/IAS tenant> \
python mcp_client_test.py
```

---

## Connecting to Joule Studio

1. **Create a BTP Destination** (BTP Cockpit → your subaccount →
   Connectivity → Destinations → New Destination):
   - URL: your server's root, e.g. `https://sap-demo-mcp-server.<your-domain>`
     — **do not append `/mcp`**; Joule Studio adds the MCP path itself
     when you configure the server inside the agent.
   - Authentication: `NoAuthentication` for a quick lab test, or
     `OAuth2ClientCredentials` pointing at your XSUAA instance for a
     server secured with `mcp_server_secured.py`.
   - Add the additional property Joule requires to recognize this as
     an MCP-serving destination (see the Joule Studio help page for
     the current property name/value — this has changed between
     releases, so verify against your tenant's docs).
   - Save, then click **Check Connection** to confirm BTP can reach
     your `/health`-adjacent route.

2. **Add the MCP server to your agent** (inside Joule Studio's agent
   builder): click **Add MCP Server**, select the destination you
   just created, and Joule Studio will list every tool your server
   exposes — the same list `mcp_client_test.py`'s `list_tools()` call
   shows you locally.

3. **Write agent instructions** describing when to use each tool —
   this is what actually drives the LLM's tool-selection behavior at
   runtime, not anything in the MCP server itself.

---

## Common Errors

| Error | Fix |
|-------|-----|
| `EnvironmentError: No identity service configured` | Set `XSUAA_URL`+`XSUAA_XSAPPNAME` or `IAS_URL`+`IAS_AUDIENCE` in `.env` before running `mcp_server_secured.py` |
| `401 Unauthorized` calling a deployed server | Token missing, expired, or wrong audience — confirm the token was issued for the exact `XSUAA_XSAPPNAME`/`IAS_AUDIENCE` this server checks |
| Tool call succeeds via `list_tools()` but fails with a scope error | Token is authenticated but lacks the scope in `MCP_REQUIRED_SCOPE` — an authorization problem, not an identity one |
| CF app crashes immediately after `cf push` | Check `cf logs sap-demo-mcp-server --recent` — usually a missing `.env`-equivalent var (CF doesn't read `.env`; set real env vars or bind a service) |
| Joule Studio "Check Connection" fails on the destination | Confirm you did **not** append `/mcp` to the destination URL, and that `/health` (unauthenticated) responds with `curl` from outside the CF space |
| `ImportError` on a `fastmcp.server.auth.*` submodule | `fastmcp`'s auth API has moved between minor versions — check `pip show fastmcp` against [gofastmcp.com](https://gofastmcp.com) |

---

## How This Relates to the Other Mini Templates

`sap_ai_core_orchestration/` and the `hana_*` folders show the LLM
side of an AI application — how to call a model, run RAG, mask PII.
This folder shows the **tool-exposure** side: how an LLM-driven agent
(whether that's Joule Studio, or a Python orchestration pipeline from
those other folders acting as its own MCP *client*) discovers and
calls capabilities you've written, over a standardized protocol,
deployed as a normal Cloud Foundry app.
