"""
============================================================
SAMPLE PROJECT — TechCorp AI Assistant (Streamlit App)
============================================================
Demonstrates all 4 OpenAI template modules in one app.

Tabs:
  🔌 Connection   → Test HANA connection + view sample data
  🤖 SQL Assistant → Ask questions about EMPLOYEES table in plain English
  📚 Document Q&A  → RAG: Ask questions about company FAQ
  💬 Full Chatbot  → Multi-mode chatbot (GENERAL / RAG / SQL / FULL)

Run:
  cd sample_project
  streamlit run app.py

Prerequisites:
  1. pip install -r requirements.txt
  2. Fill in .env  (HANA credentials + OPENAI_API_KEY)
  3. python setup_sample_data.py   ← run ONCE to create sample data
============================================================
"""

import sys, os, pathlib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Add all OpenAI template folders to path ───────────────
ROOT = pathlib.Path(__file__).parent.parent
sys.path.extend([
    str(ROOT / "hana_db_connection"),
    str(ROOT / "hana_vector_store_openai"),
    str(ROOT / "hana_ai_query_openai"),
    str(ROOT / "hana_rag_openai"),
    str(ROOT / "sap_chatbot_openai"),
])

# ═══════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="TechCorp AI Assistant",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 TechCorp AI Assistant")
st.caption("Built with OpenAI + SAP HANA Cloud · Powered by SAP AI Templates")
st.divider()

# ═══════════════════════════════════════════════════════════
# CACHED RESOURCES  (created once, reused across all tabs)
# ═══════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Connecting to HANA...")
def get_connection():
    from connect_env import connect
    return connect()

@st.cache_resource(show_spinner="Loading embedding model...")
def get_embeddings():
    from embedding_setup import get_embedding_model
    return get_embedding_model()

@st.cache_resource(show_spinner="Loading LLM...")
def get_llm_instance():
    from llm_setup import get_llm
    return get_llm()

# ═══════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "🔌 Connection",
    "🤖 SQL Assistant",
    "📚 Document Q&A",
    "💬 Full Chatbot",
])


# ───────────────────────────────────────────────────────────
# TAB 1 — HANA CONNECTION
# ───────────────────────────────────────────────────────────
with tab1:
    st.header("HANA Connection Test")
    st.write("Verify your SAP BTP Trial HANA connection before using the other tabs.")

    col_left, col_right = st.columns([1, 2])

    with col_left:
        if st.button("🔌 Test Connection", use_container_width=True):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT CURRENT_TIMESTAMP FROM DUMMY")
                ts = cursor.fetchone()[0]
                cursor.execute("SELECT VALUE FROM M_SYSTEM_OVERVIEW WHERE NAME='Version'")
                version = cursor.fetchone()[0]
                cursor.close()
                st.success("✅ Connected to HANA!")
                st.metric("Timestamp", str(ts)[:19])
                st.metric("HANA Version", version[:40])
            except Exception as e:
                st.error(f"❌ Connection failed: {e}")
                st.info("Check your .env — HANA_HOST, HANA_PORT, HANA_USER, HANA_PASSWORD")

        st.divider()
        st.markdown("**From .env:**")
        host     = os.getenv("HANA_HOST", "not set")
        port     = os.getenv("HANA_PORT", "not set")
        user     = os.getenv("HANA_USER", "not set")
        api_key  = os.getenv("OPENAI_API_KEY", "")
        st.code(f"Host: {host}\nPort: {port}\nUser: {user}", language="text")
        if api_key.startswith("sk-"):
            st.success("✅ OPENAI_API_KEY is set")
        else:
            st.warning("⚠️  OPENAI_API_KEY not set in .env")

    with col_right:
        if st.button("📋 Show SAMPLE_EMPLOYEES table", use_container_width=True):
            try:
                import pandas as pd
                conn   = get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM SAMPLE_EMPLOYEES ORDER BY ID")
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description]
                cursor.close()
                st.dataframe(pd.DataFrame(rows, columns=cols), use_container_width=True)
            except Exception as e:
                st.error(f"Table not found: {e}")
                st.info("Run `python setup_sample_data.py` first.")

        if st.button("📊 Show Vector Store stats", use_container_width=True):
            try:
                conn  = get_connection()
                table = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")
                cursor = conn.cursor()
                cursor.execute(f'SELECT COUNT(*), COUNT(DISTINCT "SOURCE_NAME") FROM "{table}"')
                total, sources = cursor.fetchone()
                cursor.close()
                c1, c2 = st.columns(2)
                c1.metric("Chunks stored", total)
                c2.metric("Documents", sources)
            except Exception as e:
                st.error(f"Vector store not found: {e}")
                st.info("Run `python setup_sample_data.py` first.")


