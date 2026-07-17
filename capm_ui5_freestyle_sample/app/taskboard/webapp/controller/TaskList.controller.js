/*
============================================================
TASK LIST CONTROLLER — the "List Report" equivalent, hand-coded
============================================================
Use this when: implementing a freestyle list screen against an
OData v4 collection. Everything a Fiori elements List Report gives
you for free (search, sort, create, navigation) is implemented
explicitly here — that verbosity IS the point of a freestyle
template: it shows exactly what Fiori elements is automating away.
============================================================
*/
sap.ui.define([
  "./BaseController",
  "sap/ui/model/json/JSONModel",
  "sap/ui/model/Filter",
  "sap/ui/model/FilterOperator",
  "sap/m/MessageToast",
  "sap/m/MessageBox"
], (BaseController, JSONModel, Filter, FilterOperator, MessageToast, MessageBox) => {
  "use strict";

  return BaseController.extend("sap.capire.taskboard.ui.controller.TaskList", {

    onInit() {
      this._oCreateDialog = null;
    },

    onTaskPress(oEvent) {
      const oItem = oEvent.getSource();
      const oContext = oItem.getBindingContext();
      const sTaskId = oContext.getProperty("ID");
      this.getRouter().navTo("detail", { taskId: sTaskId });
    },

    onSearch(oEvent) {
      // fires on both live-typing (liveChange -> "newValue") and
      // the explicit search icon/Enter (search -> "query") —
      // handling both parameter names keeps the search box
      // responsive as-you-type AND correct on explicit submit.
      const sQuery = oEvent.getParameter("newValue") ?? oEvent.getParameter("query") ?? "";
      const oBinding = this.byId("taskTable").getBinding("items");
      const aFilters = sQuery
        ? [new Filter({
            filters: [
              new Filter("title", FilterOperator.Contains, sQuery),
              new Filter("assignee", FilterOperator.Contains, sQuery)
            ],
            and: false
          })]
        : [];
      oBinding.filter(aFilters);
    },

    onRefresh() {
      this.byId("taskTable").getBinding("items").refresh();
    },

    async onCreateTask() {
      // loadFragment() is a built-in Controller helper (since UI5
      // 1.93) that instantiates + caches a fragment and connects it
      // to this controller/view — no manual sap.ui.xmlfragment() +
      // setModel()/addDependent() boilerplate needed.
      if (!this._oCreateDialog) {
        this._oCreateDialog = await this.loadFragment({
          name: "sap.capire.taskboard.ui.fragment.CreateTaskDialog"
        });
      }
      this.getView().setModel(new JSONModel({
        title: "",
        description: "",
        priority: "Medium",
        dueDate: null,
        assignee: ""
      }), "newTask");
      this._oCreateDialog.open();
    },

    onCreateTaskConfirm() {
      const oNewTask = this.getView().getModel("newTask").getData();
      if (!oNewTask.title) {
        MessageToast.show(this.getResourceBundle().getText("titleRequiredMessage"));
        return;
      }

      // ODataListBinding#create() — the v4 model's way to create a
      // new entity: it immediately inserts an optimistic row into
      // the bound Table (so the user sees it right away) and fires
      // the real POST in the background, rolling the row back if
      // the server rejects it (e.g. this template's "due date in
      // the past" check in task-service.js).
      const oListBinding = this.byId("taskTable").getBinding("items");
      oListBinding.create({
        title: oNewTask.title,
        description: oNewTask.description,
        status: "Open",
        priority: oNewTask.priority,
        dueDate: oNewTask.dueDate,
        assignee: oNewTask.assignee
      });

      this._oCreateDialog.close();
      MessageToast.show(this.getResourceBundle().getText("taskCreatedMessage"));
    },

    onCreateTaskCancel() {
      this._oCreateDialog.close();
    },

    onResetDemoData() {
      // Unbound action call: bindContext against a path with NO
      // preceding entity context, contrast with TaskDetail
      // .controller.js's onComplete(), which passes an entity
      // context as bindContext's second argument for a BOUND action.
      const oModel = this.getModel();
      const oOperation = oModel.bindContext("/resetDemoData(...)");
      oOperation.execute()
        .then(() => {
          MessageToast.show(oOperation.getBoundContext().getObject().value);
          this.byId("taskTable").getBinding("items").refresh();
        })
        .catch((oError) => {
          MessageBox.error(oError.message || this.getResourceBundle().getText("errorGenericMessage"));
        });
    }
  });
});

/*------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why bind the create dialog's inputs to a scratch "newTask"
   JSONModel instead of directly creating the OData entity and
   binding the dialog to ITS (transient) context?
A: Both are valid v4 patterns. Binding directly to a transient
   created-context is more "correct" for scenarios where you want
   the row to already exist (e.g. auto-navigating to it) even before
   the user finishes the dialog. The JSONModel-scratch approach used
   here is simpler to reason about for a basic template: NOTHING
   touches the OData model until the user commits by pressing
   Create — Cancel needs zero cleanup, since the OData model was
   never involved.

Q: `oBinding.filter(aFilters)` — does this filter CLIENT-SIDE (in
   the browser) or does it re-query the SERVER?
A: By default, v4 ODataListBinding filtering is SERVER-side: calling
   `.filter()` triggers a new OData request with a `$filter` query
   option built from the Filter objects, re-fetching only matching
   rows — it does not just hide/show already-loaded rows in the
   browser. This matters for "growing"/infinite-scroll tables like
   this one, where not all rows are even loaded client-side to
   begin with.
------------------------------------------------------------*/
