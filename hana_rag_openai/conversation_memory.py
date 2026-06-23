"""
============================================================
MINI TEMPLATE — Conversation Memory for RAG
============================================================
Use this when: you need multi-turn conversational RAG where
the LLM remembers previous questions and answers.

Without memory: each call is independent — "it" or "that"
in follow-up questions won't resolve to anything.

With memory: the last N conversation turns are passed to
the prompt as {chat_history} so the LLM understands context.

Built on: LangChain ConversationBufferWindowMemory

Setup:
  pip install langchain
============================================================
"""

from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import HumanMessage, AIMessage


class ChatMemory:
    """
    Wraps LangChain ConversationBufferWindowMemory for RAG conversations.

    Usage:
        memory = ChatMemory(window=5)

        memory.save("What is HANA?", "SAP HANA is an in-memory database...")
        memory.save("What are its key features?", "HANA supports vector search, PAL...")

        history_str = memory.get_history_string()
        # Use history_str as {chat_history} in CONVERSATIONAL_RAG_PROMPT

        memory.clear()  # start a new session
    """

    def __init__(self, window: int = 5):
        """
        Args:
            window : number of recent conversation turns to keep (default: 5)
                     Older turns are automatically dropped.
        """
        self._memory = ConversationBufferWindowMemory(
            k=window,
            return_messages=True
        )
        self.window = window
        print(f"✅ ChatMemory initialized (window={window} turns)")

    def save(self, user_input: str, ai_output: str) -> None:
        """
        Save one conversation turn (question + answer) to memory.

        Args:
            user_input : what the user asked
            ai_output  : what the assistant answered
        """
        self._memory.save_context(
            {"input": user_input},
            {"output": ai_output}
        )

    def get_messages(self) -> list:
        """Return raw LangChain message objects (HumanMessage / AIMessage)."""
        return self._memory.load_memory_variables({})["history"]

    def get_history_string(self) -> str:
        """
        Return chat history as a formatted string for prompt injection.

        Example:
            User: What is HANA?
            Assistant: SAP HANA is an in-memory database...
            User: What are its features?
            Assistant: HANA supports vector search, PAL...
        """
        messages = self.get_messages()
        if not messages:
            return "No previous conversation."

        lines = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                lines.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                lines.append(f"Assistant: {msg.content}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset conversation history (start a new session)."""
        self._memory.clear()
        print("🗑️  Conversation memory cleared.")

    def turn_count(self) -> int:
        """Return number of turns currently in memory."""
        return len(self.get_messages()) // 2


if __name__ == "__main__":
    memory = ChatMemory(window=3)

    # Simulate a conversation
    turns = [
        ("What is SAP HANA?",          "SAP HANA is a cloud-native in-memory database."),
        ("What makes it fast?",         "It stores data in RAM rather than on disk."),
        ("Does it support vectors?",    "Yes, HANA Cloud has a native Vector Engine."),
        ("What similarity function?",   "HANA uses COSINE_SIMILARITY for vector search."),
    ]

    for question, answer in turns:
        memory.save(question, answer)
        print(f"\nSaved turn {memory.turn_count()}: '{question[:40]}'")

    print("\n── Current History (last 3 turns) ────")
    print(memory.get_history_string())

    memory.clear()
    print(f"\nAfter clear — turns in memory: {memory.turn_count()}")
