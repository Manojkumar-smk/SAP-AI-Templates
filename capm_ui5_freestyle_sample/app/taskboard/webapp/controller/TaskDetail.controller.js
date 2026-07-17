/*
============================================================
TASK DETAIL CONTROLLER — the "Object Page" equivalent, hand-coded
============================================================
Use this when: implementing a freestyle detail/edit screen bound to
ONE entity, with an explicit Save/Cancel (rather than Fiori
elements' built-in draft handling — see ../capm_fiori_hana_sample/
for that alternative). The manual-save mechanic here uses a NAMED,
DEFERRED update group ("taskDetailGroup", declared in manifest.json's
groupProperties) — changes made via two-way bindings on this view's
inputs are held client-side until Save calls submitBatch().
============================================================
*/
sap.ui.define([
  "./BaseController",
  "sap/m/MessageToast",
  "sap/m/MessageBox"
], (BaseController, MessageToast, MessageBox) => {
  "use strict";

  return BaseController.extend("sap.capire.taskboard.ui.controller.TaskDetail", {

    onInit() {
      this.getRouter().getRoute("detail").attachPatternMatched(this._onPatternMatched, this);
    },

    _onPatternMatched(oEvent) {
      const sTaskId = oEvent.getParameter("arguments").taskId;
      // Edm.Guid key predicates are UNQUOTED in OData V4 URL syntax
      // (unlike Edm.String, which needs single quotes) — this
      // entity's ID comes from the CAP `cuid` aspect, which is a
      // UUID/Edm.Guid, so no quoting here.
      this.getView().bindElement({
        path: `/Tasks(${sTaskId})`,
        parameters: { $$updateGroupId: "taskDetailGroup" }
      });
    },

    async onSave() {
      const oModel = this.getModel();
      try {
        await oModel.submitBatch("taskDetailGroup");
        MessageToast.show(this.getResourceBundle().getText("taskUpdatedMessage"));
      } catch (oError) {
        MessageBox.error(oError.message || this.getResourceBundle().getText("errorGenericMessage"));
      }
    },

    onCancel() {
      // Discards every pending change queued in this deferred group
      // — the bound Inputs/Select/DatePicker snap back to the
      // last-known server values automatically, no manual reset of
      // each field needed.
      this.getModel().resetChanges("taskDetailGroup");
    },

    async onComplete() {
      const oContext = this.getView().getBindingContext();
      // BOUND action: bindContext's 2nd argument is the entity
      // CONTEXT the action operates on — contrast with
      // TaskList.controller.js's onResetDemoData(), which calls an
      // UNBOUND action with no context argument at all.
      const oOperation = this.getModel().bindContext(
        "TaskService.complete(...)",
        oContext,
        { $$groupId: "$auto" }
      );
      try {
        await oOperation.execute();
        MessageToast.show(this.getResourceBundle().getText("taskCompletedMessage"));
      } catch (oError) {
        MessageBox.error(oError.message || this.getResourceBundle().getText("errorGenericMessage"));
      }
    },

    onDelete() {
      const oContext = this.getView().getBindingContext();
      const sTitle = oContext.getProperty("title");
      MessageBox.confirm(
        this.getResourceBundle().getText("deleteConfirmMessage", [sTitle]),
        {
          title: this.getResourceBundle().getText("deleteConfirmTitle"),
          onClose: (sAction) => {
            if (sAction === MessageBox.Action.OK) {
              // Context#delete() — v4 model's own delete, sends the
              // OData DELETE request and removes the row from any
              // bound list once it succeeds.
              oContext.delete()
                .then(() => {
                  MessageToast.show(this.getResourceBundle().getText("taskDeletedMessage"));
                  this.getRouter().navTo("list", {}, true);
                })
                .catch((oError) => {
                  MessageBox.error(oError.message || this.getResourceBundle().getText("errorGenericMessage"));
                });
            }
          }
        }
      );
    }
  });
});

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why give the update group its own $$groupId ("taskDetailGroup")
   instead of just using the model's default "$auto" group for
   this form too?
A: "$auto" submits every change to the server IMMEDIATELY (as soon
   as a bound Input's change event fires) — fine for isolated
   single-field edits, but wrong for a form with a Save/Cancel
   pair: the user expects nothing to actually persist until Save is
   pressed, and Cancel needs something to discard. A named DEFERRED
   group ("submit": "API" in manifest.json) is what makes changes
   sit client-side until you explicitly call submitBatch()/
   resetChanges() — this is the freestyle-UI5 equivalent of what
   Fiori elements' built-in draft handling gives you automatically.

Q: onComplete uses `$$groupId: "$auto"` for the action call — why
   NOT the same "taskDetailGroup" as the rest of the form?
A: "Complete" is meant to fire immediately when clicked (it's an
   explicit, single action, not a field edit that should wait for a
   batch Save) — using "$auto" submits it right away, independent
   of whatever unsaved edits might still be sitting in
   "taskDetailGroup". Mixing them would mean clicking Complete could
   accidentally also submit unrelated pending field edits (or vice
   versa, silently defer the completion) — keeping them in separate
   groups makes each button's behavior predictable in isolation.
------------------------------------------------------------*/
