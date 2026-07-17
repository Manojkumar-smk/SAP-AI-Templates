//============================================================
// PROJECTION VIEW — what Fiori / OData actually consumes
//============================================================
@AccessControl.authorizationCheck: #INHERIT
@EndUserText.label: 'Customer - Consumption Projection'
@Metadata.allowExtensions: true
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.semanticKey: ['CustomerID']
define root view entity zc_customer
  provider contract transactional_query
  as projection on zi_customer
{
  key CustomerUUID,
      CustomerID,
      CustomerName,
      CustomerEmail,
      CustomerPhone,
      CreditLimit,
      Currency,
      IsBlocked,
      CreatedBy,
      CreatedAt,
      LastChangedBy,
      LastChangedAt,
      LocalLastChangedAt
}
