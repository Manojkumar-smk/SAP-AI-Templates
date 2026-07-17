/*
============================================================
DOMAIN MODEL — Task Board
============================================================
Use this when: you need a small, realistic entity to hang a
FREESTYLE UI5 app off of (as opposed to ../capm_fiori_hana_sample/,
which pairs the same kind of CAP backend with a Fiori ELEMENTS
annotation-driven frontend). Kept intentionally simple — one main
entity, one code-list association — so the UI5 app's hand-written
views/controllers are the focus, not the data model.
============================================================
*/

namespace sap.capire.taskboard;

using { cuid, managed } from '@sap/cds/common';

entity Tasks : cuid, managed {
  title       : String(100)  @mandatory;
  description : String(1000);
  status      : String(20)   @assert.range enum {
                  Open        = 'Open';
                  InProgress  = 'In Progress';
                  Done        = 'Done';
                } default 'Open';
  priority    : String(10)   @assert.range enum {
                  Low    = 'Low';
                  Medium = 'Medium';
                  High   = 'High';
                } default 'Medium';
  dueDate     : Date;
  assignee    : String(80);
}

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why `String(20)` with an `enum` instead of a proper code-list
   entity (e.g. a Status entity with a foreign key)?
A: Deliberate simplification for a TEMPLATE meant to highlight the
   UI5 layer. `@assert.range enum {...}` still gives you real
   server-side validation (an invalid status value is rejected with
   a proper CAP error) and the value list shows up in
   `$metadata` for UI5's `sap.ui.model.odata.type` binding — a real
   project with many statuses shared across entities would
   typically promote this to its own entity instead, exactly like
   `../capm_fiori_hana_sample/db/schema.cds`'s `Products`/
   `Customers` associations do for genuinely relational data.

Q: `cuid` and `managed` — what do these mixins from `@sap/cds/
   common` actually add?
A: `cuid` adds a UUID `ID` key (auto-generated on insert, matching
   this project's established convention — see [[project_sap_capm_fiori_external_api]]'s
   schema too). `managed` adds `createdAt`/`createdBy`/
   `modifiedAt`/`modifiedBy`, auto-populated by the framework on
   every insert/update — no handler code needed for audit fields,
   unlike the ABAP RAP templates in this project where you often
   set those by hand.
------------------------------------------------------------*/
