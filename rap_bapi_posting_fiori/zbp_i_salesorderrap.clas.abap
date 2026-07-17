*============================================================
* BEHAVIOR IMPLEMENTATION CLASS — MANAGED WITH UNMANAGED SAVE
*============================================================
* Use this when: implementing the hybrid pattern. Compare the
* class SHAPE against the other two templates:
*   ../rap_managed_fiori/zbp_i_product.clas.abap    → lsc_ has
*     FIVE separate empty methods (finalize/check_before_save/
*     save/cleanup/cleanup_finalize).
*   ../rap_unmanaged_fiori/zbp_i_customer.clas.abap → lsc_ has
*     those SAME five methods, all hand-written.
*   THIS file  → lsc_ has exactly ONE method, save_modified,
*     because "with unmanaged save" collapses the whole save
*     sequence into a single override point. There is also NO
*     create/update FOR MODIFY method in lhc_ — the framework still
*     handles interaction-phase buffering (that's the "managed"
*     half of the hybrid); only validation and the retryPosting
*     action are hand-written here, same as a plain managed BO.
*
* IMPORTANT CAVEAT: save_modified's exact parameter/component names
* (create-salesorderrap, update-salesorderrap, %pid, mapped-
* salesorderrap) are FRAMEWORK-GENERATED based on your entity
* alias — ADT scaffolds the precise signature when you create this
* class from the BDEF's activation quick-fix. Treat the method
* BODY logic below as the reference pattern to follow; verify the
* exact generated signature/type names against what ADT scaffolds
* in your own system before compiling.
*============================================================
CLASS lhc_salesorderrap DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PRIVATE SECTION.

    METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION
      IMPORTING keys REQUEST requested_authorizations FOR SalesOrderRap RESULT result.

    METHODS validateMandatoryData FOR VALIDATE ON SAVE
      IMPORTING keys FOR SalesOrderRap~validateMandatoryData.

    METHODS retryPosting FOR MODIFY
      IMPORTING keys FOR ACTION SalesOrderRap~retryPosting RESULT result.

ENDCLASS.

CLASS lhc_salesorderrap IMPLEMENTATION.

  METHOD get_instance_authorizations.
    result = VALUE #( FOR key IN keys
      ( %tky                    = key-%tky
        %action-retryPosting    = if_abap_behv=>auth-allowed ) ).
  ENDMETHOD.

  METHOD validateMandatoryData.
    READ ENTITIES OF zi_salesorderrap IN LOCAL MODE
      ENTITY SalesOrderRap
        FIELDS ( SoldToParty SalesOrganization Material OrderQuantity )
        WITH CORRESPONDING #( keys )
      RESULT DATA(orders).

    LOOP AT orders INTO DATA(order) WHERE OrderQuantity <= 0.
      APPEND VALUE #( %tky = order-%tky ) TO failed-salesorderrap.
      APPEND VALUE #( %tky = order-%tky
                       %msg = new_message_with_text(
                                 severity = if_abap_behv_message=>severity-error
                                 text     = 'Order quantity must be greater than zero' )
                       %element-orderquantity = if_abap_boolean=>true
                     ) TO reported-salesorderrap.
    ENDLOOP.
  ENDMETHOD.

  METHOD retryPosting.
    " -------------------------------------------------------
    " retryPosting does NOT call the BAPI wrapper directly — actions
    " run in the INTERACTION phase, and this BO's whole design
    " point is that only save_modified is allowed to touch the
    " external system. So this action's ONLY job is to mark the
    " instance as "changed" (touching OverallStatus back to blank)
    " so that the framework includes it in save_modified's `update`
    " parameter on the NEXT save — save_modified then re-runs the
    " exact same posting logic used for a fresh create.
    " -------------------------------------------------------
    MODIFY ENTITIES OF zi_salesorderrap IN LOCAL MODE
      ENTITY SalesOrderRap
        UPDATE FIELDS ( OverallStatus PostingMessage )
        WITH VALUE #( FOR key IN keys
          ( %tky            = key-%tky
            OverallStatus   = ' '
            PostingMessage  = 'Retry queued...' ) )
      FAILED   DATA(failed_retry)
      REPORTED DATA(reported_retry).

    failed   = CORRESPONDING #( DEEP failed_retry ).
    reported = CORRESPONDING #( DEEP reported_retry ).

    READ ENTITIES OF zi_salesorderrap IN LOCAL MODE
      ENTITY SalesOrderRap
        ALL FIELDS WITH CORRESPONDING #( keys )
      RESULT DATA(retried_orders).

    result = VALUE #( FOR o IN retried_orders
                       ( %tky = o-%tky %param = o ) ).
  ENDMETHOD.

ENDCLASS.


*============================================================
* SAVER CLASS — save_modified is where the BAPI is actually called
*============================================================
CLASS lsc_salesorderrap DEFINITION INHERITING FROM cl_abap_behavior_saver.
  PROTECTED SECTION.
    METHODS save_modified REDEFINITION.
ENDCLASS.

