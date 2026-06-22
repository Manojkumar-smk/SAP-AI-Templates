"""
PAGE 2 — Ask Your Data (Template 02: HANA AI Query Agent)
Natural language question → SAP Gen AI Hub generates SQL → execute → show DataFrame + summary.
"""

import sys, os
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_01_hana_connection"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_02_hana_ai_query"))

from hana_session import inject_css, page_header, require_connection, get_env_or_input

st.set_page_config(page_title="Ask Your Data", page_icon="🔍", layout="wide")
inject_css()

# ── Sidebar config ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Configuration</div>', unsafe_allow_html=True)
    llm_id = get_env_or_input("LLM_DEPLOYMENT_ID", "LLM Deployment ID")
    st.markdown('<div class="sidebar-section">Tables to Query</div>', unsafe_allow_html=True)
    tables_input = st.text_area(
        "HANA Table Names (one per line)",
        value="CUST_TICKETS",
        help="Enter the HANA table names the AI can query.",
        height=100,
    )
    show_sql = st.checkbox("Show generated SQL", value=True)
    show_summary = st.checkbox("Show AI summary", value=True)

page_header("Ask Your Data", "Type a question in plain English — AI generates and runs the SQL for you", "🔍")

if not llm_id:
    st.warning("Set **LLM_DEPLOYMENT_ID** in your `.env` or in the sidebar to continue.")
    st.stop()

conn   = require_connection()
tables = [t.strip() for t in tables_input.splitlines() if t.strip()]

if not tables:
    st.warning("Add at least one HANA table name in the sidebar.")
    st.stop()

# ── Init agent ─────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_agent(_conn, _llm_id, _tables):
    from hana_ai_query import HANAQueryAgent
    os.environ["LLM_DEPLOYMENT_ID"] = _llm_id
    return HANAQueryAgent(_conn, tables=_tables)

try:
    agent = get_agent(conn, llm_id, tables)
    st.markdown(f"**Tables in scope:** {', '.join(f'`{t}`' for t in tables)}")
except Exception as e:
    st.error(f"Failed to initialise query agent: {e}")
    st.stop()

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Schema preview ────────────────────────────────────────────
with st.expander("📋 View Table Schema"):
    st.markdown(f"""<div class="code-block">{agent.get_schema()}</div>""", unsafe_allow_html=True)

# ── Query input ───────────────────────────────────────────────
st.markdown("##### Ask a question about your data")

# Sample questions
st.markdown("**Try these examples:**")
examples = [
    "Show me the 5 most recent records",
    "How many records are there in total?",
    "Show records grouped by category with counts",
    "What are the unique values in the priority column?",
]
ex_cols = st.columns(len(examples))
for col, ex in zip(ex_cols, examples):
    if col.button(ex, use_container_width=True):
        st.session_state["nl_query"] = ex

user_query = st.text_input(
    "Your question",
    value=st.session_state.get("nl_query", ""),
    placeholder="e.g. Show the top 5 customers by total revenue",
    key="nl_query_input"
)

col_run, col_clear = st.columns([1, 5])
run_clicked   = col_run.button("▶  Run Query", type="primary")
col_clear.button("Clear", on_click=lambda: st.session_state.update({"nl_query": ""}))

if run_clicked and user_query:
    with st.spinner("Generating and running SQL…"):
        try:
            if show_summary:
                result = agent.ask_with_summary(user_query)
                df      = result["data"]
                sql     = result["sql"]
                summary = result["summary"]
            else:
                df      = agent.ask(user_query)
                sql     = ""
                summary = ""

            # ── Generated SQL
            if show_sql and sql:
                st.markdown("**Generated SQL**")
                st.markdown(f'<div class="code-block">{sql}</div>', unsafe_allow_html=True)

            # ── AI Summary
            if show_summary and summary:
                st.info(f"**AI Summary:** {summary}")

            # ── Results
            st.markdown(f"**Results** — {len(df)} row(s) returned")
            if df.empty:
                st.warning("Query returned no rows.")
            else:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False)
                st.download_button("⬇  Download CSV", csv, "query_results.csv", "text/csv")

        except Exception as e:
            st.error(f"Query failed: {e}")
elif run_clicked and not user_query:
    st.warning("Please enter a question first.")

# ── History ───────────────────────────────────────────────────
st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)
if "query_history" not in st.session_state:
    st.session_state["query_history"] = []

if run_clicked and user_query:
    st.session_state["query_history"].append(user_query)

if st.session_state["query_history"]:
    with st.expander("🕐 Query History"):
        for i, q in enumerate(reversed(st.session_state["query_history"][-10:]), 1):
            st.markdown(f"`{i}.` {q}")
