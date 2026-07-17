# RAP Unmanaged BO + Fiori Elements — User Manual

A complete **UNMANAGED** RAP Business Object (Customer Master) with
a Fiori elements UI: every CRUD operation is hand-written — the
handler class stages changes into a manual buffer during the
interaction phase, and the saver class flushes that buffer to the
database with real `INSERT`/`UPDATE`/`DELETE` statements.

> **Verification note:** as with `../rap_managed_fiori/`, this
> could not be compiled/run — no ABAP runtime is available here.
> The buffer-handoff pattern (`CLASS-DATA` staged in `lhc_`, flushed
> in `lsc_`'s `SAVE`) is a well-established, widely-taught RAP
> idiom, cross-checked against a live fetched tutorial (see the
> memory record for the source), but activate and test every
> object in ADT before relying on it.

---

## Folder Structure

```
rap_unmanaged_fiori/
├── ztcustomer.tabl.astabl        ← Persistent DB table
├── zi_customer.ddls.asddls       ← Interface view (root view entity)
├── zc_customer.ddls.asddls       ← Projection view
├── zc_customer.ddlx.asddlsxt     ← Metadata extension (Fiori UI)
├── zi_customer.bdef.asbdef       ← Behavior definition (interface, UNMANAGED)
├── zc_customer.bdef.asbdef       ← Behavior definition (projection)
├── zbp_i_customer.clas.abap      ← Behavior implementation class (lhc_ + lsc_)
├── zui_customer.srvd.srvdsrv     ← Service definition
├── zui_customer_o4.srvb.srvbsrv  ← Service binding (ADT-wizard notes)
└── USER_MANUAL.md
```

---

## How the Pieces Fit Together

```
Fiori App ──OData V4──▶ Service Binding/Definition ──▶ Projection (zc_customer)
                                                              │
                                                    Interface (zi_customer)
                                                    BDEF: "unmanaged implementation..."
                                                              │
                                        ┌─────────────────────┴─────────────────────┐
                                 INTERACTION PHASE                          SAVE SEQUENCE
                             (lhc_customer — no DB writes)           (lsc_customer — real SQL)
                          create/update/delete stage into      finalize → stamp admin fields
                          CLASS-DATA gt_create/gt_update/       save     → INSERT/UPDATE/DELETE
                          gt_delete (shared static buffer)      cleanup_finalize → CLEAR buffers
                                                              │
                                                       ztcustomer (DB table)
```

The `CLASS-DATA` buffer declared in `lhc_customer`'s `PUBLIC
SECTION` is the entire mechanism that makes "unmanaged" possible —
it's how data staged during the interaction phase survives to be
persisted later by a *different* class (`lsc_customer`) during the
save sequence.

---

## Quick Decision Guide

| Your situation | Use UNMANAGED? |
|---|---|
| Root view is a plain single-table SELECT, standard CRUD is enough | No — use `../rap_managed_fiori/`, less code |
| You need to write to a SECOND table (audit log, history) in the same save | Yes |
| You're wrapping a classic BAPI/RFC instead of a Z table | Not quite — see `../rap_bapi_posting_fiori/` (managed interaction + unmanaged save is usually cleaner for that case) |
| Complex partial-update merge logic, non-trivial locking, legacy integration | Yes |

---

## Setup (ADT / Eclipse)

1. Same creation order as the managed template: table → interface
   view → interface BDEF (choose **Unmanaged**) → projection view
   → metadata extension → projection BDEF → implementation class
   (quick-fix scaffolds `lhc_customer`/`lsc_customer`, paste this
   template's bodies in) → service definition → service binding.
2. Create the lock object referenced in the `lock` method: SE11/ADT
   → New → Lock Object → name `ZCUSTOMER_L`, table `ZTCUSTOMER`,
   lock mode `E` (exclusive) — this auto-generates the
   `ENQUEUE_ZCUSTOMER_L`/`DEQUEUE_ZCUSTOMER_L` function modules the
   `lock` method calls.
3. Activate everything, then Preview the Service Binding.

---

## Common Errors

| Error | Fix |
|-------|-----|
| Newly created row disappears after save / duplicates on next create | `CLEAR` the `gt_create`/`gt_update`/`gt_delete` buffers in `cleanup_finalize` — forgetting this is THE classic unmanaged-RAP bug (see the class file's interview points) |
| `read` method never gets called for a just-created row, field values look stale | Expected — RAP's internal buffer serves reads for records created earlier in the SAME request without invoking your `read` method again; only previously-SAVED rows go through your SELECT |
| `lock` method fails with "function module ENQUEUE_ZCUSTOMER_L not found" | You skipped step 2 above — the lock object must be created and activated before this compiles |
| Partial update overwrites fields the client didn't send with blanks | Check `entity-%control-<Field> = if_abap_behv=>mk-on` before copying each field in the `update` method — RAP only sets `%control` for fields the CLIENT actually sent, letting you distinguish "not sent" from "sent as blank" |
| `check_before_save` / `save` fires but nothing persists | Confirm you're reading from `lhc_customer=>gt_create` etc. (the STATIC class attribute) and not an instance variable — a common typo when copying this pattern is declaring the buffer as instance `DATA` instead of `CLASS-DATA`, which breaks the whole hand-off |

---

## How This Relates to the Other Templates

`../rap_managed_fiori/` is this template's mirror image — same UI
layer conventions, opposite persistence strategy. Read both
`zbp_i_product.clas.abap` and `zbp_i_customer.clas.abap` side by
side: the `lhc_`/`lsc_` class SKELETON is identical in both (same
method signatures, same save-sequence method names) — only the
METHOD BODIES differ, which is the clearest way to internalize what
"managed" vs "unmanaged" actually changes.

`../rap_bapi_posting_fiori/` takes the buffer-handoff mechanic
introduced here one step further: instead of the `SAVE` method
writing to a Z table with `INSERT`/`UPDATE`, it calls a wrapped
BAPI — same `lhc_`→`lsc_` hand-off shape, different destination for
the data.