CLASS lsc_salesorderrap IMPLEMENTATION.

  METHOD save_modified.

    " ===========================================================
    " CREATE — first-time posting of a new sales order to S/4
    " ===========================================================
    IF create-salesorderrap IS NOT INITIAL.
      LOOP AT create-salesorderrap INTO DATA(new_order).

        DATA(wrapper) = zcl_wrap_bapi_salesorder_fac=>create_instance( ).

        wrapper->create_sales_order(
          EXPORTING
            is_header = VALUE #(
              sold_to_party           = new_order-SoldToParty
              sales_organization      = new_order-SalesOrganization
              distribution_channel    = new_order-DistributionChannel
              division                = new_order-Division
              purchase_order_by_cust  = new_order-PurchaseOrderByCustomer
              requested_delivery_date = new_order-RequestedDeliveryDate )
            is_item = VALUE #(
              material       = new_order-Material
              order_quantity = new_order-OrderQuantity
              quantity_unit  = new_order-QuantityUnit )
          IMPORTING
            ev_sales_order = DATA(lv_sales_order)
            ev_net_value   = DATA(lv_net_value)
            ev_currency    = DATA(lv_currency)
            ev_success     = DATA(lv_success)
            ev_message     = DATA(lv_message) ).

        " -- THIS is the "unmanaged" half of "managed with unmanaged
        " -- save": we write the persistence SQL by hand, because the
        " -- outcome (sales_order/overall_status/posting_message) is
        " -- only known AFTER calling an external system, which the
        " -- framework's auto-generated SQL could never do.
        UPDATE ztsalesorderbuf SET
            sales_order     = @lv_sales_order
            overall_status  = @COND #( WHEN lv_success = abap_true THEN 'A' ELSE 'E' )
            posting_message = @lv_message
            net_amount      = @lv_net_value
            currency        = @lv_currency
          WHERE salesorderrap_uuid = @new_order-SalesOrderRapUUID.

        " -- LATE NUMBERING RESOLUTION — resolves the entity's
        " -- preliminary identity (%pid, assigned when the draft row
        " -- was first created client-side) to its final key, now
        " -- that we know the create attempt's outcome. Required
        " -- because "late numbering;" is set in zi_salesorderrap.
        " -- bdef.asbdef — see that file's interview points.
        CONVERT KEY OF zi_salesorderrap
          FROM new_order-%pid
          TO DATA(ls_final_key).

        mapped-salesorderrap = VALUE #( BASE mapped-salesorderrap
          ( %pid = new_order-%pid
            %key = ls_final_key ) ).

      ENDLOOP.
    ENDIF.

    " ===========================================================
    " UPDATE — reached via the retryPosting action (see lhc_
    " above), which marks a previously-failed row as changed so it
    " lands here on the next save. Same posting logic, re-run.
    " ===========================================================
    IF update-salesorderrap IS NOT INITIAL.
      LOOP AT update-salesorderrap INTO DATA(retry_order).

        SELECT SINGLE * FROM ztsalesorderbuf
          WHERE salesorderrap_uuid = @retry_order-SalesOrderRapUUID
          INTO @DATA(existing_row).

        DATA(retry_wrapper) = zcl_wrap_bapi_salesorder_fac=>create_instance( ).

        retry_wrapper->create_sales_order(
          EXPORTING
            is_header = VALUE #(
              sold_to_party           = existing_row-sold_to_party
              sales_organization      = existing_row-sales_organization
              distribution_channel    = existing_row-distribution_channel
              division                = existing_row-division
              purchase_order_by_cust  = existing_row-purchase_order_by_customer
              requested_delivery_date = existing_row-requested_delivery_date )
            is_item = VALUE #(
              material       = existing_row-material
              order_quantity = existing_row-order_quantity
              quantity_unit  = existing_row-quantity_unit )
          IMPORTING
            ev_sales_order = DATA(lv_sales_order2)
            ev_net_value   = DATA(lv_net_value2)
            ev_currency    = DATA(lv_currency2)
            ev_success     = DATA(lv_success2)
            ev_message     = DATA(lv_message2) ).

        UPDATE ztsalesorderbuf SET
            sales_order     = @lv_sales_order2
            overall_status  = @COND #( WHEN lv_success2 = abap_true THEN 'A' ELSE 'E' )
            posting_message = @lv_message2
            net_amount      = @lv_net_value2
            currency        = @lv_currency2
          WHERE salesorderrap_uuid = @retry_order-SalesOrderRapUUID.

      ENDLOOP.
    ENDIF.

  ENDMETHOD.

ENDCLASS.

*----------------------------------------------------------------
* INTERVIEW POINTS
*----------------------------------------------------------------
* Q: What happens if BAPI_SALESORDER_CREATEFROMDAT2 fails — does
*    the whole RAP save sequence roll back?
* A: No, and that's deliberate. save_modified catches the failure
*    (ev_success = abap_false) and writes OverallStatus = 'E' PLUS
*    the BAPI's error message into our own ztsalesorderbuf row —
*    the RAP save sequence itself still completes successfully
*    (the "record of the attempt" IS successfully saved, even
*    though the attempt it records was a failure). The user sees a
*    saved row with a red status and a message, and can hit "Retry
*    Posting". If you wanted a FAILED BAPI call to actually fail
*    the whole RAP save (rejecting the record entirely), you'd
*    instead APPEND to `failed-salesorderrap` and `reported-
*    salesorderrap` inside save_modified — a legitimate alternative
*    design choice worth mentioning as a trade-off in an interview.
*
* Q: Why does CONVERT KEY happen even for the FAILURE path (a
*    row that didn't get a real SalesOrder number)?
* A: CONVERT KEY resolves the RAP ENTITY's own technical identity
*    (SalesOrderRapUUID, already known from the moment the row was
*    created client-side) — it is NOT tied to whether the BAPI
*    succeeded. The framework needs SOME final key for every row in
*    `create`, success or failure, so the UI can address it
*    afterward (e.g. to show the error and offer Retry). What
*    changes based on success/failure is only the BUSINESS field
*    SalesOrder (blank on failure) — a completely separate concern
*    from the RAP entity key.
*----------------------------------------------------------------
