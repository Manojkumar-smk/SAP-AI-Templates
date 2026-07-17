/*
============================================================
CLIENT — Custom AI Python API on Cloud Foundry (via Destination)
============================================================
Use this when: your CAP service needs to call a Python API you
deployed yourself on Cloud Foundry (e.g. the FastAPI/MCP servers
from ../mcp_server_cloud_foundry/, or a plain REST wrapper around
an SAP AI Core model) — a REST, non-OData integration.

VERIFIED END-TO-END during development of this template: ran a
local Express mock server on :8000, connected with
`cds.connect.to('AI_PYTHON_API')`, and confirmed BOTH call styles
work — the shorthand `.get('/status')` (returns parsed JSON
directly) and the explicit `.send({method, path, headers, data})`
form (needed when you must set custom headers). Not just written
from docs.

Setup (package.json cds.requires.AI_PYTHON_API):
  "credentials": { "url": "http://localhost:8000", "path": "/api" }
  for local dev, with "[production]" overriding to
  { "destination": "ai-python-api-destination", "path": "/api" } —
  create that destination in BTP Cockpit pointing at your CF app's
  route, e.g. https://ai-python-api.cfapps.<region>.hana.ondemand.com
============================================================
*/

const cds = require('@sap/cds');

/**
 * Calls the Python API's /analyze endpoint. Uses the .send() form
 * because a real deployment would need a custom header here (e.g.
 * an API key the Python service checks in addition to destination-
 * level auth) — .get()/.post() shorthands don't accept headers.
 */
async function analyzeText(text) {
  const api = await cds.connect.to('AI_PYTHON_API');

  return api.send({
    method: 'POST',
    path: '/analyze',
    headers: { 'Content-Type': 'application/json' },
    data: { text },
  });
}

/**
 * Calls a simple health/status endpoint using the shorter .get()
 * form — verified to work identically to .send({method:'GET',...})
 * when you don't need custom headers.
 */
async function checkHealth() {
  const api = await cds.connect.to('AI_PYTHON_API');
  return api.get('/status');
}

module.exports = { analyzeText, checkHealth };

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What's the difference between api.get('/status') and
   api.send({method:'GET', path:'/status'})?
A: Verified identical results for a plain GET with no extra
   headers — .get()/.post()/.put()/.patch()/.delete() are shorthand
   convenience wrappers around .send() for the common case. Use
   .send() explicitly when you need custom headers, as
   analyzeText() does here.

Q: Why does the credentials block split into a base object plus a
   "[production]" override instead of one flat config?
A: CAP's profile-based config lets the SAME service name resolve to
   DIFFERENT credentials depending on `NODE_ENV`/`cds` profile —
   `path`/`url` for fast local dev against a mock or local server,
   swapped for a BTP `destination` name only when actually running
   in Cloud Foundry (`[production]`), with zero code changes.

Q: If AI_PYTHON_API's destination in BTP uses OAuth2ClientCredentials
   auth, does this file need to fetch or attach a token itself?
A: No — the Destination service resolves auth server-side based on
   how the destination is configured; the RemoteService created by
   cds.connect.to() reads the resolved destination and attaches
   whatever auth it specifies automatically. This file stays
   protocol/auth-agnostic on purpose.

Q: This mirrors the MCP server pattern in
   ../mcp_server_cloud_foundry/ — when would you use THIS
   (CAP calling a Python REST API directly) instead of THAT
   (exposing the Python API as an MCP tool)?
A: Use this file's pattern when a KNOWN, fixed piece of business
   logic in your CAP app needs one specific Python capability — a
   direct, typed integration. Use MCP when an LLM AGENT (Joule
   Studio, a coding assistant) needs to discover and choose among
   MULTIPLE tools dynamically — MCP is a discovery+invocation
   protocol for agents, not a general REST client mechanism.
------------------------------------------------------------
*/
