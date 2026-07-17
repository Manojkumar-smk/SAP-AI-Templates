*============================================================
* WRAPPER INTERFACE — Clean Core boundary around a classic BAPI
*============================================================
* Use this when: you need to call a NON-RELEASED classic BAPI
* (BAPI_SALESORDER_CREATEFROMDAT2 is not on the ABAP Cloud released
* API list) from strict(2) ABAP Cloud code, which is FORBIDDEN to
* call it directly. The standard, SAP-recommended workaround is:
* wrap the BAPI call inside your own class implementing your own
* interface, then get THAT wrapper class released/whitelisted for
* Cloud development (via the "Release Contract" tooling in ADT, or
* a customer-owned released API for on-prem/private-cloud). Your
* strict-mode RAP code then only ever touches ZIF_WRAP_BAPI_
* SALESORDER — a boundary YOU own and control — never the BAPI
* directly.
*
* This interface + its implementation (zcl_wrap_bapi_salesorder)
* + factory (zcl_wrap_bapi_salesorder_fac) together form the
* standard three-piece "BAPI wrapper" pattern for RAP + Clean Core.
*============================================================
INTERFACE zif_wrap_bapi_salesorder
  PUBLIC.

  TYPES: BEGIN OF ty_header,
           sold_to_party            TYPE char10,
           sales_organization       TYPE char4,
           distribution_channel     TYPE char2,
           division                 TYPE char2,
           purchase_order_by_cust   TYPE char20,
           requested_delivery_date  TYPE dats,
         END OF ty_header.

  TYPES: BEGIN OF ty_item,
           material         TYPE char18,
           order_quantity   TYPE p LENGTH 13 DECIMALS 3,
           quantity_unit    TYPE unit,
         END OF ty_item.

  METHODS create_sales_order
    IMPORTING
      is_header          TYPE ty_header
      is_item             TYPE ty_item
    EXPORTING
      ev_sales_order       TYPE char10
      ev_net_value          TYPE p LENGTH 15 DECIMALS 2
      ev_currency            TYPE waers
      ev_success              TYPE abap_boolean
      ev_message               TYPE string.

ENDINTERFACE.
