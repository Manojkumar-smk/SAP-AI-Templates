*============================================================
* BEHAVIOR IMPLEMENTATION CLASS — UNMANAGED scenario
*============================================================
* Use this when: implementing full hand-written CRUD. Contrast
* directly against ../rap_managed_fiori/zbp_i_product.clas.abap —
* every method here that was EMPTY there now has real logic:
*   - create/update/delete (lhc_) stage into a manual buffer
*     instead of doing nothing.
*   - save (lsc_) contains real INSERT/UPDATE/DELETE against
*     ztcustomer instead of being empty.
*
* THE KEY MECHANIC: gt_create / gt_update / gt_delete are declared
* as CLASS-DATA (static) in the PUBLIC SECTION of lhc_customer.
* Static class attributes persist for the lifetime of the class
* pool within one request/LUW — that's what lets data staged by
* lhc_customer's interaction-phase methods (create/update/delete,
* called potentially several times as the user works) survive to
* be read by lsc_customer's SAVE method later in the SAME request,
* even though lhc_ and lsc_ are separate classes.
*============================================================
CLASS lhc_customer DEFINITION INHERITING FROM cl_abap_behavior_handler.
  PUBLIC SECTION.
    "-- shared "transactional buffer" — see file header note above.
    "-- lsc_customer's SAVE method reads these directly via
    "-- lhc_customer=>gt_create etc.
    CLASS-DATA gt_create TYPE TABLE FOR CREATE zi_customer.
    CLASS-DATA gt_update TYPE TABLE FOR UPDATE zi_customer.
    CLASS-DATA gt_delete TYPE TABLE FOR DELETE zi_customer.

  PRIVATE SECTION.
    METHODS get_instance_authorizations FOR INSTANCE AUTHORIZATION
      IMPORTING keys REQUEST requested_authorizations FOR Customer RESULT result.

    METHODS validateEmail FOR VALIDATE ON SAVE
      IMPORTING keys FOR Customer~validateEmail.

    METHODS create FOR MODIFY
      IMPORTING entities FOR CREATE Customer.

    METHODS update FOR MODIFY
      IMPORTING entities FOR UPDATE Customer.

    METHODS delete FOR MODIFY
      IMPORTING keys FOR DELETE Customer.

    METHODS read FOR READ
      IMPORTING keys FOR READ Customer RESULT result.

    METHODS lock FOR LOCK
      IMPORTING keys FOR LOCK Customer.

ENDCLASS.

