"""
PAGE 4 — AI Chatbot (Template 05: SAP AI Chatbot)
Fully configurable chatbot: General / RAG / SQL / Full mode.
Conversation memory persisted in Streamlit session state.
"""

import sys, os
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_01_hana_connection"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_02_hana_ai_query"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_03_hana_vector_store"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_04_hana_rag"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_05_sap_chatbot"))

from hana_session import inject_css, page_header, require_connection, get_env_or_input

st.set_page_config(page_title="AI Chatbot", page_icon="🤖", layout="wide")
inject_css()

# ── Sidebar config ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Chatbot Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Select Mode",
        ["💬 General", "📚 RAG", "🔍 SQL", "⚡ Full (RAG + SQL)"],
        index=0,
        help="General: LLM only | RAG: HANA Vector search | SQL: HANA query | Full: both"
    )

    st.markdown('<div class="sidebar-section">SAP Gen AI Hub</div>', unsafe_allow_html=True)
    llm_id       = get_env_or_input("LLM_DEPLOYMENT_ID",       "LLM Deployment ID")
    embedding_id = get_env_or_input("EMBEDDING_DEPLOYMENT_ID", "Embedding Deployment ID") \
                   if "RAG" in mode or "Full" in mode else ""

    st.markdown('<div class="sidebar-section">LLM Settings</div>', unsafe_allow_html=True)
    llm_model   = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o", "gpt-4"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.1, 0.05)
    memory_window = st.slider("Memory (turns)", 0, 20, 10)

    if "RAG" in mode or "Full" in mode:
        st.markdown('<div class="sidebar-section">RAG Settings</div>', unsafe_allow_html=True)
        vector_table = st.text_input("Vector Table", value=os.getenv("VECTOR_TABLE_NAME","VECTOR_STORE"))
        rag_top_k    = st.slider("Top K chunks", 1, 10, 5)
        rag_min_score= st.slider("Min similarity", 0.0, 1.0, 0.5, 0.05)
    else:
        vector_table = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
        rag_top_k = 5; rag_min_score = 0.5

    if "SQL" in mode or "Full" in mode:
        st.markdown('<div class="sidebar-section">SQL Settings</div>', unsafe_allow_html=True)
        sql_tables_input = st.text_area("HANA Tables (one per line)", value="CUST_TICKETS", height=80)
    else:
        sql_tables_input = ""

    st.markdown('<div class="sidebar-section">Persona</div>', unsafe_allow_html=True)
    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful SAP AI assistant. Answer clearly and concisely.",
        height=80,
    )
    bot_name = st.text_input("Bot Name", value="SAP AI Assistant")

    st.divider()
    if st.button("🔄  Reset Conversation", use_container_width=True):
        st.session_state["chat_history"] = []
        st.session_state["chatbot"]      = None
        st.rerun()

page_header("AI Chatbot", f"Mode: {mode}  ·  {bot_name}", "🤖")

if not llm_id:
    st.warning("Set **LLM_DEPLOYMENT_ID** in `.env` or the sidebar to continue.")
    st.stop()

conn = require_connection() if ("RAG" in mode or "SQL" in mode or "Full" in mode) else None

# ── Build / rebuild chatbot when config changes ───────────────
config_key = f"{mode}|{llm_id}|{embedding_id}|{llm_model}|{temperature}|{memory_window}|{vector_table}|{rag_top_k}|{rag_min_score}|{sql_tables_input}|{system_prompt}|{bot_name}"

if st.session_state.get("chatbot_key") != config_key:
    st.session_state["chatbot_key"] = config_key
    st.session_state["chatbot"]     = None
    st.session_state["chat_history"] = []

