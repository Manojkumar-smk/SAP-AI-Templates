/*
============================================================
SRV LAYER — Custom Handlers (business logic)
============================================================
Use this when: annotations and projections alone aren't enough
— you need real code to compute values, validate state
transitions, or implement custom actions.

VERIFIED END-TO-END against a live `cds watch` instance during
development of this template (not just written from docs):

  POST /sales/SalesOrderItems  {parent_ID:'o1', product_ID:'p1', quantity:3}
  → returns netAmount: "37.50"           (= Products[p1].price 12.50 × 3)

  GET  /sales/SalesOrders(ID=o1)
  → totalAmount: "37.50"                  (rolled up from the item above)

  POST /sales/SalesOrders(ID=o1)/SalesService.confirm
  → status: "CONFIRMED"

  POST /sales/SalesOrders(ID=o1)/SalesService.confirm   (called again)
  → HTTP 400: "Order SO-0001 is 'CONFIRMED' and cannot be confirmed."

A real bug was caught and fixed during this verification: the first
version of the netAmount handler read `req.data.product` (the
association), which is undefined when a client POSTs the flattened
foreign key `product_ID` (the normal case for a plain REST/Fiori
POST) — silently leaving netAmount null. Fixed by reading
`req.data.product_ID` directly. Left in as a comment below because
it's a genuinely common CAP gotcha, not a hypothetical one.
============================================================
*/

const cds = require('@sap/cds');

module.exports = class SalesService extends cds.ApplicationService {
  init() {
    const { SalesOrders, SalesOrderItems } = this.entities;

    // ── Computed field: netAmount = product.price × quantity ─────────
    this.before(['CREATE', 'UPDATE'], SalesOrderItems, async (req) => {
      // GOTCHA (verified): req.data.product is undefined when the client
      // sends the flattened FK "product_ID" instead of a nested
      // { product: { ID: ... } } object — always check both shapes.
      const productId = req.data.product_ID || (req.data.product && req.data.product.ID);
      const { quantity } = req.data;

      if (productId && quantity != null) {
        const prod = await SELECT.one.from('sap.capire.sales.Products').where({ ID: productId });
        if (prod) req.data.netAmount = prod.price * quantity;
      }
    });

    // ── Roll-up: SalesOrders.totalAmount = sum of its items' netAmount ─
    // Runs after ANY item CREATE/UPDATE/DELETE, re-reading all items for
    // that order rather than incrementally adjusting — simpler and safe
    // against out-of-order concurrent writes, at the cost of one extra
    // SELECT per item change (fine at this data volume; a high-volume
    // order-line system would want a different strategy).
    this.after(['CREATE', 'UPDATE', 'DELETE'], SalesOrderItems, async (data, req) => {
      const parentId = req.data.parent_ID || (data && data.parent_ID);
      if (!parentId) return;

      const items = await SELECT.from(SalesOrderItems).where({ parent_ID: parentId });
      const total = items.reduce((sum, i) => sum + (i.netAmount || 0), 0);
      await UPDATE(SalesOrders, parentId).with({ totalAmount: total });
    });

    // ── Custom action: confirm ─────────────────────────────────────────
    // Bound actions receive req.subject — a CQN query already scoped to
    // the specific SalesOrders row the client called the action on, so
    // SELECT.one.from(req.subject) needs no extra WHERE clause.
    this.on('confirm', SalesOrders, async (req) => {
      const order = await SELECT.one.from(req.subject);

      if (order.status !== 'NEW') {
        // req.error() sets the HTTP status AND aborts the handler chain —
        // no further code in this handler runs, and no UPDATE happens.
        return req.error(400, `Order ${order.orderNo} is '${order.status}' and cannot be confirmed.`);
      }

      await UPDATE(req.subject).with({ status: 'CONFIRMED' });
      return SELECT.one.from(req.subject);
    });

    // ── Custom action: cancel ──────────────────────────────────────────
    this.on('cancel', SalesOrders, async (req) => {
      const order = await SELECT.one.from(req.subject);

      if (!['NEW', 'CONFIRMED'].includes(order.status)) {
        return req.error(400, `Order ${order.orderNo} is '${order.status}' and cannot be cancelled.`);
      }

      await UPDATE(req.subject).with({ status: 'CANCELLED' });
      return SELECT.one.from(req.subject);
    });

    // Always call super.init() LAST — it wires up the generic CRUD
    // handlers (including @readonly enforcement, draft handling if
    // enabled, etc.). Handlers registered above run BEFORE the generic
    // ones for 'before'/'on' phases of the SAME event, so this ordering
    // is what lets a custom 'on' handler for 'confirm' take precedence
    // over any generic fallback.
    return super.init();
  }
};

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why compute totalAmount by re-summing ALL items instead of just
   adding/subtracting the one item that changed?
A: Incremental updates require correctly reversing the OLD value on
   UPDATE/DELETE, which needs an extra read anyway (to know what the
   old netAmount was) — re-summing is simpler, self-correcting if
   anything ever drifts, and only costs one more query at this scale.

Q: Why does the confirm/cancel guard re-SELECT the order instead of
   trusting whatever status the client's request implies?
A: The client only sent the ACTION name (confirm/cancel), not the
   order's current status — the server is the only source of truth
   for state transitions, and re-reading prevents a stale/cached
   client from illegally confirming an already-cancelled order.

Q: What does `return req.error(400, ...)` actually do, versus
   `throw new Error(...)`?
A: req.error() is the CAP-idiomatic way to return a structured OData
   error response with a specific HTTP status code and message —
   throwing a plain Error would surface as a generic 500, losing the
   "this was a legitimate business rule violation, not a server bug"
   distinction that a 400 communicates to the caller.

Q: Why register custom handlers BEFORE calling super.init(), and why
   does the ORDER of before/on registration matter?
A: CAP builds a handler chain per event; for 'on' handlers (which
   handle the actual request, e.g. an action), the FIRST matching
   handler wins and later ones don't run — registering the custom
   'confirm' handler before the generic fallback from super.init()
   ensures the custom logic is the one that executes.
------------------------------------------------------------
*/