CLASS lhc_customer IMPLEMENTATION.

  METHOD get_instance_authorizations.
    result = VALUE #( FOR key IN keys
      ( %tky    = key-%tky
        %update = if_abap_behv=>auth-allowed
        %delete = if_abap_behv=>auth-allowed ) ).
  ENDMETHOD.

  METHOD validateEmail.
    " -------------------------------------------------------
    " Reads from OUR OWN buffer first (a record just created in
    " this same request hasn't hit the DB yet, so SELECT alone
    " would miss it), falling back to the DB for existing records.
    " -------------------------------------------------------
    DATA customers TYPE TABLE FOR READ RESULT zi_customer.

    LOOP AT keys INTO DATA(key).
      READ TABLE gt_create WITH KEY %tky = key-%tky
        INTO DATA(buffered) CASE SENSITIVE.
      IF sy-subrc = 0.
        APPEND CORRESPONDING #( buffered ) TO customers.
      ELSE.
        SELECT SINGLE * FROM ztcustomer
          WHERE customer_uuid = @key-CustomerUUID
          INTO CORRESPONDING FIELDS OF @DATA(db_row).
        APPEND VALUE #( %tky = key-%tky CustomerEmail = db_row-customer_email ) TO customers.
      ENDIF.
    ENDLOOP.

    LOOP AT customers INTO DATA(customer)
      WHERE CustomerEmail NOT CS '@' OR CustomerEmail IS INITIAL.
      APPEND VALUE #( %tky = customer-%tky ) TO failed-customer.
      APPEND VALUE #( %tky = customer-%tky
                       %msg = new_message_with_text(
                                 severity = if_abap_behv_message=>severity-error
                                 text     = |Customer email '{ customer-CustomerEmail }' looks invalid| )
                       %element-customeremail = if_abap_boolean=>true
                     ) TO reported-customer.
    ENDLOOP.
  ENDMETHOD.

  METHOD create.
    " -------------------------------------------------------
    " INTERACTION PHASE — NO DATABASE WRITE HAPPENS HERE.
    " We: (1) generate the technical key now (early numbering —
    " simpler than the late-numbering %pid pattern used in
    " ../rap_bapi_posting_fiori/, appropriate here because we
    " don't depend on an external system to hand us the real key),
    " (2) stage the full row into gt_create, (3) tell the framework
    " the %cid → %key mapping via `mapped` so the UI's optimistic
    " "just-created" row resolves to a real key immediately.
    " -------------------------------------------------------
    LOOP AT entities INTO DATA(entity).
      DATA(new_customer) = CORRESPONDING ztcustomer( entity MAPPING FROM ENTITY ).
      new_customer-customer_uuid = cl_system_uuid=>create_uuid_x16_static( ).

      APPEND CORRESPONDING #( new_customer ) TO gt_create ASSIGNING FIELD-SYMBOL(<staged>).
      <staged>-%cid = entity-%cid.
      <staged>-%tky-CustomerUUID = new_customer-customer_uuid.
      <staged>-CustomerUUID = new_customer-customer_uuid.

      APPEND VALUE #( %cid = entity-%cid
                       %key = VALUE #( CustomerUUID = new_customer-customer_uuid ) )
             TO mapped-customer.
    ENDLOOP.
  ENDMETHOD.

  METHOD update.
    " -------------------------------------------------------
    " Merge incoming (partial) changes with the CURRENT row so the
    " buffered record staged for SAVE is always a COMPLETE row —
    " this keeps the SAVE method's UPDATE statement simple (no
    " dynamic field lists needed).
    " -------------------------------------------------------
    LOOP AT entities INTO DATA(entity).
      SELECT SINGLE * FROM ztcustomer
        WHERE customer_uuid = @entity-CustomerUUID
        INTO @DATA(existing).

      DATA(merged) = existing.
      IF entity-%control-CustomerName    = if_abap_behv=>mk-on. merged-customer_name  = entity-CustomerName.  ENDIF.
      IF entity-%control-CustomerEmail   = if_abap_behv=>mk-on. merged-customer_email = entity-CustomerEmail. ENDIF.
      IF entity-%control-CustomerPhone   = if_abap_behv=>mk-on. merged-customer_phone = entity-CustomerPhone. ENDIF.
      IF entity-%control-CreditLimit     = if_abap_behv=>mk-on. merged-credit_limit   = entity-CreditLimit.   ENDIF.
      IF entity-%control-Currency        = if_abap_behv=>mk-on. merged-currency       = entity-Currency.      ENDIF.
      IF entity-%control-IsBlocked       = if_abap_behv=>mk-on. merged-is_blocked     = entity-IsBlocked.     ENDIF.

      APPEND CORRESPONDING #( merged ) TO gt_update ASSIGNING FIELD-SYMBOL(<staged>).
      <staged>-%tky = entity-%tky.
    ENDLOOP.
  ENDMETHOD.

  METHOD delete.
    LOOP AT keys INTO DATA(key).
      APPEND VALUE #( %tky = key-%tky ) TO gt_delete.
    ENDLOOP.
  ENDMETHOD.

  METHOD read.
    " -------------------------------------------------------
    " The RAP framework only calls READ for instances NOT already
    " sitting in ITS OWN internal transactional buffer — so a
    " record just created earlier in this same request is served
    " back to the UI without this method being called again. This
    " method only ever has to handle "existing, previously saved"
    " rows, so a plain SELECT is sufficient.
    " -------------------------------------------------------
    SELECT * FROM ztcustomer
      FOR ALL ENTRIES IN @keys
      WHERE customer_uuid = @keys-CustomerUUID
      INTO TABLE @DATA(db_rows).

    result = VALUE #( FOR row IN db_rows
      ( %tky               = VALUE #( CustomerUUID = row-customer_uuid )
        CustomerUUID        = row-customer_uuid
        CustomerID           = row-customer_id
        CustomerName          = row-customer_name
        CustomerEmail         = row-customer_email
        CustomerPhone         = row-customer_phone
        CreditLimit           = row-credit_limit
        Currency              = row-currency
        IsBlocked              = row-is_blocked
        CreatedBy               = row-created_by
        CreatedAt                = row-created_at
        LastChangedBy             = row-last_changed_by
        LastChangedAt              = row-last_changed_at
        LocalLastChangedAt          = row-local_last_changed_at ) ).
  ENDMETHOD.

  METHOD lock.
    " -------------------------------------------------------
    " "lock master" in the BDEF requires a hand-written enqueue.
    " In a real system, generate a lock object (SE11/ADT → Lock
    " Object → ZCUSTOMER_L on ztcustomer's key) and call its
    " generated ENQUEUE_/DEQUEUE_ function modules here. Shown as
    " a documented call rather than a runnable FM invocation since
    " the lock object itself is a separate DDIC artifact this
    " template doesn't include.
    " -------------------------------------------------------
    LOOP AT keys INTO DATA(key).
      CALL FUNCTION 'ENQUEUE_ZCUSTOMER_L'
        EXPORTING
          customer_uuid  = key-CustomerUUID
        EXCEPTIONS
          foreign_lock   = 1
          system_failure = 2
          OTHERS         = 3.
      IF sy-subrc <> 0.
        APPEND VALUE #( %tky = key-%tky ) TO failed-customer.
      ENDIF.
    ENDLOOP.
  ENDMETHOD.

ENDCLASS.


*============================================================
* SAVER CLASS — real INSERT/UPDATE/DELETE against ztcustomer
*============================================================
CLASS lsc_customer DEFINITION INHERITING FROM cl_abap_behavior_saver.
  PROTECTED SECTION.
    METHODS finalize REDEFINITION.
    METHODS check_before_save REDEFINITION.
    METHODS save REDEFINITION.
    METHODS cleanup REDEFINITION.
    METHODS cleanup_finalize REDEFINITION.
