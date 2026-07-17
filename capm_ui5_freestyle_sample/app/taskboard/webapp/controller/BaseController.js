/*
============================================================
BASE CONTROLLER — shared helpers every screen controller extends
============================================================
Use this when: avoiding copy-pasting the same
getOwnerComponent().getRouter() / getModel() boilerplate into every
controller. This is a plain (non-UI) JS class with no view of its
own — App/TaskList/TaskDetail controllers extend it instead of
sap.ui.core.mvc.Controller directly.
============================================================
*/
sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "sap/ui/core/routing/History"
], (Controller, History) => {
  "use strict";

  return Controller.extend("sap.capire.taskboard.ui.controller.BaseController", {

    getRouter() {
      return this.getOwnerComponent().getRouter();
    },

    getModel(sName) {
      return this.getView().getModel(sName);
    },

    setModel(oModel, sName) {
      this.getView().setModel(oModel, sName);
      return this;
    },

    getResourceBundle() {
      return this.getOwnerComponent().getModel("i18n").getResourceBundle();
    },

    onNavBack() {
      const oHistory = History.getInstance();
      const sPreviousHash = oHistory.getPreviousHash();
      if (sPreviousHash !== undefined) {
        window.history.go(-1);
      } else {
        this.getRouter().navTo("list", {}, true);
      }
    }
  });
});
