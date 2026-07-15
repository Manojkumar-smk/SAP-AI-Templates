sap.ui.define(["sap/ui/core/UIComponent"], function (UIComponent) {
    "use strict";
    // Standard CAP/UI5 freestyle bootstrap — reads manifest.json,
    // wires up the OData V4 model declared there as the "" (default) model.
    return UIComponent.extend("assistant.ui.Component", {
        metadata: { manifest: "json" },
    });
});
