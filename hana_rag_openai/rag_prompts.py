"""
============================================================
MINI TEMPLATE — RAG Prompt Templates
============================================================
Use this when: you need to customize how the LLM is instructed
to answer questions using retrieved context.

Two prompts provided:
  1. RAG_PROMPT             → single-turn Q&A (no history)
  2. CONVERSATIONAL_RAG_PROMPT → multi-turn with chat history

Both prompts enforce grounding rules:
  - Answer ONLY from the context
  - Do NOT make up facts
  - Admit when context is insufficient

Customize the rules section to match your use case
(e.g. language, tone, format of answer).

Setup:
  pip install langchain langchain-core
============================================================
"""

from langchain.prompts import ChatPromptTemplate


# ─────────────────────────────────────────────
# PROMPT 1 — Standard single-turn RAG
# ─────────────────────────────────────────────
# Variables: {context}, {user_query}

RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful assistant. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is clearly present in the context, answer directly and concisely.
- If the context does not contain enough information, say: "I don't have enough information to answer this."
- Do NOT make up facts. Do NOT use knowledge outside the provided context.
- Keep your answer clear and to the point.

Context:
{context}

User Question:
{user_query}

Answer:
""")


# ─────────────────────────────────────────────
# PROMPT 2 — Conversational RAG with chat history
# ─────────────────────────────────────────────
# Variables: {chat_history}, {context}, {user_query}

CONVERSATIONAL_RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful assistant in an ongoing conversation. Answer the user's question
using ONLY the context provided below.

Rules:
- Use chat history only to resolve references like "it", "that", or "the above".
- Answer based ONLY on the provided context — do not make up information.
- If the context does not contain the answer, say: "I don't have enough information to answer this."

Chat History:
{chat_history}

Context:
{context}

User Question:
{user_query}

Answer:
""")


# ─────────────────────────────────────────────
# PROMPT 3 — Structured answer with bullet points
# ─────────────────────────────────────────────
# Use when you want the LLM to return a formatted list
# Variables: {context}, {user_query}

STRUCTURED_RAG_PROMPT = ChatPromptTemplate.from_template("""
You are a helpful assistant. Answer the user's question using ONLY the context below.
Format your answer as a clear, structured response with bullet points where appropriate.

Rules:
- Use ONLY the provided context. Do not add outside knowledge.
- If the context is insufficient, say so clearly.
- Keep each bullet point concise (1–2 sentences max).

Context:
{context}

User Question:
{user_query}

Answer:
""")


if __name__ == "__main__":
    # Preview the prompt structure
    print("── RAG_PROMPT variables ────────────────")
    print(RAG_PROMPT.input_variables)

    print("\n── CONVERSATIONAL_RAG_PROMPT variables ─")
    print(CONVERSATIONAL_RAG_PROMPT.input_variables)

    print("\n── STRUCTURED_RAG_PROMPT variables ─────")
    print(STRUCTURED_RAG_PROMPT.input_variables)
