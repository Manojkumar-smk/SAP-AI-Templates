# RAP BAPI Posting + Fiori Elements — User Manual

A **managed-with-unmanaged-save** RAP Business Object that posts
Sales Orders into S/4HANA via the classic `BAPI_SALESORDER_
CREATEFROMDAT2`, wrapped for Clean Core / ABAP Cloud compliance. The
interaction phase (create form, mandatory-field checks) is standard
managed RAP; only the SAVE step is hand-written, and it delegates to
a released wrapper class instead of calling the BAPI directly.

> **Verification note:** could not be compiled/run — no ABAP
> runtime available. This is the highest-risk template of the
> three to take as-is: the BAPI wrapper's field mapping
> (`BAPISDHD1`/`BAPISDITM`/`BAPIPARNR`) and `save_modified`'s exact
> generated parameter/component names are the parts most likely to
> need adjustment against your actual system release and ADT's
> generated skeleton. The PATTERN (wrapper class + factory +
> `managed with unmanaged save` + `late numbering` + `CONVERT KEY` +
> `BAPI_TRANSACTION_COMMIT` inside `save_modified`) is
> well-established and cross-checked against a real, currently
> published worked example plus SAP's own sample GitHub RAP
> workshop — see the memory record for exact sources.

---

## Folder Structure

```
rap_bapi_posting_fiori/
├── ztsalesorderbuf.tabl.astabl          ← Staging buffer table (NOT the system of record)
├── zi_salesorderrap.ddls.asddls         ← Interface view
├── zc_salesorderrap.ddls.asddls         ← Projection view
├── zc_salesorderrap.ddlx.asddlsxt       ← Metadata extension (Fiori UI)
├── zi_salesorderrap.bdef.asbdef         ← Behavior def (MANAGED WITH UNMANAGED SAVE, late numbering)
├── zc_salesorderrap.bdef.asbdef         ← Behavior def (projection)
├── zif_wrap_bapi_salesorder.intf.abap   ← Wrapper interface (the released Clean Core boundary)
├── zcl_wrap_bapi_salesorder.clas.abap   ← Wrapper implementation (the ONLY place the BAPI is called)
├── zcl_wrap_bapi_salesorder_fac.clas.abap ← Factory (the released entry point)
├── zbp_i_salesorderrap.clas.abap        ← Behavior implementation (lhc_ + lsc_ with save_modified)
├── zui_salesorderrap.srvd.srvdsrv       ← Service definition
├── zui_salesorderrap_o4.srvb.srvbsrv    ← Service binding (ADT-wizard notes)
└── USER_MANUAL.md
```

---

## How the Pieces Fit Together

```
Fiori App ──OData V4──▶ Service Binding/Definition ──▶ Projection (zc_salesorderrap)
                                                              │
                                                    Interface (zi_salesorderrap)
                                       BDEF: "managed with unmanaged save" + "late numbering"
                                                              │
                        ┌─────────────────────────────────────┴─────────────────────────────────────┐
                 INTERACTION PHASE (managed, free)                              SAVE SEQUENCE (unmanaged, hand-written)
            framework buffers create/update automatically       lsc_salesorderrap.save_modified():
            lhc_: validateMandatoryData, retryPosting action       for each CREATEd row →
                                                                       zcl_wrap_bapi_salesorder_fac
                                                                          → zcl_wrap_bapi_salesorder
                                                                             → CALL FUNCTION 'BAPI_SALESORDER_CREATEFROMDAT2'
                                                                             → CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
                                                                       UPDATE ztsalesorderbuf (outcome)
                                                                       CONVERT KEY OF ... FROM %pid TO final key
                                                              │
                                        ztsalesorderbuf (buffer/audit)         S/4HANA VBAK/VBAP (real sales order)
```

---

## The BAPI Wrapper Pattern (Why Three Extra Files?)

`BAPI_SALESORDER_CREATEFROMDAT2` is a **classic, non-released**
function module — calling it directly from `strict(2)` ABAP Cloud
code is a syntax error. The standard fix:

1. **`zif_wrap_bapi_salesorder`** — an interface YOU define, with a
   clean, typed signature (no `BAPIRET2`, no classic BAPI structures
   leaking out).
2. **`zcl_wrap_bapi_salesorder`** — implements it, and is the ONLY
   class in this entire template allowed to `CALL FUNCTION
   'BAPI_SALESORDER_CREATEFROMDAT2'`.
3. **`zcl_wrap_bapi_salesorder_fac`** — a factory; RAP code asks
   THIS for an instance, never instantiates the implementation
   directly (`CREATE PRIVATE` on both classes enforces this).

