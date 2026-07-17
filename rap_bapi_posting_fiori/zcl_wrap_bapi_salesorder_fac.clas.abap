*============================================================
* FACTORY CLASS — the RELEASED entry point RAP code is allowed
* to call
*============================================================
* Use this when: obtaining an instance of the wrapper from strict
* ABAP Cloud code (e.g. zbp_i_salesorderrap.clas.abap's
* save_modified). Only THIS class + zif_wrap_bapi_salesorder need
* to go through ADT's "Release Contract" step to be legally
* callable from strict(2) code — zcl_wrap_bapi_salesorder itself
* (the implementation, with the actual BAPI call) never needs to
* be released, since callers only ever see it through the
* interface reference this factory hands back.
*============================================================
CLASS zcl_wrap_bapi_salesorder_fac DEFINITION
  PUBLIC
  FINAL
  CREATE PRIVATE.

  PUBLIC SECTION.
    CLASS-METHODS create_instance
      RETURNING VALUE(result) TYPE REF TO zif_wrap_bapi_salesorder.

ENDCLASS.

CLASS zcl_wrap_bapi_salesorder_fac IMPLEMENTATION.

  METHOD create_instance.
    result = zcl_wrap_bapi_salesorder=>create_instance( ).
  ENDMETHOD.

ENDCLASS.
