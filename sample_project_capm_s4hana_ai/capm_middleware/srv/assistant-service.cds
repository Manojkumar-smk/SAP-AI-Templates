// ============================================================
// Service Definition — what the UI5 app is allowed to call.
// One action (askAssistant) covers the whole "ask a question,
// maybe post to S/4HANA" flow. Conversation/Message are exposed
// read-only so the UI5 app can show conversation history.
// ============================================================

using assistant from '../db/schema';

service AssistantService @(requires: 'authenticated-user') {

    @readonly
    entity Conversation @(restrict: [
        { grant: ['READ'], where: 'userID = $user' }        // users only see their own conversations
    ]) as projection on assistant.Conversation;

    @readonly
    entity PostingLog as projection on assistant.PostingLog;

    // The single entry point UI5 calls for every user message.
    action askAssistant(
        conversationId : String,     // empty string = start a new conversation
        message        : String
    ) returns AssistantResult;
}

type AssistantResult {
    conversationId  : String;
    answer          : String;
    mode            : String;
    postedToS4Hana  : Boolean;
    s4hanaOrderId   : String;
}
