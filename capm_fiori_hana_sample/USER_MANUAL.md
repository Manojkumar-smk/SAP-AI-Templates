# CAPM + Fiori Elements (Annotations) + SAP HANA Cloud — User Manual

A complete, runnable sample: **db layer** (CDS domain model) → **srv
layer** (OData service + custom actions) → **Fiori elements frontend**
built entirely from annotations (no hand-written UI5 controller code)
→ deployable to Cloud Foundry with **SAP HANA Cloud** as the database.

> **Verified, not just written:** every schema/service file here was
> compiled with `cds compile` and then actually run against a live
> `cds watch` instance with real HTTP requests during development —
> including a real bug (see `srv/sales-service.js`'s header) that was
> caught and fixed by testing, not just written and assumed correct.
> Built with `@sap/cds` 10.0.3 / `@sap/cds-dk` 10.0.5.

---

## Folder Structure

```
capm_fiori_hana_sample/
├── db/
│   ├── schema.cds                    ← Domain model (Customers, Products, SalesOrders, Items)
│   └── data/                         ← CSV seed data for local dev
├── srv/
│   ├── sales-service.cds             ← Service definition (projections + actions)
│   └── sales-service.js              ← Custom handlers (computed totals, confirm/cancel)
├── app/
│   └── orders/
│       ├── fiori-service.cds         ← THE Fiori annotations (this is "the frontend")
│       └── webapp/
│           ├── manifest.json         ← Fiori elements List Report + Object Page config
│           ├── index.html            ← Local sandbox test page
│           └── i18n/i18n.properties
├── package.json                      ← cds config: sqlite (dev) / HANA Cloud (prod) profiles
├── mta.yaml                          ← Cloud Foundry deployment descriptor
├── xs-security.json                  ← XSUAA roles/scopes
└── USER_MANUAL.md                    ← This file
```

---

## How the Layers Fit Together

```
db/schema.cds  (domain model, protocol-agnostic)
      │
      ▼
srv/sales-service.cds  (WHAT is exposed: projections + actions)
      │                          │
      ▼                          ▼
srv/sales-service.js      app/orders/fiori-service.cds
(business logic:          (HOW it looks: List Report columns,
 computed totals,          Object Page facets, action buttons —
 confirm/cancel guards)    zero UI5 controller code)
      │                          │
      └──────────┬───────────────┘
                  ▼
      app/orders/webapp/manifest.json
      (points sap.fe.templates at the annotated service)
```

This is CAP's recommended separation of concerns: `db/` never
mentions OData or Fiori; `srv/*.cds` never mentions UI rendering;
`app/*/fiori-service.cds` never contains business logic. Each layer
can be understood, tested, and changed independently.

---

## Setup (One-Time)

### 1. Install dependencies
```bash
npm install
```

### 2. Deploy the local SQLite database
```bash
npx cds deploy --to sqlite
```
**Verified gotcha:** this step is required before the FIRST
`cds watch` when using a persistent `db.sqlite` file (as this
project's `package.json` does). Unlike an in-memory `:memory:`
database, a file-based one is NOT auto-seeded by `cds watch` — you
must deploy it explicitly once. Delete `db.sqlite` and re-run this
command any time you change `db/schema.cds` or the seed CSVs.

### 3. Run it
```bash
npm run watch
```
Visit `http://localhost:4004` for the CAP index page (with a Fiori
preview link — real-time annotation preview without building the
full UI5 app), or `http://localhost:4004/sales/SalesOrders` for the
raw OData response.

---

## Trying It Out (curl) — exact commands verified during development

**Verified gotcha:** `sales-service.cds` has `@(requires:
'authenticated-user')`. In local dev this uses CAP's `mocked` auth
strategy, which is NOT automatically satisfied by an anonymous
request — you need Basic auth with one of CAP's built-in mock users
(any password works; only the username is checked):

```bash
# Read the seeded demo order
curl -u alice: http://localhost:4004/sales/SalesOrders

# Add an item — netAmount is computed server-side from Products.price × quantity
curl -u alice: -X POST http://localhost:4004/sales/SalesOrderItems \
  -H "Content-Type: application/json" \
  -d '{"parent_ID":"o1","product_ID":"p1","quantity":3}'
# → netAmount: "37.50"   (Products[p1].price 12.50 × 3)

# Check the order — totalAmount auto-rolled up from its items
curl -u alice: http://localhost:4004/sales/SalesOrders\(ID=o1\)
# → totalAmount: "37.50"

# Confirm the order (custom action)
curl -u alice: -X POST "http://localhost:4004/sales/SalesOrders(ID=o1)/SalesService.confirm" \
  -H "Content-Type: application/json" -d '{}'
# → status: "CONFIRMED"

# Confirm it AGAIN — the state-transition guard rejects this
curl -u alice: -X POST "http://localhost:4004/sales/SalesOrders(ID=o1)/SalesService.confirm" \
  -H "Content-Type: application/json" -d '{}'
# → HTTP 400: "Order SO-0001 is 'CONFIRMED' and cannot be confirmed."
```

---

## The Fiori Annotations, Explained

`app/orders/fiori-service.cds` is the entire "frontend" for this
sample — no UI5 XML views, no controllers. Key terms used:

| Annotation | What it renders |
|---|---|
| `UI.SelectionFields` | Filter bar fields on the List Report |
| `UI.LineItem` | Table columns on the List Report (and `DataFieldForAction` entries become row-level buttons) |
| `UI.HeaderInfo` | Object Page title/subtitle |
| `UI.Identification` | Object Page header toolbar buttons |
| `UI.Facets` + `UI.FieldGroup` | Object Page sections — a `ReferenceFacet` pointing at `items/@UI.LineItem` renders the item composition as an editable embedded table |
| `@cds.odata.valuelist` | Convenience annotation — every association pointing at this entity automatically gets a value-help dropdown |

Change any of these, restart `cds watch`, and the Fiori preview at
the index page reflects it immediately — that live-feedback loop is
the actual point of an annotation-driven frontend.

### Want draft editing (SAP Fiori's "save as you go" UX)?
Add `@odata.draft.enabled` above `entity SalesOrders as projection
on db.SalesOrders actions {...}` in `sales-service.cds`.
**Verified gotcha:** once draft is enabled, you can no longer `POST`
directly to `/sales/SalesOrderItems` — CAP returns
`DRAFT_MODIFICATION_ONLY_VIA_ROOT`. Composition children must be
modified through the draft choreography instead (create a draft of
the ROOT SalesOrder, `PATCH` items within that draft, then
`POST .../draftActivate`) — this is standard, correct Fiori draft
behavior, not a bug, but it changes how you'd test with curl. Left
OFF in this sample to keep the curl examples above simple; see
[capire's draft guide](https://cap.cloud.sap/docs/guides/uis/fiori#draft-support)
for the full choreography if you enable it.

---

## Deploying to Cloud Foundry (with SAP HANA Cloud)

```bash
# One-time: install the MTA build tool
npm install -g mbt

# Build the deployable archive
mbt build

# Deploy (requires cf CLI logged in and targeted to your org/space,
# plus a HANA Cloud instance available in that space)
cf deploy mta_archives/capm-fiori-hana-sample_1.0.0.mtar
```

What `mta.yaml` wires together:
- **`capm-fiori-hana-sample-db`** — an HDI container on your HANA
  Cloud instance; `db/schema.cds` compiles to `.hdbtable`/`.hdbview`
  artifacts deployed here by the `-db-deployer` module.
- **`capm-fiori-hana-sample-srv`** — the CAP service, switched to
  `kind: hana` for its db connection and `kind: xsuaa` for auth via
  the `[production]` profile blocks in `package.json`.
- **`orders` + `-app-content` + `-html5-repo-host`** — the Fiori app,
  built and uploaded to the HTML5 Application Repository so it can
  be added to a Fiori Launchpad site.
- **`-destination` + `-connectivity`** — included so this service can
  make outbound calls (see the sibling
  `../capm_external_api_integration/` template for exactly that).

---

## Common Errors

| Error | Fix |
|-------|-----|
| `no such table: SalesService_SalesOrders` on first `cds watch` | Run `npx cds deploy --to sqlite` first — file-based sqlite isn't auto-seeded like `:memory:` is |
| `Unauthorized` on every curl request | `@(requires: 'authenticated-user')` needs Basic auth even in mocked mode — add `-u alice:` |
| `DRAFT_MODIFICATION_ONLY_VIA_ROOT` posting to SalesOrderItems | Expected once `@odata.draft.enabled` is added — see the draft section above |
| Item POST succeeds but `netAmount` is `null` | Check whether your client sends `product_ID` (flattened FK) vs `{product:{ID:...}}` (nested) — `sales-service.js`'s handler checks both, but a hand-rolled variant that only checks one WILL silently produce null, exactly as caught during this template's own development |
| `cds compile` errors on an `enum` + `default` combo | `enum {...}` must come BEFORE `default '...'` in the element declaration, not after |
| MTA build fails with a missing HDI/XSUAA plan | Your CF space needs a HANA Cloud instance and entitlements for `xsuaa`, `destination`, `connectivity`, and `html5-apps-repo` services — check Cockpit → Entitlements |

---

## How This Relates to the Other Templates

`../sample_project_capm_s4hana_ai/` is a larger, AI-integrated
version of a similar idea (Python AI Core service + CAP + S/4HANA
RAP + HANA). This template is the CLEAN foundational version —
pure CAPM + Fiori + HANA Cloud, no AI — meant as the reference to
come back to for the CDS/Fiori mechanics themselves. For consuming
EXTERNAL APIs from a CAP service (S/4HANA Sales Order API, a custom
AI API, CPI, BPA, n8n), see
`../capm_external_api_integration/`.
