/*
============================================================
SERVICE — exposes Tasks to the UI5 freestyle app
============================================================
Use this when: contrast this file directly with
../capm_fiori_hana_sample/srv/sales-service.cds — that service adds
Fiori-elements-oriented annotations (UI.LineItem etc. live in a
SEPARATE app/*.cds file there). Here, there are NO UI annotations
at all, anywhere in this template — a freestyle UI5 app builds its
own views by hand, so the service only needs to describe DATA and
BEHAVIOR, never presentation.
============================================================
*/

using { sap.capire.taskboard as db } from '../db/schema';

service TaskService @(path: '/odata/v4/task') {

  entity Tasks as projection on db.Tasks actions {
    // Bound action — completes a task in one call instead of the
    // client having to PATCH status itself. Demonstrates calling
    // an OData V4 bound action from freestyle UI5 (see
    // TaskDetail.controller.js's onComplete handler).
    action complete() returns Tasks;
  };

  // Unbound action — bulk-resets demo data status, handy for
  // repeatedly demoing the app without re-seeding from csv.
  action resetDemoData() returns String;
}
