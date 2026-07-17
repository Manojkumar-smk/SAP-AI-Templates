# CAP External API Integration — User Manual

How a CAP `srv.js` calls OUT to other systems: S/4HANA's Sales Order
API (OData, via imported metadata), a custom AI Python API on Cloud
Foundry, SAP Integration Suite (CPI), SAP Build Process Automation
(BPA), and n8n — all through the same `cds.connect.to()` +
BTP Destination pattern.

> **Verified, not just written:** the full request chain — OData
> action call → service handler → client file → `cds.connect.to()`
> → real HTTP call → mock server → response — was run end-to-end
> against a live `cds watch` instance during development (see
> `srv/integration-service.js`'s header for the exact command).
> Built with `@sap/cds` 10.0.3 / `@sap/cds-dk` 10.0.5.

---

## Folder Structure

```
capm_external_api_integration/
├── srv/
│   ├── external/
│   │   └── API_SALES_ORDER_SRV.cds    ← Trimmed external model (see file header re: `cds import`)
│   ├── s4_sales_order_client.js        ← OData consumption (cds.ql against a remote model)
│   ├── ai_python_api_client.js         ← REST via Destination (custom CF-hosted API)
│   ├── cpi_api_client.js               ← REST via Destination (SAP Integration Suite)
│   ├── bpa_api_client.js               ← REST via Destination (SAP Build Process Automation)
│   ├── n8n_api_client.js               ← REST, two styles: Destination OR direct + API key
│   ├── integration-service.cds         ← Unbound actions exposing all six as one API
│   └── integration-service.js          ← Wires actions to client files
├── package.json                        ← cds.requires for all five external services
├── .env.example
└── USER_MANUAL.md
```

---

## The One Pattern Behind Every Client File

Every external system in this folder — SAP or not — is consumed the
same way:

```js
const remote = await cds.connect.to('SERVICE_NAME');   // looked up in cds.requires
const result = await remote.send({ method, path, headers, data });
// or the shorthand: remote.get(path) / remote.post(path, data) / ...
```

What differs per system is entirely in `package.json`'s
`cds.requires.<SERVICE_NAME>` config — a base `credentials.url` for
local dev, and a `"[production]"` block that swaps to
`credentials.destination` (a BTP Destination Service entry name) when
deployed. **The client code never changes between environments.**

| Service | kind | Local dev | Production |
|---|---|---|---|
| `API_SALES_ORDER_SRV` | `odata` (+ imported `model`) | direct sandbox URL | `destination: S4HANA_SALES_ORDER` |
| `AI_PYTHON_API` | `rest` | `http://localhost:8000` | `destination: ai-python-api-destination` |
| `CPI_API` | `rest` | `http://localhost:9000` | `destination: cpi-destination` |
| `BPA_API` | `rest` | `http://localhost:9100` | `destination: bpa-destination` |
| `N8N_API` | `rest` | `http://localhost:5678` | `destination: n8n-destination` (or direct + API key — see `n8n_api_client.js`) |

`kind: "odata"` is the one exception that behaves differently — it
also needs a `model` (the imported CDS), which lets you query it with
`SELECT`/`INSERT` instead of raw `.send()` calls. See
`s4_sales_order_client.js` for why that matters.

---

## Setup (One-Time)

### 1. Install dependencies
```bash
npm install
```

### 2. Point local dev at something real (or a mock)
The `credentials.url` values in `package.json` default to
`localhost` ports matching nothing in particular — for real local
testing, either:
- Run simple mock servers on those ports (this template's own
  development used a 6-line Express mock — see the verified example
  in `ai_python_api_client.js`'s header), or
- Point the URLs at real dev/sandbox systems (S/4HANA's public API
  sandbox at `sandbox.api.sap.com` works without a destination for
  quick testing of `API_SALES_ORDER_SRV`).

### 3. Run it
```bash
npm run watch
curl -X POST http://localhost:4004/integration/analyzeSalesOrderText \
  -H "Content-Type: application/json" -d '{"text":"SAP BTP is great"}'
```

---

## Getting the REAL S/4HANA Sales Order Model

`srv/external/API_SALES_ORDER_SRV.cds` in this template is
**hand-trimmed for readability** — it is NOT what you should ship.
Get the real, complete model:

```bash
# 1. Download the $metadata document — from an on-prem system:
curl -u <user>:<pass> \
  https://<host>/sap/opu/odata/sap/API_SALES_ORDER_SRV/\$metadata \
  -o API_SALES_ORDER_SRV.edmx
# ...or from S/4HANA Cloud's API Business Hub:
# https://api.sap.com/api/API_SALES_ORDER_SRV → API Specification → Download

# 2. Import it
cds import ./API_SALES_ORDER_SRV.edmx --as cds

# 3. This generates srv/external/API_SALES_ORDER_SRV.csn (the FULL
#    model) and adds/updates the cds.requires entry in package.json
#    automatically. Replace the hand-written .cds file in this
#    template with the generated one.
```

---

## Setting Up the BTP Destinations

For each `[production]` `destination` name referenced in
`package.json`, create a matching entry in **BTP Cockpit →
Connectivity → Destinations**:

| Destination | Points at | Typical auth |
|---|---|---|
| `S4HANA_SALES_ORDER` | Your S/4HANA system's OData root | OAuth2SAMLBearer or Principal Propagation (on-prem via Cloud Connector), OAuth2ClientCredentials (Cloud) |
| `ai-python-api-destination` | Your CF app's route (see `../mcp_server_cloud_foundry/`) | NoAuthentication (private route) or OAuth2ClientCredentials via XSUAA |
| `cpi-destination` | Your Integration Suite tenant + iFlow path | OAuth2ClientCredentials against the tenant's own OAuth token endpoint |
| `bpa-destination` | Your Process Automation instance's API endpoint (Cockpit → instance → API Endpoint) | OAuth2ClientCredentials |
| `n8n-destination` (optional) | Your n8n instance's base URL | Whatever your n8n webhook trigger node expects (often a static header — see `n8n_api_client.js`) |

Test each with **Check Connection** in Cockpit before wiring up the
CAP app — a destination that fails there will fail identically (but
with a less obvious error) when called via `cds.connect.to()`.

---

## Common Errors

| Error | Fix |
|-------|-----|
| `Error during request to remote service: fetch failed ... ECONNREFUSED` | Nothing is listening at `credentials.url` — start your mock/dev server, or check the port matches `package.json` |
| `cds import` fails with an unresolvable reference | Some S/4 metadata documents reference external vocabularies your `cds-dk` version doesn't ship — check the SAP Note for your specific API, or use `--as cds --resolve-external-refs` if available in your `cds-dk` version |
| Actions in `integration-service.cds` return a JSON-STRING instead of a structured object | Intentional simplification — see the file's header comment; a production version would declare typed `type`/`aspect` structures instead of `String` |
| Real S/4 `INSERT` from `s4_sales_order_client.js` fails with a business-rule error from S/4 itself | That's S/4's own validation (e.g. invalid material, sales org not configured) surfacing through the OData error response — inspect the error's `innererror` for the SAP-side message |
| BPA call succeeds but nothing seems to happen | Confirm `definitionId` matches an actually-DEPLOYED workflow definition in your BPA instance — starting an instance of a definition that doesn't exist/isn't deployed fails with a 404, not silently |

---

## How This Relates to the Other Templates

`../capm_fiori_hana_sample/` is the "clean" CAPM + Fiori + HANA
reference — no external calls. This template is its natural
complement: the same kind of CAP service, but focused entirely on
OUTBOUND integration. A real project would likely combine both —
e.g. that sample's `sales-service.js` `confirm` handler calling this
template's `startApprovalWorkflow` action (see
`integration-service.js`'s interview points for exactly how).
`../mcp_server_cloud_foundry/` and `../gen_ai_hub_tool_calling/` are
what you'd deploy to BE the "AI Python API" this template's
`ai_python_api_client.js` calls INTO.
