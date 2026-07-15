"""
============================================================
SIMPLE PROJECT — Orchestration Agent (CLI)
============================================================
Use this when: you want to RUN a working chatbot right now
that exercises every module in this folder, wired together
by orchestration_pipeline.py + conversation_history_module.py.

This is the "connect all the pieces" entry point for the whole
folder — same role that sap_chatbot/cli_runner.py plays for the
DIY-RAG templates, but every module here (masking, filtering,
grounding, structured output) runs INSIDE the SAP AI Core
orchestration deployment instead of in hand-written Python.

Commands during chat:
  /mode <name>   → switch mode: general | grounded | strict
  /history       → print the conversation so far
  /reset         → clear conversation memory
  /quit          → exit

Modes:
  general   → templating + LLM only (no masking/filtering/grounding)
  grounded  → adds document grounding (needs a data repository set up)
  strict    → adds data masking + content filtering (safest for PII)

Setup:
  pip install "sap-ai-sdk-gen[all]" python-dotenv
  python orchestration_agent.py
============================================================
"""

from gen_ai_hub.orchestration.models.template import Template, TemplateValue
from gen_ai_hub.orchestration.models.message import SystemMessage, UserMessage
from gen_ai_hub.orchestration.models.config import OrchestrationConfig

from orchestration_setup import get_orchestration_service
from llm_module import build_llm
from content_filtering_module import build_filtering, STRICT_FILTER
from data_masking_module import build_masking
from document_grounding_module import build_grounding
from gen_ai_hub.orchestration.models.document_grounding import DocumentGrounding
from gen_ai_hub.orchestration.models.sap_data_privacy_integration import MaskingMethod, ProfileEntity
from conversation_history_module import ConversationBuffer


SYSTEM_PROMPT = (
    "You are a helpful SAP AI Core assistant. Be concise and professional."
)


class OrchestrationAgent:
    """
    Ties together templating + LLM + (optional) masking/filtering/
    grounding + conversation memory behind one simple `.ask()` call —
    the orchestration-module equivalent of sap_chatbot/chatbot_core.py.
    """

    def __init__(self, orchestration_service, mode: str = "general", memory_window: int = 10):
        self.orchestration_service = orchestration_service
        self.mode = mode
        self.buffer = ConversationBuffer(max_turns=memory_window)

    def _build_config(self) -> OrchestrationConfig:
        use_grounding = self.mode == "grounded"
        use_safety = self.mode == "strict"

        user_message = "Question: {{?text}}\nContext: {{?groundingOutput}}" if use_grounding else "{{?text}}"
        template = Template(messages=[SystemMessage(SYSTEM_PROMPT), UserMessage(user_message)])

        kwargs = {"template": template, "llm": build_llm(model="gpt-4o-mini", temperature=0.2)}

        if use_safety:
            kwargs["data_masking"] = build_masking(
                method=MaskingMethod.PSEUDONYMIZATION,
                entities=[ProfileEntity.PERSON, ProfileEntity.EMAIL, ProfileEntity.PHONE],
            )
            kwargs["filtering"] = build_filtering(input_filter=STRICT_FILTER, output_filter=STRICT_FILTER)

        if use_grounding:
            kwargs["grounding"] = DocumentGrounding(
                module_config=build_grounding(input_placeholder="text", output_placeholder="groundingOutput")
            )

        return OrchestrationConfig(**kwargs)

    def ask(self, user_text: str) -> str:
        config = self._build_config()
        try:
            result = self.orchestration_service.run(
                config=config,
                template_values=[TemplateValue(name="text", value=user_text)],
                messages_history=self.buffer.history,
            )
            answer = result.orchestration_result.choices[0].message.content
            self.buffer.add_user(user_text)
            self.buffer.add_assistant(answer)
            return answer
        except Exception as e:
            return f"⚠️ Request blocked or failed ({self.mode} mode): {e}"

    def reset(self):
        self.buffer.reset()

    def set_mode(self, mode: str):
        if mode not in ("general", "grounded", "strict"):
            raise ValueError("mode must be one of: general, grounded, strict")
        self.mode = mode
        self.reset()   # switching modes starts a fresh conversation


def run_cli(agent: OrchestrationAgent):
    print(f"\n{'=' * 60}")
    print("  SAP AI Core — Orchestration Agent")
    print(f"  Mode: {agent.mode} | Memory: {agent.buffer.max_turns} turns")
    print(f"{'=' * 60}")
    print("Commands: /mode <general|grounded|strict> | /history | /reset | /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "/quit":
            print("Goodbye!")
            break
        if user_input.lower() == "/reset":
            agent.reset()
            print("Bot: Conversation cleared.\n")
            continue
        if user_input.lower() == "/history":
            for msg in agent.buffer.history:
                print(f"  {type(msg).__name__}: {getattr(msg, 'content', msg)}")
            print()
            continue
        if user_input.lower().startswith("/mode"):
            parts = user_input.split()
            if len(parts) == 2:
                try:
                    agent.set_mode(parts[1])
                    print(f"Bot: Switched to '{agent.mode}' mode (conversation reset).\n")
                except ValueError as e:
                    print(f"Bot: {e}\n")
            else:
                print("Usage: /mode general|grounded|strict\n")
            continue

        answer = agent.ask(user_input)
        print(f"Bot [{agent.mode}]: {answer}\n")


if __name__ == "__main__":
    orchestration_service = get_orchestration_service()
    agent = OrchestrationAgent(orchestration_service, mode="general")
    run_cli(agent)


"""
------------------------------------------------------------
🎯 INTERVIEW POINTS
------------------------------------------------------------
Q: Why does set_mode() reset the conversation buffer?
A: Each mode uses a different OrchestrationConfig (different template
   placeholders — "grounded" mode expects a groundingOutput placeholder
   that "general" mode's template never fills). Carrying history built
   under one template into a differently-shaped template risks
   placeholder mismatches, so starting fresh is the safer default.

Q: How is this file different from orchestration_pipeline.py?
A: orchestration_pipeline.py demonstrates BUILDING a full config and
   running it once. orchestration_agent.py wraps that same pattern in
   a class with state (conversation memory, mode switching) and a
   runnable CLI loop — this is the "simple project" you'd actually
   hand to a user, mirroring sap_chatbot/cli_runner.py.

Q: Why is error handling in `.ask()` a caught exception returning a
   string, rather than letting it propagate?
A: A CLI/chat UI should degrade gracefully — a blocked/filtered
   request is an expected outcome (not a bug), so the user sees a
   clear message instead of a crash.

Q: How would you turn this into a Streamlit app like
   sample_project_sapgenai/app.py?
A: Same pattern as that file — cache an OrchestrationAgent instance
   with st.cache_resource, keep history in st.session_state instead of
   the class-level buffer, and call agent.ask() from a st.chat_input
   callback.
------------------------------------------------------------
"""
