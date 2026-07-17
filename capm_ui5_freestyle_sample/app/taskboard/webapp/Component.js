/*
============================================================
COMPONENT.JS — the app's entry point
============================================================
Use this when: every freestyle UI5 app needs exactly one of these.
`metadata: { manifest: "json" }` tells UI5 to load manifest.json
as the single source of truth for models, routing, and
dependencies — everything declared there (the OData model, the
router, the i18n ResourceModel) is created automatically; this file
only adds what CAN'T be declared in JSON: the device model (needs
the live `sap/ui/Device` singleton) and explicitly starting the
router.
============================================================
*/
sap.ui.define([
  "sap/ui/core/UIComponent",
  "sap/ui/Device",
  "./model/models"
], (UIComponent, Device, models) => {
  "use strict";

  return UIComponent.extend("sap.capire.taskboard.ui.Component", {
    metadata: {
      manifest: "json"
    },

    init() {
      // call the base component's init function
      UIComponent.prototype.init.apply(this, arguments);

      // set the device model — device orientation/size info used by
      // views for responsive behavior, kept in its own named model
      // so it never collides with the "" (default OData) model.
      this.setModel(models.createDeviceModel(), "device");

      // enable routing — MUST be called explicitly; declaring
      // "routing" in manifest.json only CONFIGURES the router, it
      // doesn't start it.
      this.getRouter().initialize();
    }
  });
});

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why is the device model set up in JS instead of manifest.json's
   declarative "models" section, like the OData and i18n models are?
A: manifest.json's model factory only knows how to construct models
   from serializable JSON config (a dataSource URI, a bundle name,
   etc.) — `sap/ui/Device` is a live, already-instantiated JS
   object reflecting the CURRENT browser/device, not something a
   JSON descriptor can describe. Anything that needs actual runtime
   JS logic to construct has to be wired up in Component.js's init().
------------------------------------------------------------*/
