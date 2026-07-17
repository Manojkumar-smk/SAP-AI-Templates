/*
============================================================
CLIENT — SAP Build Process Automation (start a workflow instance)
============================================================
Use this when: a business event in your CAP app (e.g. a Sales
Order needing manager approval) should kick off an SAP Build
Process Automation workflow instead of implementing approval
logic by hand in CAP.

API shape (SAP Build Process Automation's public Workflow
Instances API, via API Business Hub):
  POST /v1/workflow-instances
  { "definitionId": "<process-definition-id>", "context": { ...input params... } }
Auth: OAuth2ClientCredentials against the BPA service instance's
own UAA — configure this on the BTP destination, same as any other
SAP BTP service-to-service call.

Setup (package.json cds.requires.BPA_API):
  "credentials": { "url": "http://localhost:9100", "path": "/process-instances" }
  for local dev, with "[production]" overriding to
  { "destination": "bpa-destination", "path": "/process-instances" } —
  the destination's URL should point at your BPA service instance's
  API endpoint (find it via BTP Cockpit → your Process Automation
  instance → API Endpoint, or SAP Note / KBA 3501325).
============================================================
*/

const cds = require('@sap/cds');

/**
 * Starts a new BPA process instance for the given definition, with
 * the given input context. Returns the created instance (including
 * its instanceId, used later to poll or correlate a callback).
 */
async function startApprovalProcess(definitionId, context) {
  const bpa = await cds.connect.to('BPA_API');

  return bpa.post('/v1/workflow-instances', {
    definitionId,
    context,
  });
}

/** Example: kick off a Sales Order approval workflow. */
async function startSalesOrderApproval(salesOrder) {
  return startApprovalProcess('sales-order-approval', {
    orderId: salesOrder.ID,
    orderNo: salesOrder.orderNo,
    totalAmount: salesOrder.totalAmount,
    currency: salesOrder.currency_code,
  });
}

module.exports = { startApprovalProcess, startSalesOrderApproval };

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: What does "definitionId" actually refer to, and where does it
   come from?
A: It's the ID of a WORKFLOW DEFINITION you've already modeled and
   deployed in the SAP Build Process Automation editor (or via its
   deployment API) — this client doesn't create workflows, it only
   starts INSTANCES of ones that already exist.

Q: Why pass business data via a "context" object instead of, say,
   query parameters?
A: The workflow definition declares typed input parameters (its
   "start form"/context schema) that the running process instance
   reads from — context is how CAP hands business data (which order,
   which amount) into the workflow's own data model, decoupled from
   HTTP transport details.

Q: How would the CAP app find out when the approval is DECIDED
   (approved/rejected), given this call only STARTS the process?
A: Two common patterns: (1) BPA calls back into a CAP-exposed
   webhook/action when the process completes a task, or (2) CAP
   polls the workflow instance status via BPA's API. This client
   only covers the "start" half — see USER_MANUAL.md for how the
   sibling files in this folder would need a callback endpoint to
   close the loop.

Q: Why use bpa.post(path, data) here but cpi.send({...}) in the CPI
   client?
A: Functionally interchangeable for a plain POST with default JSON
   headers — .post() is just the shorthand. It's used here to show
   BOTH styles across this folder's files rather than because BPA
   specifically requires it.
------------------------------------------------------------
*/
