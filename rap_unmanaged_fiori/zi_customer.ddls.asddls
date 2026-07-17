//============================================================
// INTERFACE VIEW (root view entity) — UNMANAGED
//============================================================
// Use this when: same role as ../rap_managed_fiori/zi_product.ddls
// — this view's SHAPE doesn't differ for managed vs unmanaged.
// What differs is what happens NEXT: this view's Behavior
// Definition will say "unmanaged" instead of "managed", meaning
// the framework will call YOUR create/update/delete/read/lock
// methods for every single operation instead of generating SQL.
//============================================================

@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Customer - Interface View'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType: {
  serviceQuality: #X,
  sizeCategory: #S,
  dataClass: #MIXED
}
define root view entity zi_customer
  as select from ztcustomer
{
  key customer_uuid           as CustomerUUID,
      customer_id              as CustomerID,
      customer_name             as CustomerName,
      customer_email            as CustomerEmail,
      customer_phone            as CustomerPhone,
      @Semantics.amount.currencyCode: 'Currency'
      credit_limit              as CreditLimit,
      @Semantics.currencyCode: true
      currency                  as Currency,
      is_blocked                 as IsBlocked,

      @Semantics.user.createdBy: true
      created_by                 as CreatedBy,
      @Semantics.systemDateTime.createdAt: true
      created_at                 as CreatedAt,
      @Semantics.user.localInstanceLastChangedBy: true
      last_changed_by            as LastChangedBy,
      @Semantics.systemDateTime.localInstanceLastChangedAt: true
      last_changed_at            as LastChangedAt,
      @Semantics.systemDateTime.lastChangedAt: true
      local_last_changed_at      as LocalLastChangedAt

}

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Could this exact CDS view be reused by BOTH a managed and an
   unmanaged behavior definition, in two different scenarios?
A: Structurally yes — the view is just a SELECT. In practice you
   wouldn't: a real project picks ONE implementation type per BO
   and commits to it, because the behavior definition + handler
   class you write depend entirely on that choice. But it's a
   useful thing to say out loud in an interview: managed/unmanaged
   is a BEHAVIOR-layer decision, not a DATA-MODEL-layer one.
------------------------------------------------------------*/