# ───────────────────────────────────────────────────────────
# TAB 2 — SQL ASSISTANT
#   Template used: hana_ai_query_openai/
#   Key files: llm_setup.py, schema_inspector.py,
#              sql_generator.py, query_with_summary.py
# ───────────────────────────────────────────────────────────
with tab2:
    st.header("SQL Assistant")
    st.markdown(
        "Ask questions about **SAMPLE_EMPLOYEES** in plain English. "
        "The AI generates SQL, runs it against HANA, and summarises the result."
    )

    with st.expander("ℹ️ Table schema"):
        st.code(
            "SAMPLE_EMPLOYEES (\n"
            "  ID          INT,\n"
            "  NAME        NVARCHAR(100),\n"
            "  DEPARTMENT  NVARCHAR(50),   -- Engineering / HR / Sales / Finance\n"
            "  ROLE        NVARCHAR(100),\n"
            "  SALARY      INT,            -- annual salary in INR\n"
            "  HIRE_DATE   DATE,\n"
            "  LOCATION    NVARCHAR(50)    -- Bangalore / Mumbai / Delhi / Hyderabad / Pune\n"
            ")",
            language="sql",
        )

    # Example questions
    examples = [
        "Who are all employees in Engineering?",
        "What is the average salary by department?",
        "Who is the highest paid employee?",
        "How many employees are in each location?",
        "List employees hired after 2022, sorted by salary descending.",
        "Which departments have more than 2 employees?",
    ]
    chosen = st.selectbox("Try an example:", ["— pick one —"] + examples, key="sql_ex")
    default_q = chosen if chosen != "— pick one —" else ""

    user_q = st.text_input(
        "Your question:",
        value=default_q,
        placeholder="e.g. What is the average salary in Finance?",
        key="sql_q",
    )

    if st.button("🔍 Run", key="sql_run"):
        if not user_q.strip():
            st.warning("Enter a question first.")
        else:
            try:
                conn = get_connection()
                llm  = get_llm_instance()
                from query_with_summary import ask_with_summary
                import pandas as pd
                with st.spinner("Generating SQL and fetching results..."):
                    result = ask_with_summary(
                        conn=conn,
                        user_query=user_q,
                        llm=llm,
                        tables=["SAMPLE_EMPLOYEES"],
                    )

                with st.expander("📝 Generated SQL", expanded=True):
                    st.code(result["sql"], language="sql")

                if result["data"] is not None and len(result["data"]) > 0:
                    st.markdown("**Results:**")
                    st.dataframe(pd.DataFrame(result["data"]), use_container_width=True)
                else:
                    st.info("Query returned no rows.")

                if result.get("summary"):
                    st.markdown("**AI Summary:**")
                    st.write(result["summary"])

            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Make sure HANA is connected and setup_sample_data.py has been run.")


# ───────────────────────────────────────────────────────────
# TAB 3 — DOCUMENT Q&A (RAG)
#   Templates used: hana_vector_store_openai/ + hana_rag_openai/
#   Key files: embedding_setup.py, similarity_search.py,
#              rag_pipeline.py, context_retriever.py
# ───────────────────────────────────────────────────────────
with tab3:
    st.header("Document Q&A — RAG")
    st.markdown(
        "Ask questions about the **TechCorp Company Handbook**. "
        "The AI searches HANA Vector Engine for relevant chunks, then generates a cited answer."
    )

    with st.expander("ℹ️ What's in the knowledge base?"):
        st.markdown(
            "- Work From Home Policy\n"
            "- Leave Policy (Annual, Sick, Maternity, Paternity)\n"
            "- Performance Review & Ratings\n"
            "- Salary & Bonus Structure\n"
            "- Employee Benefits\n"
            "- Onboarding Process\n"
            "- Travel Policy\n"
            "- IT & Security Rules"
        )

    rag_examples = [
        "How many days of annual leave do employees get?",
        "What is the work from home policy?",
        "How does the performance rating system work?",
        "What are the business travel expense limits?",
        "What health insurance is provided?",
        "What is the learning budget per year?",
        "What happens if I get a rating of 2?",
        "How long is the onboarding program?",
    ]
    rag_chosen = st.selectbox("Try an example:", ["— pick one —"] + rag_examples, key="rag_ex")
    rag_default = rag_chosen if rag_chosen != "— pick one —" else ""

    rag_q = st.text_input(
        "Your question:",
        value=rag_default,
        placeholder="e.g. What is the maternity leave policy?",
        key="rag_q",
    )

    col_k, col_s = st.columns(2)
    with col_k:
        top_k = st.slider("Chunks to retrieve (top_k)", 1, 10, 4, key="rag_k")
    with col_s:
        min_score = st.slider("Min similarity score", 0.0, 1.0, 0.3, 0.05, key="rag_min")

    if st.button("📚 Ask", key="rag_run"):
        if not rag_q.strip():
            st.warning("Enter a question first.")
        else:
            try:
                conn     = get_connection()
                emb      = get_embeddings()
                llm      = get_llm_instance()
                table    = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE")

                from rag_pipeline import rag_query as run_rag
                with st.spinner("Searching documents and generating answer..."):
                    result = run_rag(
                        conn=conn,
                        user_query=rag_q,
                        embedding_model=emb,
                        llm=llm,
                        table_name=table,
                        top_k=top_k,
                        min_score=min_score,
                    )

                st.markdown("### Answer")
                st.write(result["answer"])

                if result.get("sources"):
                    with st.expander(f"📎 Sources ({len(result['sources'])} chunks)", expanded=True):
                        for s in result["sources"]:
                            st.markdown(
                                f"**[{s['rank']}]** `{s['source_name']}` — "
                                f"score: `{s['score']:.3f}`"
                            )

                if result.get("context"):
                    with st.expander("🔍 Raw context sent to LLM"):
                        st.text(result["context"])

            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Make sure setup_sample_data.py has been run to embed the FAQ document.")


