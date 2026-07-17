# CAPM + Freestyle SAPUI5 (Task Board) — User Manual

A CAP (Node.js) backend with a **hand-coded, freestyle SAPUI5**
frontend — no Fiori elements, no annotations driving the UI. Every
view, controller, and binding is written explicitly, using
`cds-plugin-ui5` to serve both the OData service and the UI5 app
from one `cds watch` process.

> **Verified, not just written:** installed for real
> (`@sap/cds` 10.0.3, `@sap/cds-dk` 10.0.5, `cds-plugin-ui5` 0.17.4,
> `@cap-js/sqlite` 3.0.2) and run end-to-end via `cds watch` —
> `GET /odata/v4/task/Tasks`, the bound `complete` action, the
> unbound `resetDemoData` action, and both CREATE validations (past
> due date, invalid status enum) were all exercised live via curl.
> The UI5 app's `manifest.json` passed the SAPUI5 MCP server's
> `run_manifest_validation` (Manifest Version 2) and its four files
> passed `run_ui5_linter` with **zero** findings — two real issues
> the linter caught and this template fixed: a deprecated
> `synchronizationMode` model parameter, and two XML bindings
> reaching `sap.ui.model.odata.type.Date` as a bare global instead
> of through `core:require` (see `TaskList.view.xml` /
> `TaskDetail.view.xml`).

---

## Folder Structure

```
capm_ui5_freestyle_sample/
├── db/
│   ├── schema.cds                  ← Tasks entity (status/priority enums)
│   └── data/*.csv                  ← sample rows
├── srv/
│   ├── task-service.cds            ← CRUD + complete (bound) + resetDemoData (unbound)
│   └── task-service.js             ← action handlers + due-date guardrail
├── app/taskboard/webapp/
│   ├── Component.js                ← app entry point
│   ├── manifest.json               ← models, routing — Manifest Version 2
│   ├── index.html                  ← declarative ComponentSupport bootstrap
│   ├── controller/
│   │   ├── BaseController.js       ← router/model/i18n helpers
│   │   ├── App.controller.js       ← app-shell busy-state model
│   │   ├── TaskList.controller.js  ← search, create, actions
│   │   └── TaskDetail.controller.js← manual save/cancel, complete, delete
│   ├── view/
│   │   ├── App.view.xml            ← single sap.m.App shell (routing target)
│   │   ├── TaskList.view.xml       ← hand-built "List Report"
│   │   └── TaskDetail.view.xml     ← hand-built "Object Page" (Form + ColumnLayout)
│   ├── fragment/
│   │   └── CreateTaskDialog.fragment.xml
│   ├── model/
│   │   ├── models.js               ← device model
│   │   └── formatter.js            ← status/priority → ValueState
│   ├── css/style.css
│   └── i18n/i18n.properties
├── package.json                    ← @sap/cds, cds-plugin-ui5, @sap/cds-dk
└── USER_MANUAL.md
```

---

## How the Pieces Fit Together

```
cds watch  (ONE process, ONE port, per SAPUI5 MCP guidelines)
   │
   ├── cds-plugin-ui5 → serves app/taskboard/webapp/* at /taskboard/webapp/
   │                     (index.html, manifest.json, views, controllers, i18n — as static/live-reload files)
   │
   └── @sap/cds → serves TaskService at /odata/v4/task/
                     (Tasks CRUD, complete action, resetDemoData action)

Browser loads /taskboard/webapp/index.html
   → ComponentSupport boots Component.js
   → manifest.json's "" model = ODataModel v4 pointed at /odata/v4/task/
   → router shows TaskList.view.xml (route "") or TaskDetail.view.xml (route "task/{taskId}")
   → controllers bind/filter/create/delete directly against that ODataModel — no annotations involved anywhere
```

---

## Freestyle UI5 vs. Fiori Elements — Same Backend Style, Opposite Frontend Philosophy

This template is the deliberate counterpart to
**`../capm_fiori_hana_sample/`** in this project. Same kind of CAP
service, same OData v4 protocol — completely different frontend
approach:

