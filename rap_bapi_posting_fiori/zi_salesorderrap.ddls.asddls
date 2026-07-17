//============================================================
// INTERFACE VIEW (root view entity)
//============================================================
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Sales Order Posting - Interface View'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory: #S,
  dataClass: #TRANSACTIONAL
}
define root view entity zi_salesorderrap
  as select from ztsalesorderbuf
{
  key salesorderrap_uuid          as SalesOrderRapUUID,
      sales_order                  as SalesOrder,
      sold_to_party                 as SoldToParty,
      sales_organization             as SalesOrganization,
      distribution_channel            as DistributionChannel,
      division                         as Division,
      purchase_order_by_customer        as PurchaseOrderByCustomer,
      requested_delivery_date            as RequestedDeliveryDate,
      material                            as Material,
      order_quantity                       as OrderQuantity,
      quantity_unit                         as QuantityUnit,
      @Semantics.amount.currencyCode: 'Currency'
      net_amount                             as NetAmount,
      @Semantics.currencyCode: true
      currency                                as Currency,
      overall_status                           as OverallStatus,
      posting_message                           as PostingMessage,

      @Semantics.user.createdBy: true
      created_by                                 as CreatedBy,
      @Semantics.systemDateTime.createdAt: true
      created_at                                  as CreatedAt,
      @Semantics.user.localInstanceLastChangedBy: true
      last_changed_by                              as LastChangedBy,
      @Semantics.systemDateTime.localInstanceLastChangedAt: true
      last_changed_at                               as LastChangedAt,
      @Semantics.systemDateTime.lastChangedAt: true
      local_last_changed_at                          as LocalLastChangedAt

}

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: SalesOrder (the real S/4 document number) is a plain non-key
   field here, not part of the entity's key — why?
A: The entity's KEY (SalesOrderRapUUID) has to exist and be stable
   from the moment the user starts creating the record — long
   before the real SalesOrder number exists. If SalesOrder were the
   key, the entity would have NO valid key during the entire
   interaction phase, which RAP doesn't allow. Keeping them separate
   is exactly what makes "late numbering" of the BUSINESS number
   possible while the TECHNICAL key stays assignable up front.
------------------------------------------------------------*/
