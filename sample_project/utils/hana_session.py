"""
Shared HANA connection utilities for the Streamlit sample project.
Uses st.cache_resource so the connection is created once per session.
"""

import sys
import streamlit as st
from pathlib import Path

# ── Add template paths ────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(ROOT / "template_01_hana_connection"))
sys.path.append(str(ROOT / "template_02_hana_ai_query"))
sys.path.append(str(ROOT / "template_03_hana_vector_store"))
sys.path.append(str(ROOT / "template_04_hana_rag"))
sys.path.append(str(ROOT / "template_05_sap_chatbot"))


@st.cache_resource(show_spinner="Connecting to SAP HANA Cloud...")
def get_connection():
    """
    Opens and caches the HANA connection for the entire Streamlit session.
    Called once — reused across all pages.
    """
    from hana_connection import get_hana_credentials, get_dbapi_connection
    creds = get_hana_credentials()
    conn  = get_dbapi_connection(creds)
    return conn


def require_connection():
    """
    Call at the top of any page that needs HANA.
    Returns conn, or shows an error and stops the page.
    """
    try:
        return get_connection()
    except Exception as e:
        st.error(f"**HANA connection failed:** {e}")
        st.info("Check your `.env` file and make sure HANA_HOST, HANA_USER, HANA_PASSWORD are set correctly.")
        st.stop()


def get_env_or_input(key: str, label: str, secret: bool = False) -> str:
    """
    Returns value from .env if set, otherwise shows a Streamlit input in sidebar.
    Useful for deployment IDs that may not be in .env.
    """
    import os
    val = os.getenv(key)
    if val:
        return val
    if secret:
        return st.sidebar.text_input(label, type="password", key=key)
    return st.sidebar.text_input(label, key=key)


SAP_CSS = """
<style>
/* SAP-inspired colour palette */
:root {
    --sap-blue:    #0070F2;
    --sap-dark:    #003B62;
    --sap-grey:    #475E75;
    --sap-light:   #EEF4FF;
    --sap-green:   #1A7F40;
    --sap-red:     #BB0000;
    --sap-orange:  #E76500;
}

/* Top header bar */
.sap-header {
    background: linear-gradient(135deg, #003B62 0%, #0070F2 100%);
    padding: 1.2rem 1.5rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.sap-header h1 {
    color: white !important;
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
}
.sap-header p {
    color: rgba(255,255,255,0.85);
    margin: 0;
    font-size: 0.9rem;
}

/* Status badges */
.badge-ok   { background:#D6F5E3; color:#1A7F40; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.82rem; }
.badge-fail { background:#FFE0E0; color:#BB0000; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.82rem; }
.badge-info { background:#EEF4FF; color:#0070F2; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.82rem; }

/* Metric cards */
.metric-card {
    background: white;
    border: 1px solid #DDE5F0;
    border-top: 4px solid #0070F2;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-card .value { font-size: 1.8rem; font-weight: 700; color: #003B62; }
.metric-card .label { font-size: 0.8rem; color: #475E75; margin-top: 2px; }

/* Chat bubbles */
.chat-user {
    background: #EEF4FF;
    border-left: 4px solid #0070F2;
    padding: 0.7rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
}
.chat-bot {
    background: #F5F5F5;
    border-left: 4px solid #475E75;
    padding: 0.7rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 6px 0;
}
.chat-label { font-size:0.75rem; font-weight:700; text-transform:uppercase; color:#475E75; margin-bottom:3px; }

/* Source pill */
.source-pill {
    display: inline-block;
    background: #EEF4FF;
    color: #0070F2;
    border: 1px solid #BDD4FF;
    border-radius: 12px;
    padding: 2px 9px;
    font-size: 0.78rem;
    margin: 2px 3px;
}

/* Code block */
.code-block {
    background: #1E1E2E;
    color: #CBD3F5;
    padding: 0.8rem 1rem;
    border-radius: 6px;
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
    white-space: pre-wrap;
    margin: 0.5rem 0;
}

/* Divider */
.sap-divider {
    border: none;
    border-top: 2px solid #EEF4FF;
    margin: 1.2rem 0;
}

/* Sidebar label */
.sidebar-section {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #475E75;
    letter-spacing: 0.05em;
    padding: 8px 0 4px 0;
}
</style>
"""


def inject_css():
    st.markdown(SAP_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, icon: str = "🔷"):
    st.markdown(f"""
    <div class="sap-header">
        <div style="font-size:2rem;">{icon}</div>
        <div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
