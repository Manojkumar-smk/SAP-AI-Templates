//============================================================
// PROJECTION VIEW — what Fiori / OData actually consumes
//============================================================
@AccessControl.authorizationCheck: #INHERIT
@EndUserText.label: 'Sales Order Posting - Consumption Projection'
@Metadata.allowExtensions: true
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.semanticKey: ['SalesOrderRapUUID']
define root view entity zc_salesorderrap
  provider contract transactional_query
  as projection on zi_salesorderrap
{
  key SalesOrderRapUUID,
      SalesOrder,
      SoldToParty,
      SalesOrganization,
      DistributionChannel,
      Division,
      PurchaseOrderByCustomer,
      RequestedDeliveryDate,
      Material,
      OrderQuantity,
      QuantityUnit,
      NetAmount,
      Currency,
      OverallStatus,
      PostingMessage,
      CreatedBy,
      CreatedAt,
      LastChangedBy,
      LastChangedAt,
      LocalLastChangedAt
}
