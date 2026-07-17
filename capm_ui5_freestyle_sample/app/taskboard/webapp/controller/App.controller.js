sap.ui.define([
  "./BaseController",
  "sap/ui/model/json/JSONModel"
], (BaseController, JSONModel) => {
  "use strict";

  return BaseController.extend("sap.capire.taskboard.ui.controller.App", {
    onInit() {
      // "appView" — a small UI-state-only model (busy indicator
      // etc.), deliberately separate from the "" OData model and
      // any per-screen "newTask" scratch models, so its lifecycle
      // (lives for the whole app) is never confused with a
      // screen's own transient state.
      const oAppViewModel = new JSONModel({
        busy: false,
        delay: 0
      });
      this.setModel(oAppViewModel, "appView");
    }
  });
});
