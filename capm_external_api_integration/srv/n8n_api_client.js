/*
============================================================
CLIENT — n8n Webhook / API (non-SAP automation tool)
============================================================
Use this when: you want a CAP business event to trigger an n8n
workflow (n8n is typically self-hosted or on a third-party cloud,
NOT an SAP BTP service) — e.g. posting a Slack message, updating
a spreadsheet, or fanning out to other non-SAP tools n8n already
has nodes for.

Why this file looks almost identical to the others, despite n8n
being a non-SAP tool:
  BTP Destinations aren't limited to SAP systems — you can create a
  destination for ANY HTTPS URL, including a self-hosted n8n
  instance, and get the same benefit (credentials centralized in
  Destination service, not hardcoded/env-var'd per app). This file
  shows BOTH options since n8n setups vary more than SAP-to-SAP
  integrations do:
    Option A: route through a BTP destination (recommended if you
              want n8n credentials managed the same way as your
              SAP destinations).
    Option B: call it directly with an API key header, common for
              simpler/local setups where standing up a BTP
              destination for one external webhook is overkill.

n8n auth: most n8n webhook nodes are secured with either a static
header (e.g. "X-N8N-API-KEY") or Basic Auth configured on the
webhook trigger node itself — check your specific workflow's
trigger node configuration for the exact scheme it expects.

Setup (package.json cds.requires.N8N_API) — Option A shown:
  "credentials": { "url": "http://localhost:5678", "path": "/webhook" }
  (n8n's default local port is 5678). For Option B, skip the
  cds.requires entry entirely and see callWebhookDirect() below.
============================================================
*/

const cds = require('@sap/cds');

/**
 * Option A: call an n8n webhook via a configured CAP remote service
 * (destination-based in production, direct URL in dev) — preferred
 * when you want n8n's credentials centrally managed like any other
 * integration in this folder.
 */
async function triggerWorkflow(webhookPath, payload) {
  const n8n = await cds.connect.to('N8N_API');

  return n8n.send({
    method: 'POST',
    path: webhookPath,   // e.g. '/sales-order-created'
    headers: { 'Content-Type': 'application/json' },
    data: payload,
  });
}

/**
 * Option B: call an n8n webhook directly with a static API key,
 * bypassing cds.requires/Destination entirely — simplest option for
 * a quick integration, at the cost of the URL/key living in this
 * app's own environment variables instead of a centrally managed
 * BTP destination.
 */
async function callWebhookDirect(webhookUrl, payload) {
  const apiKey = process.env.N8N_API_KEY;
  const response = await fetch(webhookUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-N8N-API-KEY': apiKey,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`n8n webhook call failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

module.exports = { triggerWorkflow, callWebhookDirect };

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why offer TWO integration styles here when every other file in
   this folder shows only one (destination-based)?
A: n8n isn't part of the SAP BTP ecosystem, so unlike CPI/BPA/S4 —
   where a BTP destination is basically always the right call — a
   self-hosted or third-party-hosted n8n instance is a legitimate
   case where a simpler direct-call approach (Option B) may be the
   pragmatic choice, especially for a single one-off webhook.

Q: What's the actual downside of Option B (direct fetch + env var
   API key) compared to Option A (destination)?
A: The key lives in this app's own config/environment instead of
   the centrally managed Destination service — meaning key rotation,
   auditing, and access control for that credential are now this
   app's responsibility rather than a platform-level concern shared
   across every app that might need to call the same n8n instance.

Q: Why does callWebhookDirect() use the global `fetch` instead of
   cds.connect.to()?
A: cds.connect.to() requires the target to be pre-declared in
   cds.requires — Option B is explicitly for the case where you
   DON'T want that ceremony for a single ad-hoc webhook call; plain
   `fetch` (built into Node.js since v18, no extra dependency) is
   the more honest tool for that job.

Q: How would you decide whether a CAP action calling n8n should
   await the workflow's result or fire-and-forget?
A: Depends on whether the CAP request NEEDS the n8n workflow's
   output to respond correctly to its own caller. A notification
   ("tell Slack an order shipped") is fire-and-forget; a workflow
   that enriches data CAP is about to return to its own caller must
   be awaited.
------------------------------------------------------------
*/
