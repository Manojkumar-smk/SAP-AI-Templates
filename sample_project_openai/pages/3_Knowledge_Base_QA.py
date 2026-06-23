"""
PAGE 3 — Knowledge Base Q&A (Template 04: HANA RAG Agent)
Ask questions answered from documents stored in the HANA Vector Store.
"""

import sys, os
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_01_hana_connection"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_03_hana_vector_store"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_04_hana_rag"))

from hana_session import inject_css, page_header, require_connection, get_env_or_input

st.set_page_config(page_title="Knowledge Base Q&A", page_icon="📚", layout="wide")
inject_css()

# ── Sidebar config ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Configuration</div>', unsafe_allow_html=True)
    llm_id       = get_env_or_input("LLM_DEPLOYMENT_ID",       "LLM Deployment ID")
    embedding_id = get_env_or_input("EMBEDDING_DEPLOYMENT_ID", "Embedding Deployment ID")
    vector_table = st.text_input("Vector Table", value=os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE"))
    top_k        = st.slider("Top K chunks", 1, 10, 5)
    min_score    = st.slider("Min similarity score", 0.0, 1.0, 0.5, 0.05)
    source_filter = st.text_input("Filter by source (optional)", placeholder="document.pdf")

page_header("Knowledge Base Q&A", "Ask questions answered from your documents stored in HANA Vector Store", "📚")

if not llm_id or not embedding_id:
    st.warning("Set **LLM_DEPLOYMENT_ID** and **EMBEDDING_DEPLOYMENT_ID** in `.env` or the sidebar.")
    st.stop()

conn = require_connection()

@st.cache_resource(show_spinner=False)
def get_rag_agent(_conn, _llm_id, _emb_id, _table, _top_k, _min_score):
    from hana_rag import HANARagAgent
    os.environ["LLM_DEPLOYMENT_ID"]       = _llm_id
    os.environ["EMBEDDING_DEPLOYMENT_ID"] = _emb_id
    return HANARagAgent(
        conn=_conn,
        table_name=_table,
        top_k=_top_k,
        min_score=_min_score,
        memory_window=0,    # stateless for single-turn Q&A; chatbot page handles memory
    )

try:
    agent = get_rag_agent(conn, llm_id, embedding_id, vector_table, top_k, min_score)
except Exception as e:
    st.error(f"Failed to initialise RAG agent: {e}")
    st.stop()

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Q&A interface ─────────────────────────────────────────────
st.markdown("##### Ask a question from your knowledge base")

user_question = st.text_input(
    "Your question",
    placeholder="e.g. What is the warranty policy for premium products?",
)

if st.button("▶  Get Answer", type="primary") and user_question:
    with st.spinner("Searching knowledge base and generating answer…"):
        try:
            result = agent.ask(
                user_question,
                source_filter=source_filter if source_filter else None,
                top_k=top_k,
            )

            # ── Answer ─────────────────────────────────────────
            st.markdown("**Answer**")
            st.markdown(f"""
            <div style="background:#F0F5FF;border-left:4px solid #0070F2;
                        border-radius:0 8px 8px 0;padding:1rem 1.2rem;
                        font-size:1rem;color:#1A1A2E;line-height:1.6;">
                {result['answer']}
            </div>
            """, unsafe_allow_html=True)

            # ── Sources ────────────────────────────────────────
            if result["sources"]:
                st.markdown("<br>**Sources used**", unsafe_allow_html=True)
                src_cols = st.columns(min(len(result["sources"]), 4))
                for i, src in enumerate(result["sources"]):
                    score_color = "#1A7F40" if src["score"] >= 0.7 else "#E76500"
                    src_cols[i % len(src_cols)].markdown(f"""
                    <div style="border:1px solid #DDE5F0;border-radius:8px;padding:0.6rem;text-align:center;">
                        <div style="font-size:0.75rem;color:#475E75;">#{src['rank']}</div>
                        <div class="source-pill">{src['source_name']}</div>
                        <div style="font-size:0.8rem;color:{score_color};font-weight:700;margin-top:4px;">
                            {src['score']} similarity
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No relevant chunks found above the similarity threshold. "
                           "Try lowering **Min similarity score** in the sidebar, "
                           "or upload more documents in the Document Manager.")

            # ── Context viewer ─────────────────────────────────
            with st.expander("🔍 View retrieved context chunks"):
                st.markdown(f'<div class="code-block">{result["context"]}</div>',
                            unsafe_allow_html=True)

            # ── Save to history ────────────────────────────────
            if "qa_history" not in st.session_state:
                st.session_state["qa_history"] = []
            st.session_state["qa_history"].append({
                "question": user_question,
                "answer":   result["answer"],
                "sources":  [s["source_name"] for s in result["sources"]],
            })

        except Exception as e:
            st.error(f"Q&A failed: {e}")

# ── Q&A History ───────────────────────────────────────────────
st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)
if st.session_state.get("qa_history"):
    with st.expander(f"🕐 Q&A History ({len(st.session_state['qa_history'])} questions)"):
        for i, item in enumerate(reversed(st.session_state["qa_history"][-10:]), 1):
            st.markdown(f"**Q{i}:** {item['question']}")
            st.markdown(f"> {item['answer'][:200]}{'…' if len(item['answer'])>200 else ''}")
            if item["sources"]:
                st.markdown("Sources: " + " ".join(f"`{s}`" for s in item["sources"]))
            st.markdown("---")