if st.session_state.get("chatbot") is None:
    from sap_chatbot import (
        ChatbotConfig, SAPChatbot,
        create_general_chatbot, create_rag_chatbot,
        create_sql_chatbot, create_full_chatbot
    )
    os.environ["LLM_DEPLOYMENT_ID"]       = llm_id
    os.environ["EMBEDDING_DEPLOYMENT_ID"] = embedding_id or ""

    sql_tables = [t.strip() for t in sql_tables_input.splitlines() if t.strip()]

    try:
        if "General" in mode:
            bot = create_general_chatbot(
                llm_deployment_id=llm_id, system_prompt=system_prompt,
                llm_model=llm_model, temperature=temperature, memory_window=memory_window,
            )
            # Override bot name
            bot.config.bot_name = bot_name

        elif "RAG" in mode and "Full" not in mode:
            bot = create_rag_chatbot(
                conn=conn, llm_deployment_id=llm_id,
                embedding_deployment_id=embedding_id, vector_table=vector_table,
                system_prompt=system_prompt, llm_model=llm_model,
                rag_top_k=rag_top_k, rag_min_score=rag_min_score, memory_window=memory_window,
            )
            bot.config.bot_name = bot_name

        elif "SQL" in mode and "Full" not in mode:
            if not sql_tables:
                st.error("Add at least one HANA table in the sidebar for SQL mode.")
                st.stop()
            bot = create_sql_chatbot(
                conn=conn, llm_deployment_id=llm_id, sql_tables=sql_tables,
                system_prompt=system_prompt, llm_model=llm_model, memory_window=memory_window,
            )
            bot.config.bot_name = bot_name

        else:  # Full
            if not sql_tables:
                st.error("Add at least one HANA table in the sidebar for Full mode.")
                st.stop()
            bot = create_full_chatbot(
                conn=conn, llm_deployment_id=llm_id,
                embedding_deployment_id=embedding_id, sql_tables=sql_tables,
                vector_table=vector_table, system_prompt=system_prompt,
                llm_model=llm_model, rag_top_k=rag_top_k, rag_min_score=rag_min_score,
                memory_window=memory_window,
            )
            bot.config.bot_name = bot_name

        st.session_state["chatbot"] = bot

    except Exception as e:
        st.error(f"Failed to initialise chatbot: {e}")
        st.stop()

bot = st.session_state["chatbot"]

# ── Chat history display ──────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

chat_container = st.container()

with chat_container:
    if not st.session_state["chat_history"]:
        st.markdown(f"""
        <div style="text-align:center;padding:2rem;color:#8A9BB0;">
            <div style="font-size:2.5rem;">🤖</div>
            <div style="font-size:1rem;margin-top:0.5rem;">
                <strong>{bot_name}</strong> is ready.<br>
                <span style="font-size:0.85rem;">Mode: {mode}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-user">
                <div class="chat-label">You</div>
                {msg["content"]}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-bot">
                <div class="chat-label">{bot_name}</div>
                {msg["content"]}
            </div>""", unsafe_allow_html=True)

            # Show sources if any
            if msg.get("sources"):
                pills = " ".join(
                    f'<span class="source-pill">📄 {s["source_name"]} ({s["score"]})</span>'
                    for s in msg["sources"]
                )
                st.markdown(f'<div style="margin-top:4px;">{pills}</div>', unsafe_allow_html=True)

            # Show SQL if any
            if msg.get("sql_used"):
                with st.expander("🔍 SQL Query used"):
                    st.markdown(f'<div class="code-block">{msg["sql_used"]}</div>',
                                unsafe_allow_html=True)

            # Show mode badge
            badge_color = {"GENERAL": "#475E75", "RAG": "#0070F2", "SQL": "#1A7F40",
                           "RAG+SQL": "#7B2FBE"}.get(msg.get("mode",""), "#475E75")
            st.markdown(f'<span style="font-size:0.72rem;color:{badge_color};">⚙ {msg.get("mode","")}</span>',
                        unsafe_allow_html=True)

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Chat input ────────────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    col_input, col_send = st.columns([5, 1])
    user_input = col_input.text_input(
        "Message",
        placeholder=f"Ask {bot_name} anything…",
        label_visibility="collapsed",
    )
    send = col_send.form_submit_button("Send ➤", use_container_width=True)

if send and user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})

    with st.spinner(f"{bot_name} is thinking…"):
        try:
            response = bot.chat(user_input)
            st.session_state["chat_history"].append({
                "role":     "assistant",
                "content":  response["answer"],
                "sources":  response.get("sources", []),
                "sql_used": response.get("sql_used", ""),
                "mode":     response.get("mode", ""),
            })
        except Exception as e:
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": f"⚠️ Error: {e}",
                "sources": [], "sql_used": "", "mode": "ERROR",
            })

    st.rerun()

# ── Stats footer ──────────────────────────────────────────────
if st.session_state["chat_history"]:
    turns = len([m for m in st.session_state["chat_history"] if m["role"] == "user"])
    st.caption(f"Turns: {turns}  ·  Memory window: {memory_window}  ·  Model: {llm_model}")
