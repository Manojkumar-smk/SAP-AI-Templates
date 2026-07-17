/*
============================================================
CLIENT — SAP Integration Suite / Cloud Integration (CPI) iFlow
============================================================
Use this when: an iFlow deployed on SAP Integration Suite exposes
a REST endpoint (via its HTTPS Sender adapter) that your CAP
service needs to call — e.g. an iFlow that does data transformation,
fans out to multiple legacy systems, or applies integration-specific
retry/monitoring that you don't want to reimplement in CAP.

Same mechanical pattern as ai_python_api_client.js — CPI is "just"
another REST endpoint from CAP's perspective, reached via a
Destination. What's CPI-specific is how the DESTINATION itself gets
configured, not this client code:

  - The iFlow's endpoint URL is its tenant runtime host + the path
    you set on the iFlow's HTTPS Sender adapter, e.g.
    https://<tenant>.it-cpiXXX.cfapps.<region>.hana.ondemand.com/http/<your-path>
  - Auth is almost always OAuth2ClientCredentials against the
    tenant's own OAuth token endpoint (Monitor → Manage Security
    Material in Integration Suite to find/create the OAuth client),
    configured on the BTP destination, not in this file.

Setup (package.json cds.requires.CPI_API):
  "credentials": { "url": "http://localhost:9000", "path": "/http/demo-iflow" }
  for local dev (point this at a mock or a real dev-tenant iFlow),
  with "[production]" overriding to
  { "destination": "cpi-destination", "path": "/http/demo-iflow" }.
============================================================
*/

const cds = require('@sap/cds');

/**
 * Posts a payload to a CPI iFlow endpoint and returns its response.
 * Structurally identical to calling any other REST API via a
 * destination — the integration complexity lives in the iFlow
 * itself (routing, transformation, retries), not in this call site.
 */
async function triggerIntegrationFlow(payload) {
  const cpi = await cds.connect.to('CPI_API');

  return cpi.send({
    method: 'POST',
    path: '/',                 // relative to credentials.path configured above
    headers: { 'Content-Type': 'application/json' },
    data: payload,
  });
}

module.exports = { triggerIntegrationFlow };

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What's actually different between calling CPI, calling BPA, and
   calling a plain custom REST API, from CAP's code perspective?
A: Nothing at the cds.connect.to()/.send() level — that's the whole
   point of the Destination abstraction. What differs is entirely in
   configuration: which BTP destination name is used, what auth type
   it specifies, and what path/payload shape the target system
   expects. The CAP-side integration code is deliberately generic.

Q: Why route through CPI at all instead of calling the ultimate
   target system (say, a legacy SOAP service) directly from CAP?
A: CPI centralizes integration concerns — protocol translation
   (SOAP↔REST), message transformation, retry/error-handling
   policies, and monitoring — in one place that integration teams
   own and can change WITHOUT touching or redeploying the CAP app.
   It also lets CAP stay REST-only even when upstream systems aren't.

Q: If the iFlow itself is slow (e.g. it's doing a batch transform),
   how should this client behave differently from a fast API call?
A: Consider not awaiting synchronously in the CAP request handler —
   either call an async iFlow pattern (fire-and-forget + a
   callback/webhook back into CAP) or set a longer timeout
   explicitly on the destination/service config, since the default
   HTTP client timeout may be too short for a genuinely long-running
   integration flow.
------------------------------------------------------------
*/
