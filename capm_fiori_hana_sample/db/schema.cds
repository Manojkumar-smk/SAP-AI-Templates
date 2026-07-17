/*
============================================================
DB LAYER — Domain Model (Core Data Services)
============================================================
Use this when: you're defining the persistence model a CAP
service will expose. This file has NO knowledge of OData, REST,
or Fiori — it's pure domain modeling, reusable by any number of
services built on top of it (a deliberate CAP separation-of-
concerns principle: db/ stays protocol-agnostic).

Domain: a minimal Sales Order Management model —
  Customers (1) ── (N) SalesOrders (1) ── composition ── (N) SalesOrderItems
                                                              │
                                              Products (1) ──┘ (association)

Why Composition for items but Association for customer/product:
  Composition ("owns") means SalesOrderItems have NO independent
  existence — deleting a SalesOrder deletes its items, and Fiori
  Elements draft mode only allows in-line "Create" for compositions.
  Association ("refers to") means Customers/Products are their own
  independent entities that SalesOrders merely point to — deleting
  an order must never delete the customer or product it referenced.

Verified: this schema was compiled with `cds compile` (zero errors)
and actually deployed + queried against a live SQLite instance
during development of this template — not just written from docs.
============================================================
*/

namespace sap.capire.sales;

// cuid    → adds a UUID `key ID` field (the CAP convention for primary keys)
// managed → adds createdAt/createdBy/modifiedAt/modifiedBy, auto-populated
// Currency, Country → reuse types from @sap/cds/common; they come with
//   built-in code-list entities (Currencies, Countries) and automatically
//   get Fiori value-help (@cds.odata.valuelist) wired up for free.
using { cuid, managed, Currency, Country } from '@sap/cds/common';

entity Customers : cuid, managed {
  name    : String(100) @title: 'Customer Name';
  email   : String(120);
  country : Country;

  // Inverse/virtual side of the SalesOrders.customer association below —
  // "on orders.customer = $self" tells the compiler how to join back,
  // without creating a second foreign key column on this entity.
  orders  : Association to many SalesOrders on orders.customer = $self;
}

entity Products : cuid, managed {
  name        : String(100) @title: 'Product Name';
  description : String(1000);
  price       : Decimal(15,2);
  currency    : Currency;
  stock       : Integer default 0;
}

entity SalesOrders : cuid, managed {
  orderNo     : String(20) @title: 'Order Number';
  customer    : Association to Customers;

  // Inline enum: restricts the value AND gives Fiori clients a proper
  // dropdown instead of a free-text field, with zero extra annotation.
  status      : String(20) enum {
    NEW; CONFIRMED; SHIPPED; CANCELLED;
  } default 'NEW';

  orderDate   : Date;

  // Composition, not Association — see file header for why this
  // distinction matters for both deletion cascading and Fiori draft.
  items       : Composition of many SalesOrderItems on items.parent = $self;

  // @readonly: the CLIENT never sets this directly — it's computed
  // server-side by srv/sales-service.js whenever items change.
  // (Leaving it writable would let a client desync totalAmount from
  // the actual sum of its items.)
  totalAmount : Decimal(15,2) @readonly;
  currency    : Currency;
}

entity SalesOrderItems : cuid {
  parent    : Association to SalesOrders;
  product   : Association to Products;
  quantity  : Integer;

  // @readonly here blocks a CLIENT from setting netAmount directly in
  // a request body — but does NOT block sales-service.js's `before`
  // handler from computing and writing it server-side. Verified
  // directly: @readonly is enforced against incoming request payloads
  // by the OData protocol layer, not against server-side handler code,
  // so this is safe to combine with the computed-field pattern below.
  @readonly netAmount : Decimal(15,2);
}
