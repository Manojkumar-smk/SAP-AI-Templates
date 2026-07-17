# RAP Managed BO + Fiori Elements — User Manual

A complete **MANAGED** RAP Business Object (Product Master) with a
Fiori elements UI: the framework auto-generates all CREATE/UPDATE/
DELETE database logic, and you write only the parts it can't infer
— validation, determination, actions, authorization.

> **Verification note (read this first):** unlike this project's
> Python/Node.js templates (`../mcp_server_cloud_foundry/`,
> `../capm_fiori_hana_sample/`, etc.), which were installed and
> actually RUN in a sandbox, **this ABAP template could not be
> compiled or executed** — there is no ABAP runtime available in
> this environment. Every pattern here is built from current,
> authoritative sources (SAP Help Portal, official SAP-samples
> GitHub RAP workshops, and verified community RAP tutorials — see
> the memory record for exact sources) and cross-checked for
> internal consistency across files, but you MUST activate each
> object in ADT and resolve any release-specific syntax drift
> before treating this as production code.

---

## Folder Structure

```
rap_managed_fiori/
├── ztproduct.tabl.astabl         ← Persistent DB table (root table)
├── zi_product.ddls.asddls        ← Interface view (root view entity)
├── zc_product.ddls.asddls        ← Projection view (consumption)
├── zc_product.ddlx.asddlsxt      ← Metadata extension (Fiori UI annotations)
├── zi_product.bdef.asbdef        ← Behavior definition (interface, MANAGED)
├── zc_product.bdef.asbdef        ← Behavior definition (projection)
├── zbp_i_product.clas.abap       ← Behavior implementation class (lhc_ + lsc_)
├── zui_product.srvd.srvdsrv      ← Service definition
├── zui_product_o4.srvb.srvbsrv   ← Service binding (ADT-wizard notes, not code)
└── USER_MANUAL.md
```

File extensions follow the real **abapGit** naming convention used
when these objects are version-controlled in a git repo (as opposed
to SE80/SE11 GUI names) — this is what you'd actually see in a
cloned ABAP Cloud repository.

---

## How the Pieces Fit Together

```
Fiori App  ──HTTP/OData V4──▶  Service Binding (zui_product_o4)
                                      │
                                Service Definition (zui_product.srvd)
                                      │
                            Projection View (zc_product.ddls)
                              + Metadata Ext. (zc_product.ddlx)   ← UI annotations
                              + Projection BDEF (zc_product.bdef) ← "use create/update/..."
                                      │
                              Interface View (zi_product.ddls)
                              + Interface BDEF (zi_product.bdef)  ← "managed", validations,
                                      │                              determinations, actions
                          Behavior Impl. Class (zbp_i_product)
                              lhc_product  → validations/determinations/actions/auth
                              lsc_product  → EMPTY save methods (framework does the SQL)
                                      │
                            Persistent Table (ztproduct)
```

The MANAGED keyword in `zi_product.bdef.asbdef` is what makes the
bottom three layers collapse into framework-generated SQL — that's
the entire value proposition of "managed" vs. the unmanaged
template.

---

## Quick Decision Guide: Is MANAGED the Right Choice?

| Your situation | Use MANAGED? |
|---|---|
| Root view selects from ONE real transparent table, no joins | Yes — this template |
| You need custom business logic (validations, defaults, status transitions) | Yes — via validations/determinations/actions, framework still does CRUD |
| The "table" you're really writing to is a classic BAPI, RFC, or external API | No — see `../rap_bapi_posting_fiori/` |
| You need full hand-control over the SQL (e.g. writing to 3 tables per save, complex locking) | No — see `../rap_unmanaged_fiori/` |
| Root view is a JOIN/UNION of multiple tables | No — managed requires a single persistent table |

---

## Setup (ADT / Eclipse)

1. Create objects in this order (each depends on the previous):
   `ztproduct.tabl.astabl` → `zi_product.ddls.asddls` →
   `zi_product.bdef.asbdef` (choose **Managed** when the wizard
   asks for implementation type) → `zc_product.ddls.asddls` →
   `zc_product.ddlx.asddlsxt` → `zc_product.bdef.asbdef` →
   `zbp_i_product.clas.abap` (auto-scaffolded by clicking the
   quick-fix on the BDEF's activation warning, then paste this
   template's method bodies in) → `zui_product.srvd.srvdsrv` →
   Service Binding (see that file's header for the exact wizard
   steps).
2. Register message class `ZPRODUCT_MSG` with message `001`
   (referenced in `validatePrice`), text e.g. `Product &1 must
   have a price greater than zero` — or just use
   `new_message_with_text(...)` everywhere instead if you'd rather
   skip message class maintenance for a quick demo.
3. Activate everything, then **Preview** the Service Binding.

---

## Common Errors

| Error | Fix |
|-------|-----|
| BDEF activation fails: "Managed implementation requires a persistent table" | Root view's FROM clause isn't a single transparent table — check for joins/views creeping in |
| "Field X used in mapping is not part of the entity" | The `mapping for ztproduct { ... }` block in the interface BDEF must list EVERY exposed field, on both sides, with matching case-sensitivity for the table-side names |
| Action button doesn't appear on the Fiori Object Page | Confirm BOTH the interface BDEF (`action (features:instance) activate ...`) AND projection BDEF (`use action activate;`) declare it — missing either one silently hides it |
| 412 Precondition Failed on every update | Expected ETag behavior from `LocalLastChangedAt` — the UI must re-read after any change before allowing another edit; don't treat this as a bug |
| Validation error doesn't block save | `%element-price = if_abap_boolean=>true` in `reported` is what ties the message to a specific FIELD for UI highlighting — omitting it still shows the message but won't highlight the field, and forgetting to APPEND to `failed-product` (not just `reported-product`) won't block the save at all |

---

## How This Relates to the Other Templates

This is the "framework does the work" baseline. `../rap_unmanaged_fiori/`
shows the opposite extreme (you write every SQL statement).
`../rap_bapi_posting_fiori/` is the hybrid — managed interaction
phase (like this template) but a hand-written save that calls a
BAPI instead of either the framework's auto-SQL or your own raw
SQL. Read the three BDEFs side by side (one word differs each time:
`managed`, `unmanaged`, `managed with unmanaged save`) to see the
whole spectrum in one sitting.

The Fiori-layer conventions here (metadata extension separate from
projection view, `@UI.facet`/`lineItem`/`identification` structure)
deliberately mirror the CAP+Fiori-elements annotations in
`../capm_fiori_hana_sample/app/orders/fiori-service.cds` — same UI
concepts, different syntax, useful for contrasting CAP vs. RAP in
an interview.
