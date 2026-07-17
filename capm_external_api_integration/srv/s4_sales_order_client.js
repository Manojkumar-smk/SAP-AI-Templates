/*
============================================================
CLIENT — S/4HANA Sales Order API (OData, via cds.connect.to)
============================================================
Use this when: your CAP service needs to read or create Sales
Orders in a real S/4HANA system, using the imported external
model in ./external/API_SALES_ORDER_SRV.cds.

How this differs from the REST clients in this folder:
  Because package.json declares this service with `"kind": "odata"`
  AND a `"model"` pointing at the imported CDS, CAP can REFLECT on
  the entity shapes — meaning you query it with the same cds.ql
  SELECT/INSERT syntax you'd use against your OWN database, not
  raw HTTP calls. srv.entities gives you the actual entity
  definitions to build queries against.

Setup (package.json cds.requires.API_SALES_ORDER_SRV):
  "credentials": { "url": "...", "path": "/sap/opu/odata/sap/API_SALES_ORDER_SRV" }
  for local dev, with a "[production]" block overriding to
  { "destination": "S4HANA_SALES_ORDER", "path": "..." } — create
  that destination in BTP Cockpit → Connectivity → Destinations,
  pointing at your S/4HANA system's Cloud Connector / OAuth setup.
============================================================
*/

const cds = require('@sap/cds');

/**
 * Fetches a single Sales Order with its items from S/4HANA.
 */
async function getSalesOrder(salesOrderId) {
  const srv = await cds.connect.to('API_SALES_ORDER_SRV');
  const { A_SalesOrder } = srv.entities;

  // Standard cds.ql SELECT — CAP translates this into the correct
  // OData GET request (with $expand for to_Item) against the remote
  // service, exactly as it would translate the same query against
  // a local database.
  return srv.run(
    SELECT.one.from(A_SalesOrder, salesOrderId).columns(so => {
      so`.*`, so.to_Item(item => { item`.*` });
    })
  );
}

/**
 * Creates a new Sales Order with one item — demonstrates a WRITE
 * against the remote system, not just a read.
 */
async function createSalesOrder({ soldToParty, salesOrganization, material, quantity }) {
  const srv = await cds.connect.to('API_SALES_ORDER_SRV');
  const { A_SalesOrder } = srv.entities;

  return srv.run(
    INSERT.into(A_SalesOrder).entries({
      SalesOrderType: 'OR',
      SalesOrganization: salesOrganization,
      SoldToParty: soldToParty,
      to_Item: [
        { Material: material, RequestedQuantity: quantity },
      ],
    })
  );
}

module.exports = { getSalesOrder, createSalesOrder };

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why does this file use SELECT/INSERT (cds.ql) instead of raw
   HTTP calls like the REST clients in this folder do?
A: Because the remote service was configured with `kind: "odata"`
   and a `model` (the imported CDS), CAP's RemoteService can
   translate cds.ql queries into correct OData requests — the same
   abstraction that lets CAP code targeting a local db ALSO target
   a remote OData service with the same query syntax. REST-kind
   services (see the other client files) have no such model to
   reflect on, so they only offer raw .get/.post/.send methods.

Q: Where does authentication actually happen for this call?
A: It's entirely configuration, not code — package.json's
   `[production]` block points `credentials.destination` at a BTP
   Destination Service entry, which holds the OAuth/Basic/
   Principal-Propagation auth details AND (for on-prem systems) the
   Cloud Connector routing. This file never sees a token or
   password.

Q: What happens if the imported model (API_SALES_ORDER_SRV.cds) is
   missing a field this code tries to use?
A: CAP would reject the query at the cds.ql level before any HTTP
   request is sent — the model is the contract; if `NetAmount`
   isn't in the imported CSN, `SELECT` can't reference it, which is
   exactly why re-running `cds import` after an S/4 upgrade (that
   might add/rename fields) matters.

Q: Why INSERT with a nested `to_Item` array instead of two separate
   calls (create order, then create item)?
A: S/4HANA's Sales Order API expects deep create — the order and at
   least one item are created in a single OData deep-insert request,
   matching how the business object actually works in S/4 (an order
   with zero items isn't a meaningful business document).
------------------------------------------------------------
*/
