/*
============================================================
SERVICE IMPLEMENTATION — wires each action to its external client
============================================================
VERIFIED END-TO-END during development of this template: ran a
local Express mock on :8000 simulating the AI Python API, started
this service with `cds watch`, and called:

  curl -X POST http://localhost:4004/integration/analyzeSalesOrderText \
    -H "Content-Type: application/json" -d '{"text":"SAP BTP is great"}'

  → {"value": "{\"received\":{\"text\":\"SAP BTP is great\"},
               \"sentiment\":\"positive\",\"confidence\":0.95}"}

confirming the full chain: OData action call → this handler →
ai_python_api_client.js → cds.connect.to('AI_PYTHON_API') → real
HTTP POST → mock server → JSON response → back through the action
result. The other five actions follow the identical wiring pattern
(untested against real S4/CPI/BPA/n8n endpoints, which this sandbox
has no access to — but the CAP-side mechanics are the same proven
RemoteService pattern for every one of them).
============================================================
*/

const cds = require('@sap/cds');
const { getSalesOrder, createSalesOrder } = require('./s4_sales_order_client');
const { analyzeText } = require('./ai_python_api_client');
const { triggerIntegrationFlow } = require('./cpi_api_client');
const { startApprovalProcess } = require('./bpa_api_client');
const { triggerWorkflow } = require('./n8n_api_client');

module.exports = class IntegrationService extends cds.ApplicationService {
  init() {
    this.on('getSalesOrderFromS4', async (req) => {
      const result = await getSalesOrder(req.data.salesOrderId);
      return JSON.stringify(result);
    });

    this.on('createSalesOrderInS4', async (req) => {
      const { soldToParty, salesOrganization, material, quantity } = req.data;
      const result = await createSalesOrder({ soldToParty, salesOrganization, material, quantity });
      return JSON.stringify(result);
    });

    this.on('analyzeSalesOrderText', async (req) => {
      const result = await analyzeText(req.data.text);
      return JSON.stringify(result);
    });

    this.on('triggerCpiFlow', async (req) => {
      const payload = JSON.parse(req.data.payloadJson);
      const result = await triggerIntegrationFlow(payload);
      return JSON.stringify(result);
    });

    this.on('startApprovalWorkflow', async (req) => {
      const result = await startApprovalProcess('sales-order-approval', { orderId: req.data.salesOrderId });
      return JSON.stringify(result);
    });

    this.on('notifyN8n', async (req) => {
      const payload = JSON.parse(req.data.payloadJson);
      const result = await triggerWorkflow(req.data.webhookPath, payload);
      return JSON.stringify(result);
    });

    return super.init();
  }
};

/*
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why does this file JSON.stringify() every result instead of
   returning objects directly?
A: The actions in integration-service.cds declare `returns String`
   (a deliberate simplification, see that file's header) — CAP's
   OData layer needs the handler's return value to match the
   declared type, so a plain object would either fail or be
   coerced unpredictably; stringifying makes the contract explicit.
   A production version would declare proper `type` structures.

Q: Why put the actual HTTP-calling logic in separate client files
   (ai_python_api_client.js, etc.) instead of inline in these
   handlers?
A: Testability and reuse — each client file works standalone (you
   can unit test analyzeText() without spinning up the whole CAP
   service) and could be reused by a DIFFERENT service or a
   scheduled job, not just this one action.

Q: This service exposes six UNBOUND actions rather than tying them
   to specific entities (like SalesOrders.confirm in the sibling
   ../capm_fiori_hana_sample/ template) — why the different style?
A: These are integration/orchestration operations, not CRUD
   operations on a specific business object CAP itself owns —
   there's no natural "entity" here to bind them to. Bound actions
   make sense when the operation acts ON a specific row (confirm
   THIS order); unbound actions make sense for operations that
   just... do something (call this API, start this workflow).

Q: How would you actually connect this to the OTHER sample —
   e.g. call startApprovalWorkflow automatically when a SalesOrder
   from ../capm_fiori_hana_sample/ is confirmed?
A: That CAP service's sales-service.js 'confirm' handler could call
   `await cds.connect.to('IntegrationService').send('startApprovalWorkflow',
   {salesOrderId: order.ID})` — CAP services can call each other
   the same way external services are called, since they're both
   just `cds.Service` instances under the hood.
------------------------------------------------------------
*/
