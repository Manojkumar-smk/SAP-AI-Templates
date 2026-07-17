*============================================================
* WRAPPER IMPLEMENTATION — the ONLY place BAPI_SALESORDER_
* CREATEFROMDAT2 is actually called from
*============================================================
* Use this when: implementing zif_wrap_bapi_salesorder. All the
* "old ABAP" (BAPI structures, CALL FUNCTION, classic BAPIRET2
* message handling) is quarantined here — the RAP saver class
* that calls this wrapper never sees any of it, only the clean
* interface signature.
*============================================================
CLASS zcl_wrap_bapi_salesorder DEFINITION
  PUBLIC
  FINAL
  CREATE PRIVATE.

  PUBLIC SECTION.
    INTERFACES zif_wrap_bapi_salesorder.

    CLASS-METHODS create_instance
      RETURNING VALUE(result) TYPE REF TO zif_wrap_bapi_salesorder.

ENDCLASS.

CLASS zcl_wrap_bapi_salesorder IMPLEMENTATION.

  METHOD create_instance.
    result = NEW zcl_wrap_bapi_salesorder( ).
  ENDMETHOD.

  METHOD zif_wrap_bapi_salesorder~create_sales_order.

    DATA: ls_header  TYPE bapisdhd1,
          ls_headerx TYPE bapisdhd1x,
          lt_items   TYPE TABLE OF bapisditm,
          lt_itemsx  TYPE TABLE OF bapisditmx,
          lt_partners TYPE TABLE OF bapiparnr,
          lt_return  TYPE TABLE OF bapiret2,
          lv_salesdocument TYPE bapivbeln-vbeln.

    ls_header = VALUE #(
      doc_type       = 'OR'
      sales_org      = is_header-sales_organization
      distr_chan     = is_header-distribution_channel
      division       = is_header-division
      purch_no_c     = is_header-purchase_order_by_cust
      req_date_h     = is_header-requested_delivery_date ).
    ls_headerx = VALUE #(
      updateflag     = 'I'
      doc_type       = abap_true
      sales_org      = abap_true
      distr_chan     = abap_true
      division       = abap_true
      purch_no_c     = abap_true
      req_date_h     = abap_true ).

    lt_partners = VALUE #(
      ( partn_role = 'AG'  "-- sold-to party
        partn_numb = is_header-sold_to_party ) ).

    lt_items = VALUE #(
      ( itm_number = '000010'
        material   = is_item-material
        target_qty = is_item-order_quantity
        target_qu  = is_item-quantity_unit ) ).
    lt_itemsx = VALUE #(
      ( itm_number = '000010'
        updateflag = 'I'
        material   = abap_true
        target_qty = abap_true
        target_qu  = abap_true ) ).

    CALL FUNCTION 'BAPI_SALESORDER_CREATEFROMDAT2'
      EXPORTING
        order_header_in  = ls_header
        order_header_inx = ls_headerx
      IMPORTING
        salesdocument    = lv_salesdocument
      TABLES
        return           = lt_return
        order_items_in   = lt_items
        order_items_inx  = lt_itemsx
        order_partners   = lt_partners.

    " -----------------------------------------------------------
    " Classic BAPI pattern: check the RETURN table for errors
    " (type 'E'/'A') BEFORE deciding whether to commit. This BAPI,
    " like most classic BAPIs, does its own updates via
    " CALL FUNCTION ... IN UPDATE TASK internally — nothing is
    " actually persisted to the database until a caller explicitly
    " triggers BAPI_TRANSACTION_COMMIT, which is why that call
    " below is required and is NOT the same thing as a forbidden
    " raw "COMMIT WORK" in RAP strict-mode code (see this method's
    " caller, zbp_i_salesorderrap.clas.abap's save_modified, for
    " why this specific call IS allowed there).
    " -----------------------------------------------------------
    DATA(has_error) = xsdbool( line_exists( lt_return[ type = 'E' ] )
                             OR line_exists( lt_return[ type = 'A' ] ) ).

    IF has_error = abap_false.
      CALL FUNCTION 'BAPI_TRANSACTION_COMMIT'
        EXPORTING
          wait = abap_true.

      ev_success     = abap_true.
      ev_sales_order = lv_salesdocument.
      ev_message     = |Sales order { lv_salesdocument } created successfully|.
      " NetAmount/Currency: a real implementation would re-read the
      " created order (BAPI_SALESORDER_GETSTATUS or a follow-up
      " READ against I_SalesOrder) to get the S/4-calculated
      " pricing — omitted here to keep the wrapper focused on the
      " create+commit mechanics this template is teaching.
      ev_net_value   = 0.
      ev_currency    = 'USD'.
    ELSE.
      CALL FUNCTION 'BAPI_TRANSACTION_ROLLBACK'.

      ev_success = abap_false.
      ev_message = COND #(
        WHEN lt_return IS NOT INITIAL
        THEN |{ lt_return[ 1 ]-id }{ lt_return[ 1 ]-number }: { lt_return[ 1 ]-message }|
        ELSE 'BAPI_SALESORDER_CREATEFROMDAT2 failed with no message' ).
    ENDIF.

  ENDMETHOD.

ENDCLASS.

*----------------------------------------------------------------
* INTERVIEW POINTS
*----------------------------------------------------------------
* Q: Why CREATE PRIVATE + a separate factory class instead of just
*    letting callers do "NEW zcl_wrap_bapi_salesorder( )" directly?
* A: Two reasons commonly given in Clean Core guidance: (1) it lets
*    the factory be the SINGLE released/whitelisted entry point —
*    you release zcl_wrap_bapi_salesorder_fac's create_instance()
*    and the interface, but the concrete implementation class
*    itself can remain un-released, giving you room to swap
*    implementations later (e.g. point at a different BAPI, or a
*    released RAP interface, without changing the release
*    contract). (2) it's a testability seam — a unit test can
*    inject a test-double from a DIFFERENT factory method without
*    touching production wiring.
*
* Q: Is calling BAPI_TRANSACTION_COMMIT here actually compliant
*    with RAP strict(2) mode's "no explicit COMMIT WORK" rule?
* A: Yes, with an important nuance: strict mode forbids YOUR CODE
*    issuing a raw COMMIT WORK / ROLLBACK WORK statement directly,
*    because that would prematurely end the RAP-managed SAP LUW
*    outside the framework's control. BAPI_TRANSACTION_COMMIT is
*    different — it's the SAP-standard, BAPI-protocol-compliant way
*    to finalize updates queued by CALL FUNCTION ... IN UPDATE TASK
*    (which classic BAPIs use internally), and calling it from
*    within the SAVE SEQUENCE (specifically inside save_modified,
*    which the RAP framework invokes AT the point it expects your
*    custom persistence to finalize) is the officially sanctioned
*    pattern for exactly this BAPI-wrapping scenario. Calling it
*    from anywhere OUTSIDE the save sequence (e.g. from an action
*    in the interaction phase) would still be wrong.
*----------------------------------------------------------------
