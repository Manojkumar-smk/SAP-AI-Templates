/*
============================================================
SERVICE — Ties every external client into callable CAP actions
============================================================
Use this when: you want ONE OData/REST entry point your own Fiori
app (or another service) can call, which internally fans out to
the external systems in this folder — clients don't need to know
S/4HANA, CPI, BPA, and n8n exist behind these actions.

Simplified action signatures using String for demo payloads — a
production service would use proper typed structures/aspects
instead of stringified JSON in/out (kept as strings here so the
whole file — and the curl examples in USER_MANUAL.md — stay easy
to read without a wall of nested type definitions).

Verified: compiled with `cds compile` and actually run — see
integration-service.js's header for the exact verified request.
============================================================
*/

service IntegrationService @(path: '/integration') {

  action getSalesOrderFromS4(salesOrderId: String)
    returns String;

  action createSalesOrderInS4(soldToParty: String, salesOrganization: String,
                               material: String, quantity: Decimal)
    returns String;

  action analyzeSalesOrderText(text: String)
    returns String;

  action triggerCpiFlow(payloadJson: String)
    returns String;

  action startApprovalWorkflow(salesOrderId: String)
    returns String;

  action notifyN8n(webhookPath: String, payloadJson: String)
    returns String;
}