ENDCLASS.

CLASS lsc_customer IMPLEMENTATION.

  METHOD finalize.
    " Stamp administrative/ETag fields on everything staged for
    " create or update — this is the framework's job in MANAGED
    " (via @Semantics annotations alone); here WE must set it.
    DATA(now) = utclong_current( ).
    LOOP AT lhc_customer=>gt_create ASSIGNING FIELD-SYMBOL(<c>).
      <c>-CreatedBy            = cl_abap_context_info=>get_user_technical_name( ).
      <c>-CreatedAt             = now.
      <c>-LastChangedBy          = <c>-CreatedBy.
      <c>-LastChangedAt           = now.
      <c>-LocalLastChangedAt        = now.
    ENDLOOP.
    LOOP AT lhc_customer=>gt_update ASSIGNING FIELD-SYMBOL(<u>).
      <u>-LastChangedBy  = cl_abap_context_info=>get_user_technical_name( ).
      <u>-LastChangedAt   = now.
      <u>-LocalLastChangedAt = now.
    ENDLOOP.
  ENDMETHOD.

  METHOD check_before_save.
    " Cross-entity / cross-buffer checks needing the FULL picture
    " (all creates+updates+deletes together) would go here — e.g.
    " "you cannot delete the last remaining Customer for a given
    " SalesOrganization". Not needed for this template.
  ENDMETHOD.

  METHOD save.
    " -------------------------------------------------------
    " THIS is the method that does NOT exist (is empty) in the
    " managed template. Every statement below is exactly the SQL
    " the RAP framework would have auto-generated FOR you under
    " "managed" — here, you write it explicitly.
    " -------------------------------------------------------
    IF lhc_customer=>gt_create IS NOT INITIAL.
      INSERT ztcustomer FROM TABLE @( CORRESPONDING #( lhc_customer=>gt_create MAPPING FROM ENTITY ) ).
    ENDIF.

    IF lhc_customer=>gt_update IS NOT INITIAL.
      UPDATE ztcustomer FROM TABLE @( CORRESPONDING #( lhc_customer=>gt_update MAPPING FROM ENTITY ) ).
    ENDIF.

    IF lhc_customer=>gt_delete IS NOT INITIAL.
      DELETE ztcustomer FROM TABLE @( VALUE #( FOR d IN lhc_customer=>gt_delete
                                                ( customer_uuid = d-CustomerUUID ) ) ).
    ENDIF.
  ENDMETHOD.

  METHOD cleanup.
    " Called if the save sequence is ABORTED partway through
    " (e.g. a parallel entity's check_before_save failed) — release
    " anything acquired outside the DB (locks handled separately by
    " the framework calling your LOCK method's inverse automatically
    " at commit/rollback, so usually nothing extra needed here).
  ENDMETHOD.

  METHOD cleanup_finalize.
    " Runs after a SUCCESSFUL save — reset our static buffers so
    " the NEXT request (new LUW) starts clean. Skipping this is a
    " classic unmanaged-RAP bug: stale data from a previous request
    " leaking into the next one via the CLASS-DATA buffer.
    CLEAR: lhc_customer=>gt_create, lhc_customer=>gt_update, lhc_customer=>gt_delete.
  ENDMETHOD.

ENDCLASS.

*----------------------------------------------------------------
* INTERVIEW POINTS
*----------------------------------------------------------------
* Q: Why stamp CreatedAt/LastChangedAt in FINALIZE rather than
*    directly in the create/update handler methods?
* A: FINALIZE runs once, immediately before the save sequence
*    starts committing — guaranteeing the timestamp reflects the
*    moment of SAVE, not the moment the user happened to start
*    editing (which could be minutes earlier if they left the
*    Object Page open). It also centralizes this cross-cutting
*    concern in one place instead of duplicating it in create AND
*    update.
*
* Q: What's the single most common bug in a hand-rolled unmanaged
*    BO like this one?
* A: Forgetting CLEANUP_FINALIZE — if the static gt_create/
*    gt_update/gt_delete buffers aren't cleared after a successful
*    save, the NEXT unrelated request in the same work process can
*    pick up leftover rows and either duplicate-insert them or
*    silently resave stale data. This is exactly the kind of bug
*    that's invisible in a quick manual test (one user, one
*    request at a time) and only shows up under concurrent load —
*    a good thing to mention proactively in an interview.
*
* Q: The UPDATE method does a SELECT SINGLE against the DB inside
*    the INTERACTION phase — is a database READ allowed there, when
*    WRITES aren't?
* A: Yes. RAP's "no DB writes in the interaction phase" rule is
*    specifically about WRITES — reads are unrestricted anywhere
*    (interaction phase, save sequence, validations). That's what
*    makes it safe for a validation method to SELECT for a
*    business check, and safe for this UPDATE handler to fetch the
*    current row to merge partial changes.
*----------------------------------------------------------------
