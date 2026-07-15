// ============================================================
// Service Implementation — the orchestrator of the whole project.
// One action, four steps, every time it's called:
//   1. Call the Python AI Core service (/api/orchestrate)
//   2. Persist the user message + AI answer to HANA (CQL)
//   3. If the AI detected a "post a sales order" intent,
//      call the S/4HANA RAP-based OData action to actually post it
//   4. Return one combined result to the UI5 app
// ============================================================

const cds = require('@sap/cds');
const { v4: uuidv4 } = require('uuid');

module.exports = cds.service.impl(async function () {
    const { Conversation, Message, PostingLog } = this.entities;

    // Two outbound connections, both destination-backed (see package.json's
    // cds.requires) — CAP never hardcodes a URL or credential here.
    const aiCoreService = await cds.connect.to('AI_CORE_SERVICE');
    const s4hanaService = await cds.connect.to('S4HANA_SALES_API');

    this.on('askAssistant', async (req) => {
        const { message } = req.data;
        let { conversationId } = req.data;
        const userID = req.user.id;

        // ── Step 0: make sure we have a Conversation row to attach messages to ──
        if (!conversationId) {
            conversationId = uuidv4();
            await INSERT.into(Conversation).entries({ ID: conversationId, userID, title: message.slice(0, 60) });
        }

        // ── Step 1: call the Python AI Core service ──────────────────────────
        // POST {AI_CORE_SERVICE_URL}/api/orchestrate  { message }
        let aiResult;
        try {
            aiResult = await aiCoreService.send('POST', '/api/orchestrate', { message });
        } catch (err) {
            req.error(502, `AI Core service call failed: ${err.message}`);
            return;
        }

        // ── Step 2: persist BOTH sides of this turn to HANA ───────────────────
        await INSERT.into(Message).entries([
            { ID: uuidv4(), conversation_ID: conversationId, role: 'user', content: message, mode: aiResult.mode },
            { ID: uuidv4(), conversation_ID: conversationId, role: 'assistant', content: aiResult.answer, mode: aiResult.mode },
        ]);

        // ── Step 3: if this was a posting request, call the S/4HANA RAP action ──
        let postedToS4Hana = false;
        let s4hanaOrderId = '';

        if (aiResult.is_posting_intent && aiResult.posting_payload) {
            const { customer, material, quantity } = aiResult.posting_payload;
            try {
                // This calls a RAP-based OData V4 action exposed by S/4HANA —
                // e.g. a custom Sales Order Behavior Definition's "create" action.
                // RAP (RESTful ABAP Programming Model) is implemented IN ABAP on
                // the S/4HANA side; CAP only ever calls its already-published API.
                const s4Response = await s4hanaService.send('POST', '/sap/opu/odata4/sap/api_salesorder/srvd/sap/salesorder/0001/SalesOrder', {
                    SoldToParty: customer,
                    to_Item: { results: [{ Material: material, RequestedQuantity: quantity }] },
                });
                s4hanaOrderId = s4Response.SalesOrder;
                postedToS4Hana = true;

                await INSERT.into(PostingLog).entries({
                    ID: uuidv4(), conversation_ID: conversationId, customer, material, quantity,
                    s4hana_order_id: s4hanaOrderId, status: 'SUCCESS',
                });
            } catch (err) {
                await INSERT.into(PostingLog).entries({
                    ID: uuidv4(), conversation_ID: conversationId, customer, material, quantity,
                    status: 'FAILED', error_message: err.message,
                });
                // Posting failure does NOT fail the whole request — the user still
                // gets the AI's answer, just with postedToS4Hana = false.
            }
        }

        // ── Step 4: one combined result back to UI5 ───────────────────────────
        return {
            conversationId,
            answer: aiResult.answer,
            mode: aiResult.mode,
            postedToS4Hana,
            s4hanaOrderId,
        };
    });
});
