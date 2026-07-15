sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageToast",
], function (Controller, JSONModel, MessageToast) {
    "use strict";

    return Controller.extend("assistant.ui.controller.App", {

        onInit: function () {
            // Local chat transcript for THIS browser session — the real, durable
            // transcript lives in HANA via the Conversation/Message entities,
            // this JSONModel just drives the on-screen list.
            this.getView().setModel(new JSONModel({ messages: [] }), "local");
            this._conversationId = "";
        },

        onSend: async function () {
            const oInput = this.byId("messageInput");
            const sMessage = oInput.getValue().trim();
            if (!sMessage) return;

            const oLocalModel = this.getView().getModel("local");
            const aMessages = oLocalModel.getProperty("/messages");
            aMessages.push({ role: "You", content: sMessage });
            oLocalModel.setProperty("/messages", aMessages);
            oInput.setValue("");

            // Calls AssistantService.askAssistant(...) — the ONE action that
            // drives the whole flow (AI Core call + HANA persistence + optional
            // S/4HANA posting) on the CAP side. See srv/assistant-service.js.
            const oModel = this.getView().getModel();          // the OData V4 model from manifest.json
            const oAction = oModel.bindContext("/askAssistant(...)");
            oAction.setParameter("conversationId", this._conversationId);
            oAction.setParameter("message", sMessage);

            try {
                await oAction.execute();
                const oResult = oAction.getBoundContext().getObject();

                this._conversationId = oResult.conversationId;   // carry forward for the next turn
                aMessages.push({ role: "Assistant", content: oResult.answer });
                oLocalModel.setProperty("/messages", aMessages);

                if (oResult.postedToS4Hana) {
                    MessageToast.show(`Posted to S/4HANA — Sales Order ${oResult.s4hanaOrderId}`);
                }
            } catch (oError) {
                MessageToast.show("Assistant call failed: " + oError.message);
            }
        },
    });
});
