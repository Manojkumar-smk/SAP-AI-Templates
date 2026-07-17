/*
============================================================
APP LAYER — Fiori Elements Annotations ("the frontend")
============================================================
Use this when: this IS the answer to "how do I build a frontend
using annotations" — SAP Fiori elements apps are generic UI
renderers that read these annotations from the service's OData
$metadata and construct the List Report + Object Page screens
from them. There is close to zero hand-written UI code involved
— the manifest.json in ./webapp/ just points at this service,
and the floorplan (List Report / Object Page) is entirely driven
by what's annotated here.

Where this file lives and why:
  CAP's recommendation is to keep srv/*.cds free of UI concerns
  and put Fiori annotations in app/<app-name>/fiori-service.cds,
  using `annotate <Service>.<Entity> with @(...)` from OUTSIDE the
  service definition. This keeps the service's protocol contract
  (srv/sales-service.cds) readable on its own, and lets different
  Fiori apps annotate the SAME service differently if needed.

Verified: compiled together with sales-service.cds via
`cds compile ... --to edmx` (zero errors) and the resulting
$metadata was inspected to confirm every annotation below
produces the expected OData UI vocabulary terms.
============================================================
*/

using SalesService as service from '../../srv/sales-service';

// ── List Report + Object Page for SalesOrders ──────────────
annotate service.SalesOrders with @(
  UI: {
    // Filter bar fields on the List Report.
    SelectionFields: [ status, customer_ID, orderDate ],

    // Object Page title/subtitle — Title binds to orderNo, Description
    // to status, so the page header reads e.g. "SO-0001 — CONFIRMED".
    HeaderInfo: {
      TypeName      : 'Sales Order',
      TypeNamePlural: 'Sales Orders',
      Title         : { Value: orderNo },
      Description   : { Value: status },
    },

    // Table columns on the List Report. The two DataFieldForAction
    // entries turn the confirm/cancel actions (defined in
    // sales-service.cds) into row-level action buttons — no UI5
    // controller code needed to wire that up.
    LineItem: [
      { Value: orderNo,     Label: 'Order No' },
      { Value: customer.name, Label: 'Customer' },
      { Value: orderDate,   Label: 'Order Date' },
      { Value: status,      Label: 'Status' },
      { Value: totalAmount, Label: 'Total' },
      { $Type: 'UI.DataFieldForAction', Action: 'SalesService.confirm', Label: 'Confirm' },
      { $Type: 'UI.DataFieldForAction', Action: 'SalesService.cancel',  Label: 'Cancel' },
    ],

    // Same two actions, as toolbar buttons on the Object Page header
    // (in addition to the row-level buttons above on the list).
    Identification: [
      { $Type: 'UI.DataFieldForAction', Action: 'SalesService.confirm', Label: 'Confirm Order' },
      { $Type: 'UI.DataFieldForAction', Action: 'SalesService.cancel',  Label: 'Cancel Order' },
    ],

    // Facets structure the Object Page into sections/tabs. A
    // ReferenceFacet pointing at a FieldGroup renders a form; one
    // pointing at "items/@UI.LineItem" renders the item COMPOSITION
    // as an embedded, editable table — this is what makes Fiori
    // elements show "Items" as its own section automatically.
    Facets: [
      { $Type: 'UI.ReferenceFacet', Label: 'Order Details', Target: '@UI.FieldGroup#Main' },
      { $Type: 'UI.ReferenceFacet', Label: 'Items',         Target: 'items/@UI.LineItem' },
    ],

    FieldGroup #Main: {
      Data: [
        { Value: orderNo },
        { Value: customer_ID, Label: 'Customer' },
        { Value: orderDate },
        { Value: status },
        { Value: totalAmount },
        { Value: currency_code },
      ],
    },
  }
);

// ── Item table columns (rendered inside the Items facet above) ─
annotate service.SalesOrderItems with @(
  UI.LineItem: [
    { Value: product.name, Label: 'Product' },
    { Value: quantity,     Label: 'Quantity' },
    { Value: netAmount,    Label: 'Net Amount' },
  ]
);

// ── Master-data list for Customers (its own, simpler List Report) ─
annotate service.Customers with @(
  UI: {
    SelectionFields: [ name, country_code ],
    HeaderInfo: {
      TypeName: 'Customer', TypeNamePlural: 'Customers',
      Title: { Value: name },
    },
    LineItem: [
      { Value: name,         Label: 'Name' },
      { Value: email,        Label: 'Email' },
      { Value: country_code, Label: 'Country' },
    ],
  }
) {
  // @cds.odata.valuelist on the key: every OTHER entity that has a
  // managed association to Customers (like SalesOrders.customer)
  // automatically gets a value-help dropdown in Fiori — no extra
  // Common.ValueList annotation needs to be hand-written anywhere.
  ID @cds.odata.valuelist;
};
