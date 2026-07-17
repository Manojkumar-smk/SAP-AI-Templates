/*
============================================================
SRV LAYER — Service Definition (protocol-facing)
============================================================
Use this when: you're deciding WHAT a service exposes from the
domain model — which entities, in what shape (a "projection"),
with which extra operations (actions). This file stays free of
Fiori-specific UI annotations on purpose — see
../app/orders/fiori-service.cds for those (CAP's recommended
separation: srv/ defines WHAT is exposed, app/ defines HOW it
looks, per https://cap.cloud.sap/docs/guides/uis/fiori).

Why "as projection on" instead of exposing db entities directly:
  A projection lets you rename, hide, or restrict fields per
  service without touching the shared domain model in db/ —
  other services could expose the SAME Customers/Products
  entities differently (e.g. an internal admin service showing
  more fields than this customer-facing one).

Verified: this file — together with sales-service.js — was run
against a live SQLite-backed OData service during development,
not just compiled. See sales-service.js's header for the exact
requests that were tested.
============================================================
*/

using { sap.capire.sales as db } from '../db/schema';

// @requires: 'authenticated-user' → in production (xsuaa auth kind),
// every request must carry a valid JWT. In local dev (auth kind
// 'mocked', see package.json) this is NOT automatically satisfied —
// verified directly: an anonymous curl request gets a plain
// "Unauthorized" once this annotation is added, and needs Basic auth
// with one of CAP's built-in mock users to pass, e.g.:
//   curl -u alice: http://localhost:4004/sales/SalesOrders
// (any password works in mocked mode — only the username is checked
// against cds.requires.auth.users, run `cds env get requires.auth`
// to see the full built-in list: alice, bob, carol, dave, ...).
// xs-security.json defines finer-grained SalesUser/SalesAdmin scopes
// as a starting point if you want to gate specific actions (e.g.
// restrict `cancel` to SalesAdmin via `@(requires: 'SalesAdmin')`
// directly on the action).
@(requires: 'authenticated-user')
service SalesService @(path: '/sales') {

  // @readonly (entity-level) → Fiori will not offer Create/Update/Delete
  // UI actions for these two — they're master data maintained elsewhere
  // in this sample, only referenced (not edited) from the Sales Order app.
  @readonly
  entity Customers as projection on db.Customers;

  @readonly
  entity Products  as projection on db.Products;

  // "actions { ... }" appends custom operations to the projection,
  // scoped to a SPECIFIC SalesOrder instance (bound actions — that's
  // why they can return "SalesOrders", the same type, and why the UI
  // annotations in fiori-service.cds can turn them into buttons that
  // appear once a row/object is already selected).
  entity SalesOrders as projection on db.SalesOrders actions {
    action confirm() returns SalesOrders;
    action cancel()  returns SalesOrders;
  };

  entity SalesOrderItems as projection on db.SalesOrderItems;
}
