/*
============================================================
FORMATTER — status/priority text-to-color mapping
============================================================
Use this when: a value needs to drive a UI control's semantic
color/icon but the mapping (e.g. "Done" -> green) isn't something
an OData type with formatOptions can express — per SAPUI5
guidelines, this is exactly the case where a hand-written formatter
is the right tool, rather than reaching for one by default.
Referenced from XML views via `core:require` (see TaskList.view.xml)
rather than a global reference — see that file's header comment.
============================================================
*/
sap.ui.define([], () => {
  "use strict";

  return {
    /**
     * @param {string} sStatus - "Open" | "In Progress" | "Done"
     * @returns {string} a sap.ui.core.ValueState string
     */
    statusState(sStatus) {
      switch (sStatus) {
        case "Done": return "Success";
        case "In Progress": return "Warning";
        case "Open": return "Information";
        default: return "None";
      }
    },

    /**
     * @param {string} sPriority - "Low" | "Medium" | "High"
     * @returns {string} a sap.ui.core.ValueState string
     */
    priorityState(sPriority) {
      switch (sPriority) {
        case "High": return "Error";
        case "Medium": return "Warning";
        case "Low": return "Success";
        default: return "None";
      }
    }
  };
});
