// ============================================================
// Data Model — every conversation turn is persisted here.
// This is the ONLY place in the whole project that writes to
// HANA — the Python AI Core service is deliberately stateless
// (see ai_core_service/hana_db.py comments).
// ============================================================

namespace assistant;

using { cuid, managed } from '@sap/cds/common';

entity Conversation : cuid, managed {
    userID : String;                         // owner — set from the logged-in XSUAA user
    title  : String;
    to_messages : Composition of many Message on to_messages.conversation = $self;
}

entity Message : cuid, managed {
    conversation : Association to Conversation;
    role         : String;                   // "user" | "assistant"
    content      : LargeString;
    mode         : String;                   // "CHAT" | "RAG" | "SQL" | "ORCHESTRATE"
}

// One row per S/4HANA posting triggered by the assistant — an audit trail
// separate from the chat transcript, so "what did the AI actually post?"
// is always answerable independently of the conversation log.
entity PostingLog : cuid, managed {
    conversation   : Association to Conversation;
    customer       : String;
    material       : String;
    quantity       : Integer;
    s4hana_order_id : String;                // the Sales Order number returned by the RAP OData action
    status         : String;                 // "SUCCESS" | "FAILED"
    error_message  : String;
}