Only the interface + factory need to go through ADT's **Release
Contract** step to become legally callable from strict-mode RAP
code — the implementation class (where the actual BAPI call lives)
never needs to be released.

---

## Quick Decision Guide

| Your situation | Use this pattern? |
|---|---|
| Persistence target is a classic BAPI/RFC, not a table you own | Yes — this template |
| Target is a RELEASED RAP-based interface (not a classic BAPI) | Similar shape, but you'd use deep-create EML against that interface instead of `CALL FUNCTION` — see the SAP-samples `rap610` ex4 workshop referenced in this project's memory |
| You control the target table directly | No — see `../rap_unmanaged_fiori/` (no wrapper needed) |
| Standard CRUD against your own table, no external call | No — see `../rap_managed_fiori/` |

---

## Setup (ADT / Eclipse)

1. Create `ztsalesorderbuf.tabl.astabl` → `zi_salesorderrap.ddls.asddls`
   → `zi_salesorderrap.bdef.asbdef` (implementation type **Managed**,
   then manually add `with unmanaged save` and `late numbering` if
   the wizard doesn't offer them directly) → projection view →
   metadata extension → projection BDEF.
2. Create `zif_wrap_bapi_salesorder.intf.abap`, then
   `zcl_wrap_bapi_salesorder.clas.abap`, then
   `zcl_wrap_bapi_salesorder_fac.clas.abap` — in that order, since
   each depends on the previous.
3. **Release** `zif_wrap_bapi_salesorder` and
   `zcl_wrap_bapi_salesorder_fac` via ADT → right-click → Show
   Release State / Release Contract (needed before strict-mode code
   can reference them — the behavior implementation class won't
   activate without this step).
4. Create `zbp_i_salesorderrap.clas.abap` via the BDEF's quick-fix,
   paste in this template's method bodies, **re-check the generated
   `save_modified` signature against what ADT scaffolds** (see the
   caveat at the top of this manual) and adjust component names if
   they differ.
5. Service definition → service binding → Preview.

---

## Common Errors

| Error | Fix |
|-------|-----|
| BDEF activation fails: "BAPI/function module call not allowed in strict mode" | You called the BAPI directly from `zbp_i_salesorderrap.clas.abap` instead of through the wrapper — the whole point of `zcl_wrap_bapi_salesorder` is to be the one place that's allowed to do this (after release) |
| `zif_wrap_bapi_salesorder` / `zcl_wrap_bapi_salesorder_fac` won't activate in strict-mode context | Release Contract step (setup step 3) skipped |
| `CONVERT KEY OF ... FROM ... TO ...` syntax error | This statement is only valid **inside a save sequence method** (here, `save_modified`) — calling it from an action or validation is a compile error by design |
| New row stays stuck showing no SalesOrder AND no error message | Check `has_error` logic in `zcl_wrap_bapi_salesorder.clas.abap` — a BAPI can return warnings (type `W`/`I`) that aren't treated as failures; make sure `ev_success`/`ev_message` are always set on every code path |
| `retryPosting` button does nothing | Confirm both BDEFs declare it (`action (features:instance) retryPosting ...` in the interface BDEF, `use action retryPosting;` in the projection BDEF) — same gotcha as the other two templates |
| Real S/4 BAPI error like "Sold-to party does not exist" | Working as intended — that's S/4's own master-data validation surfacing through `BAPIRET2`, captured into `PostingMessage`; fix the test data (`SoldToParty`, `Material`, etc.) to reference real records in your system |

---

## How This Relates to the Other Templates

This is the "hybrid" point on the managed↔unmanaged spectrum: the
interaction phase behaves exactly like `../rap_managed_fiori/`
(framework buffers create/update, you only write validations/
determinations/actions), but the SAVE step behaves like
`../rap_unmanaged_fiori/` (you write real persistence code) — except
here that code calls OUT to an external system instead of writing
to your own table. Read all three `zbp_i_*.clas.abap` files' saver
classes side by side, in this order: `zbp_i_product` (fully empty
save) → `zbp_i_customer` (full hand-written SQL save) →
`zbp_i_salesorderrap` (single `save_modified` calling an external
wrapper) — that progression is the cleanest way to internalize the
whole managed/unmanaged/hybrid spectrum for an interview.

The wrapper-class-for-Clean-Core pattern here is conceptually the
ABAP-side mirror of `../capm_external_api_integration/`'s
`s4_sales_order_client.js`, which calls the SAME kind of S/4 Sales
Order API — but from a CAP (Node.js) side, over OData, using a BTP
Destination instead of a local BAPI call. Comparing the two is a
good way to show you understand BOTH "S/4 as the RAP BO's own
backend" and "S/4 as an external system CAP calls into."
