/*
============================================================
EXTERNAL SERVICE MODEL — S/4HANA Sales Order API (trimmed)
============================================================
Use this when: you need to READ/CREATE Sales Orders in S/4HANA
(on-prem via SAP Gateway, or S/4HANA Cloud) from a CAP service.

IMPORTANT — this file is a HAND-TRIMMED, representative
reproduction of what `cds import` generates, kept small on
purpose for readability. The REAL workflow is:

  1. Download the service's $metadata document. From S/4HANA
     Cloud's API Business Hub: https://api.sap.com/api/API_SALES_ORDER_SRV
     → "API Specification" tab → download the .edmx file.
     From an on-prem system: GET .../sap/opu/odata/sap/API_SALES_ORDER_SRV/$metadata

  2. Run the import:
       cds import ./API_SALES_ORDER_SRV.edmx --as cds
     This creates srv/external/API_SALES_ORDER_SRV.csn (the REAL,
     COMPLETE model — every entity, every field, all ~50+ fields
     on A_SalesOrder alone) and registers an entry in package.json's
     cds.requires automatically.

  3. Delete/replace this hand-written file with the generated one.

This trimmed version keeps only the fields this template's demo
code actually touches, to keep the annotated example readable.
Verified: compiles cleanly with `cds compile` as valid CDS syntax
using the exact @cds.external / @cds.external.name pattern `cds
import` produces — but is NOT a substitute for importing your
system's real metadata.
============================================================
*/

@cds.external
service API_SALES_ORDER_SRV {

  @cds.external.name: 'A_SalesOrder'
  entity A_SalesOrder {
    key SalesOrder            : String(10);
        SalesOrderType         : String(4);
        SalesOrganization      : String(4);
        SoldToParty            : String(10);
        TotalNetAmount         : Decimal(15,2);
        TransactionCurrency    : String(5);
        OverallSDProcessStatus : String(1);
        to_Item : Association to many API_SALES_ORDER_SRV.A_SalesOrderItem
                     on to_Item.SalesOrder = SalesOrder;
  }

  @cds.external.name: 'A_SalesOrderItem'
  entity A_SalesOrderItem {
    key SalesOrder       : String(10);
    key SalesOrderItem    : String(6);
        Material           : String(40);
        RequestedQuantity  : Decimal(13,3);
        NetAmount          : Decimal(15,2);
  }
}
