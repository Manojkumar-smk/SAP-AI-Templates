"""
============================================================
MINI TEMPLATE — Interactive CLI Chat Runner
============================================================
Use this when: you want to run your chatbot interactively
in the terminal to test it or use it directly.

Commands during chat:
  /reset    → clear conversation history, start fresh
  /history  → print full conversation so far
  /mode     → show current chatbot mode
  /quit     → exit

How to use:
  1. Pick your chatbot preset below (general / rag / sql / full)
  2. Uncomment the one you want
  3. python cli_runner.py

Setup:
  pip install -r requirements.txt
============================================================
"""

import os, sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "hana_db_connection"))

from dotenv import load_dotenv
from chatbot_presets import (
    create_general_chatbot,
    create_rag_chatbot,
    create_sql_chatbot,
    create_full_chatbot,
)

load_dotenv()


def run_cli(bot):
    """
    Start an interactive chat loop in the terminal.

    Args:
        bot : SAPChatbot instance (from any chatbot_presets factory)
    """
    print(f"\n{'=' * 60}")
    print(f"  {bot.config.bot_name}")
    print(f"  Mode: {bot.config.mode()} | Memory: {bot.config.memory_window} turns")
    print(f"{'=' * 60}")
    print("Type your message. Commands: /reset | /history | /mode | /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() == "/quit":
            print("Goodbye!")
            break
        elif user_input.lower() == "/reset":
            bot.reset()
            print(f"Bot: Conversation cleared. Starting fresh!\n")
            continue
        elif user_input.lower() == "/history":
            bot.print_history()
            continue
        elif user_input.lower() == "/mode":
            print(f"Mode: {bot.config.mode()} | Turns: {bot.get_turn_count()}\n")
            continue

        # Send message
        response = bot.chat(user_input)

        print(f"\nBot [{response['mode']}]: {response['answer']}")

        if response["sources"]:
            print(f"Sources: {[s['source_name'] for s in response['sources']]}")

        if response["sql_used"]:
            print(f"SQL: {response['sql_used']}")

        print()


if __name__ == "__main__":
    # ── Connect to HANA (only needed for RAG / SQL modes) ─────
    from connect_env import connect   # swap to connect_btp_cf if on BTP
    conn = connect()

    # ── Pick ONE preset and uncomment it ──────────────────────

    # Option A: General chatbot (no DB)
    bot = create_general_chatbot(
        system_prompt = "You are a helpful SAP technical assistant.",
        memory_window = 10,
    )

    # Option B: RAG chatbot (documents from HANA Vector Store)
    # bot = create_rag_chatbot(
    #     conn          = conn,
    #     vector_table  = "VECTOR_STORE",
    #     rag_top_k     = 5,
    #     rag_min_score = 0.5,
    # )

    # Option C: SQL chatbot (live HANA table data)
    # bot = create_sql_chatbot(
    #     conn       = conn,
    #     sql_tables = ["CUST_TICKETS", "SALES_ORDERS"],
    # )

    # Option D: Full chatbot (RAG + SQL + memory)
    # bot = create_full_chatbot(
    #     conn         = conn,
    #     sql_tables   = ["CUST_TICKETS"],
    #     vector_table = "VECTOR_STORE",
    # )
    # ──────────────────────────────────────────────────────────

    try:
        run_cli(bot)
    finally:
        conn.close()