| | This template (freestyle) | `../capm_fiori_hana_sample/` (Fiori elements) |
|---|---|---|
| Views | Hand-written XML (`TaskList.view.xml`, ...) | Auto-rendered from annotations, no view XML |
| List/columns | `sap.m.Table` wired by hand in the view | `@UI.LineItem` annotations in `app/orders/fiori-service.cds` |
| Create/Edit | Custom dialog + explicit `submitBatch()`/`resetChanges()` | Built-in Fiori elements draft handling |
| Actions | Manual `oModel.bindContext(...).execute()` | `@UI.lineItem: [{type: #FOR_ACTION, ...}]` annotation |
| Code volume | High — you write navigation, search, save/cancel, formatters | Low — framework generates the UI from the service + annotations |
| When to choose | Highly custom UX, non-standard interactions, dashboards | Standard List Report / Object Page CRUD apps, fastest to build |

Both are legitimate, production-used approaches — knowing when to
reach for which (and being able to explain the trade-off) is a
common interview topic in its own right.

---

## Setup

```bash
cd capm_ui5_freestyle_sample
npm install
npx cds deploy --to sqlite   # seeds db.sqlite from db/data/*.csv — REQUIRED once
                              # (file-based sqlite is NOT auto-seeded by cds watch,
                              # see Common Errors below)
cds watch
```

Open **http://localhost:4004/taskboard/webapp/index.html** (the CAP
launch page at http://localhost:4004 also lists this app and the
service, per SAPUI5 MCP guidelines).

---

## Common Errors

| Error | Fix |
|-------|-----|
| `Tasks` request returns `no such table: TaskService_Tasks` | You skipped `cds deploy --to sqlite` — file-based sqlite (`db.sqlite`, as configured in `package.json`) isn't auto-seeded the way in-memory sqlite is |
| UI5 app 404s at `/taskboard/webapp/index.html` | `cds-plugin-ui5` isn't installed/detected — confirm it's in `package.json`'s `devDependencies` and that you ran `cds watch` from the project ROOT, not from inside `app/taskboard/` |
| Browser console: `ui5-middleware-simpleproxy` / CORS errors | You're running a separate `ui5 serve` instead of `cds watch` — per SAPUI5 MCP guidelines, freestyle UI5 apps in a CAP project must be served BY `cds watch`, not a standalone UI5 dev server, or the OData calls won't share an origin with the service |
| `manifest.json` fails `run_manifest_validation` after you edit it | Check `_version` first — Manifest Version 2 (`"_version": "2.0.0"`) removed `rootView.async`/`routing.config.async`, renamed target `viewName` → `name`, added required `id` per target, and requires `flexEnabled: true` (not `false`) — all things this template already applies, but easy to regress while extending it |
| `run_ui5_linter` flags `no-globals` on a `type: 'sap.ui.model.odata.type.Date'` binding | Wrap it with `core:require="{ ODataDate: 'sap/ui/model/odata/type/Date' }"` and reference `type: 'ODataDate'` instead of the dotted global string — see `TaskList.view.xml`/`TaskDetail.view.xml` for the working pattern |
| Save button does nothing / changes silently vanish | Confirm the bound Input/Select/DatePicker in `TaskDetail.view.xml` are all within the element bound via `$$updateGroupId: "taskDetailGroup"`, and that `manifest.json`'s `groupProperties` still marks that group `"submit": "API"` — without both halves, edits submit immediately via `$auto` instead of waiting for Save |

---

## How This Relates to the Other Templates

`../capm_fiori_hana_sample/` and `../capm_external_api_integration/`
are the other two CAP (Node.js) templates in this project — same
`cds.ApplicationService`/`srv/*.js` handler conventions (see
[[project_sap_capm_fiori_external_api]]), same CDS modeling style.
This template's `TaskService` could just as easily grow the
external-API-calling patterns from `capm_external_api_integration/`
(e.g. an action here calling out to CPI/BPA) without changing
anything about how the UI5 frontend talks to it — the frontend only
ever sees `/odata/v4/task/...`, never whatever the service handler
does internally.

The RAP templates (`../rap_managed_fiori/`, `../rap_unmanaged_fiori/`,
`../rap_bapi_posting_fiori/`) are the ABAP-side equivalent of "here's
the backend, here's the Fiori frontend" — useful for contrasting CAP
+ UI5 against RAP + Fiori elements for the SAME kind of CRUD-plus-
actions business scenario, in an interview.