# ───────────────────────────────────────────────────────────
# TAB 4 — FULL CHATBOT
#   Template used: sap_chatbot_openai/
#   Key files: chatbot_config.py, chatbot_core.py,
#              prompt_builder.py, rag_retriever.py, sql_retriever.py
# ───────────────────────────────────────────────────────────
with tab4:
    st.header("Full Chatbot")
    st.write("Multi-turn conversation with memory. Switch modes to enable RAG and/or SQL.")

    # ── Mode selector ──────────────────────────────────────
    MODES = {
        "💬 GENERAL — plain conversation":         (False, False),
        "📚 RAG — document Q&A with memory":       (True,  False),
        "🤖 SQL — employee database Q&A":          (False, True),
        "⚡ FULL — RAG + SQL combined":            (True,  True),
    }
    mode_label = st.selectbox("Mode:", list(MODES.keys()), key="chat_mode")
    enable_rag, enable_sql = MODES[mode_label]

    MODE_DESC = {
        "💬 GENERAL — plain conversation":    "Plain LLM chat with rolling memory. No data retrieval.",
        "📚 RAG — document Q&A with memory":  "Searches company FAQ before each reply. Cites sources.",
        "🤖 SQL — employee database Q&A":     "Generates SQL for SAMPLE_EMPLOYEES to answer data questions.",
        "⚡ FULL — RAG + SQL combined":       "Uses both document search and DB queries together.",
    }
    st.caption(MODE_DESC[mode_label])

    # ── Build/cache chatbot per mode ───────────────────────
    bot_key  = f"bot_{mode_label}"
    hist_key = f"hist_{mode_label}"

    if bot_key not in st.session_state:
        try:
            from chatbot_config import ChatbotConfig
            from chatbot_core import SAPChatbot
            conn   = get_connection()
            config = ChatbotConfig(
                llm_model      = "gpt-4o-mini",
                temperature    = 0.2,
                memory_window  = 10,
                enable_rag     = enable_rag,
                embedding_model= "text-embedding-3-small",
                vector_table   = os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE"),
                rag_top_k      = 4,
                rag_min_score  = 0.3,
                enable_sql     = enable_sql,
                sql_tables     = ["SAMPLE_EMPLOYEES"] if enable_sql else [],
                system_prompt  = (
                    "You are a friendly TechCorp HR and data assistant. "
                    "Help employees with policy questions, HR rules, and employee data. "
                    "Be concise. If you don't know, say so."
                ),
                bot_name="TechCorp Assistant",
            )
            st.session_state[bot_key]  = SAPChatbot(conn, config)
            st.session_state[hist_key] = []
        except Exception as e:
            st.error(f"Could not start chatbot: {e}")
            st.stop()

    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    # ── Chat history display ───────────────────────────────
    for msg in st.session_state[hist_key]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📎 {len(msg['sources'])} sources"):
                    for s in msg["sources"]:
                        st.caption(
                            f"[{s.get('rank','?')}] {s.get('source_name','')} "
                            f"— score: {s.get('score',0):.3f}"
                        )
            if msg.get("sql_used"):
                with st.expander("🗃️ SQL used"):
                    st.code(msg["sql_used"], language="sql")

    # ── Chat input ─────────────────────────────────────────
    if prompt := st.chat_input("Ask me anything about TechCorp..."):
        st.session_state[hist_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    bot    = st.session_state[bot_key]
                    result = bot.chat(prompt)

                    st.write(result["answer"])

                    if result.get("sources"):
                        with st.expander(f"📎 {len(result['sources'])} sources"):
                            for s in result["sources"]:
                                st.caption(
                                    f"[{s.get('rank','?')}] {s.get('source_name','')} "
                                    f"— score: {s.get('score',0):.3f}"
                                )
                    if result.get("sql_used"):
                        with st.expander("🗃️ SQL used"):
                            st.code(result["sql_used"], language="sql")

                    st.caption(f"Mode: {result['mode']} · Turn: {result['turn']}")

                    st.session_state[hist_key].append({
                        "role":     "assistant",
                        "content":  result["answer"],
                        "sources":  result.get("sources", []),
                        "sql_used": result.get("sql_used"),
                    })
                except Exception as e:
                    st.error(f"Error: {e}")

    # ── Reset button ───────────────────────────────────────
    if st.button("🔄 Reset conversation", key="reset"):
        if bot_key in st.session_state:
            st.session_state[bot_key].reset()
        st.session_state[hist_key] = []
        st.rerun()
