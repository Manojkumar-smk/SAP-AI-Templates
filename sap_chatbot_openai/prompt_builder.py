"""
============================================================
MINI TEMPLATE — Dynamic Prompt Builder
============================================================
Use this when: you need a chat prompt that adapts based on
which features are active (RAG context, SQL results, or both).

The prompt is built dynamically:
  - Always includes: system_prompt + chat history + user message
  - If RAG enabled:  injects {rag_context} section
  - If SQL enabled:  injects {sql_result} + {sql_used} section
  - If both:         injects all sections

This means the LLM always knows exactly what data is available.

Setup:
  pip install langchain langchain-core
============================================================
"""

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from chatbot_config import ChatbotConfig


def build_prompt(config: ChatbotConfig, has_rag: bool, has_sql: bool) -> ChatPromptTemplate:
    """
    Build a ChatPromptTemplate dynamically based on active features.

    Args:
        config  : ChatbotConfig (reads system_prompt and bot_name)
        has_rag : True if RAG context is available for this turn
        has_sql : True if SQL results are available for this turn

    Returns:
        ChatPromptTemplate ready to be chained with | llm | StrOutputParser()

    Template variables in the returned prompt:
        Always present : {history}, {user_message}
        If has_rag     : {rag_context}
        If has_sql     : {sql_result}, {sql_used}
    """
    system_parts = [config.system_prompt]

    if has_rag:
        system_parts.append(
            "\n\nYou have access to a knowledge base. "
            "Relevant context is provided below under 'KNOWLEDGE BASE CONTEXT'. "
            "Use it to answer the user's question. "
            "If the context doesn't contain the answer, say you don't have that information."
        )

    if has_sql:
        system_parts.append(
            "\n\nYou also have access to structured data from a database. "
            "Query results are provided below under 'DATABASE RESULTS'. "
            "Use them to give precise, data-backed answers."
        )

    messages = [("system", "".join(system_parts))]

    if has_rag:
        messages.append(("system", "KNOWLEDGE BASE CONTEXT:\n{rag_context}"))

    if has_sql:
        messages.append(("system", "DATABASE RESULTS (SQL: {sql_used}):\n{sql_result}"))

    # Chat history slot + user message
    messages.append(MessagesPlaceholder(variable_name="history"))
    messages.append(("human", "{user_message}"))

    return ChatPromptTemplate.from_messages(messages)


if __name__ == "__main__":
    config = ChatbotConfig(
        system_prompt = "You are a helpful SAP assistant.",
        enable_rag    = True,
        enable_sql    = True,
    )

    print("── General prompt variables ────────────")
    p = build_prompt(config, has_rag=False, has_sql=False)
    print(p.input_variables)

    print("\n── RAG prompt variables ────────────────")
    p = build_prompt(config, has_rag=True, has_sql=False)
    print(p.input_variables)

    print("\n── SQL prompt variables ────────────────")
    p = build_prompt(config, has_rag=False, has_sql=True)
    print(p.input_variables)

    print("\n── Full (RAG + SQL) prompt variables ───")
    p = build_prompt(config, has_rag=True, has_sql=True)
    print(p.input_variables)
