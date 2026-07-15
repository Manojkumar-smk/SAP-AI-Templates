"""
============================================================
MINI TEMPLATE — Conversation History Module
============================================================
Use this when: you're building a multi-turn chat and need the
model to remember earlier turns.

Key concept — Orchestration is STATELESS:
  Every `.run()` call is independent. SAP AI Core does not keep
  a session for you. To get multi-turn memory, YOUR app must
  collect prior messages and resend them as `messages_history`
  on every subsequent call.

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python conversation_history_module.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage, AssistantMessage
from gen_ai_hub.orchestration.models.llm import LLM
from gen_ai_hub.orchestration.models.config import OrchestrationConfig

from orchestration_setup import get_orchestration_service


class ConversationBuffer:
    """
    Minimal in-memory turn tracker. Swap this for Redis / a DB table
    per user session in a real multi-user app — this class alone does
    NOT persist across process restarts.
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns   # cap history so token usage doesn't grow unbounded
        self.history: list = []      # list of SystemMessage/UserMessage/AssistantMessage

    def add_user(self, text: str):
        self.history.append(UserMessage(text))
        self._trim()

    def add_assistant(self, text: str):
        self.history.append(AssistantMessage(text))
        self._trim()

    def _trim(self):
        # Keep only the most recent N turns (2 messages per turn: user + assistant)
        max_messages = self.max_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def reset(self):
        self.history = []


def ask(orchestration_service, buffer: ConversationBuffer, system_prompt: str, user_text: str) -> str:
    """
    Sends one turn, including all prior turns as messages_history,
    then records both sides of the exchange into the buffer.
    """
    template = Template(messages=[
        SystemMessage(system_prompt),
        UserMessage("{{?text}}"),
    ])
    config = OrchestrationConfig(template=template, llm=LLM(name="gpt-4o-mini"))

    result = orchestration_service.run(
        config=config,
        template_values=[TemplateValue(name="text", value=user_text)],
        messages_history=buffer.history,   # ← this is what gives the illusion of memory
    )

    answer = result.orchestration_result.choices[0].message.content
    buffer.add_user(user_text)
    buffer.add_assistant(answer)
    return answer


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()
    buffer = ConversationBuffer(max_turns=10)
    system_prompt = "You are a helpful SAP technical assistant. Keep answers short."

    turns = [
        "My name is Priya and I work on the AI Core team.",
        "What's my name?",                       # tests memory of turn 1
        "What team do I work on?",                # tests memory of turn 1
    ]

    for turn in turns:
        print(f"User: {turn}")
        reply = ask(orchestration_service, buffer, system_prompt, turn)
        print(f"Bot:  {reply}\n")


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Does the Orchestration Service store conversation state on SAP's
   side?
A: No. It is stateless per-request. The calling application is fully
   responsible for tracking and resending message history.

Q: Why cap conversation history instead of sending the full
   transcript every time?
A: Token cost grows with every turn resent; capping (a sliding window,
   as in ConversationBuffer._trim) bounds cost/latency at the expense
   of the model "forgetting" very old turns. Production systems often
   summarize older turns instead of dropping them outright.

Q: Where would you persist ConversationBuffer.history in a real
   multi-user web app?
A: Keyed by session/user ID in Redis, a database table, or (for
   short-lived sessions) server-side session storage — never in a
   plain in-memory Python list shared across requests/users, which
   would leak one user's history into another's.

Q: How does messages_history interact with the Template's own
   placeholder messages?
A: messages_history is prepended as prior conversational turns; the
   Template's messages (System + the current placeholder-filled
   UserMessage) represent the NEW turn being asked right now.
------------------------------------------------------------
"""
