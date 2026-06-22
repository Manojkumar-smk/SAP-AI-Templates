"""
============================================================
SAP AI Templates — Sample Streamlit App
============================================================
Home page: HANA health check + app overview.
Navigate using the sidebar to explore all templates.

Run:
    cd sample_project
    streamlit run app.py
============================================================
"""

import sys, os
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent / "template_01_hana_connection"))

from hana_session import inject_css, page_header, get_connection

st.set_page_config(
    page_title  = "SAP AI Templates",
    page_icon   = "🔷",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)
inject_css()

# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Navigation</div>', unsafe_allow_html=True)
    st.page_link("app.py",                               label="🏠  Home & Health Check")
    st.page_link("pages/1_Document_Manager.py",           label="📄  Document Manager")
    st.page_link("pages/2_Ask_Your_Data.py",              label="🔍  Ask Your Data (SQL)")
    st.page_link("pages/3_Knowledge_Base_QA.py",          label="📚  Knowledge Base Q&A")
    st.page_link("pages/4_AI_Chatbot.py",                 label="🤖  AI Chatbot")
    st.divider()
    st.markdown('<div class="sidebar-section">About</div>', unsafe_allow_html=True)
    st.caption("SAP AI Templates v1.0\nBuilt with SAP HANA Cloud + SAP Gen AI Hub")

# ── Page header ───────────────────────────────────────────────
page_header(
    "SAP AI Templates",
    "Sample application demonstrating all 5 SAP AI coding templates",
    "🔷"
)

# ── Template cards ────────────────────────────────────────────
st.markdown("### What's inside")
cols = st.columns(5)
cards = [
    ("T01", "🔌", "HANA\nConnection",   "Connect to HANA Cloud with health check"),
    ("T02", "🔍", "AI SQL\nQuery",      "Natural language → SQL → DataFrame"),
    ("T03", "📄", "Vector\nStore",      "Embed documents into HANA Vector Engine"),
    ("T04", "📚", "RAG\nAgent",         "Retrieve context → grounded LLM answer"),
    ("T05", "🤖", "AI\nChatbot",        "Configurable chatbot: General / RAG / SQL"),
]
for col, (tag, icon, name, desc) in zip(cols, cards):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size:1.8rem;">{icon}</div>
            <div class="value" style="font-size:1rem;">{tag}</div>
            <div style="font-size:0.9rem;font-weight:600;color:#003B62;margin-top:4px;">{name}</div>
            <div class="label" style="margin-top:6px;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── HANA Health Check ─────────────────────────────────────────
st.markdown("### 🔌 HANA Cloud — Connection Health Check")

col1, col2 = st.columns([1, 2])

with col1:
    if st.button("▶  Run Health Check", type="primary", use_container_width=True):
        st.session_state["run_health"] = True

if st.session_state.get("run_health"):
    with st.spinner("Connecting to SAP HANA Cloud..."):
        try:
            from hana_connection import get_hana_credentials, get_dbapi_connection, health_check
            creds  = get_hana_credentials()
            conn   = get_dbapi_connection(creds)
            result = health_check(conn)
            conn.close()

            if result["status"] == "OK":
                st.success("**Connection successful!**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Status",    result["status"])
                m2.metric("Timestamp", result["timestamp"])
                m3.metric("Version",   result["version"][:30] if result["version"] else "—")
            else:
                st.error(f"Health check failed: {result['error']}")

        except Exception as e:
            st.error(f"**Connection failed:** {e}")
            st.info("Make sure your `.env` file is set up correctly. See `.env.example` for reference.")

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Architecture diagram ──────────────────────────────────────
st.markdown("### 🏗️ Template Dependency Chain")
st.markdown("""
<div class="code-block">Template 01  hana_connection.py       ← HANA credentials, connection, health check
     │
     ├── Template 02  hana_ai_query.py      ← NL question → SQL → DataFrame
     │
     ├── Template 03  hana_vector_store.py  ← Load docs → embed → store REAL_VECTOR
     │         │
     │         └── Template 04  hana_rag.py ← COSINE_SIMILARITY search → grounded answer
     │                   │
     └─────────────────── Template 05  sap_chatbot.py
                          └── ChatbotConfig → General / RAG / SQL / Full chatbot
</div>
""", unsafe_allow_html=True)

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)
st.caption("👈 Use the sidebar to navigate to each template demo.")
