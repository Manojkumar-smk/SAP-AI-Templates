"""
PAGE 1 — Document Manager (Template 03: HANA Vector Store)
Upload documents → chunk → embed via SAP Gen AI Hub → store in HANA REAL_VECTOR.
"""

import sys, os, tempfile
import streamlit as st
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_01_hana_connection"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "template_03_hana_vector_store"))

from hana_session import inject_css, page_header, require_connection, get_env_or_input

st.set_page_config(page_title="Document Manager", page_icon="📄", layout="wide")
inject_css()

# ── Sidebar config ────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Configuration</div>', unsafe_allow_html=True)
    embedding_id = get_env_or_input("EMBEDDING_DEPLOYMENT_ID", "Embedding Deployment ID")
    vector_table = st.text_input("Vector Table Name", value=os.getenv("VECTOR_TABLE_NAME", "VECTOR_STORE"))
    chunk_size   = st.slider("Chunk Size (chars)", 200, 1000, 500, step=50)
    chunk_overlap= st.slider("Chunk Overlap",       0,  200,  50,  step=10)

page_header("Document Manager", "Upload documents and store vector embeddings in SAP HANA Cloud", "📄")

if not embedding_id:
    st.warning("Set **EMBEDDING_DEPLOYMENT_ID** in your `.env` or in the sidebar to continue.")
    st.stop()

# ── Connect ────────────────────────────────────────────────────
conn = require_connection()

# ── Init vector store ──────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_vector_store(_conn, _embedding_id, _table):
    from hana_vector_store import HANAVectorStore
    os.environ["EMBEDDING_DEPLOYMENT_ID"] = _embedding_id
    return HANAVectorStore(_conn, table_name=_table)

try:
    store = get_vector_store(conn, embedding_id, vector_table)
except Exception as e:
    st.error(f"Failed to initialise vector store: {e}")
    st.stop()

# ── Stats banner ───────────────────────────────────────────────
try:
    stats = store.get_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Chunks",   stats["total_chunks"])
    c2.metric("Total Sources",  stats["total_sources"])
    c3.metric("Vector Table",   stats["table"])
except:
    pass

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Upload section ─────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📁  Upload File", "🔗  Add URL", "✏️  Add Text"])

# ── Tab 1: File upload ─────────────────────────────────────────
with tab1:
    st.markdown("##### Upload a document to embed and store")
    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "csv", "xlsx", "xls"],
        help="Supported: PDF, TXT, CSV, Excel (.xlsx/.xls)"
    )

    clear_existing = st.checkbox("Replace existing vectors for this file (if previously uploaded)")

    if uploaded and st.button("⚡  Embed & Store", type="primary"):
        suffix = Path(uploaded.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        with st.spinner(f"Embedding {uploaded.name}…"):
            try:
                count = store.add(
                    tmp_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    clear_existing=clear_existing,
                )
                st.success(f"✅ Stored **{count}** chunks from `{uploaded.name}`")
                st.cache_resource.clear()   # refresh stats
            except Exception as e:
                st.error(f"Failed: {e}")
            finally:
                os.unlink(tmp_path)

# ── Tab 2: URL ────────────────────────────────────────────────
with tab2:
    st.markdown("##### Fetch and embed a web page")
    url = st.text_input("URL", placeholder="https://help.sap.com/docs/hana-cloud")
    if url and st.button("⚡  Fetch & Embed", type="primary"):
        with st.spinner(f"Fetching and embedding {url}…"):
            try:
                count = store.add(url, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                st.success(f"✅ Stored **{count}** chunks from `{url}`")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Failed: {e}")

# ── Tab 3: Raw text ───────────────────────────────────────────
with tab3:
    st.markdown("##### Paste or type text to embed directly")
    raw_text = st.text_area("Text content", height=180, placeholder="Paste your text here…")
    source_label = st.text_input("Source label", value="manual_input", placeholder="my_text_01")
    if raw_text and st.button("⚡  Embed Text", type="primary"):
        with st.spinner("Embedding text…"):
            try:
                count = store.add(raw_text, source_name=source_label,
                                  chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                st.success(f"✅ Stored **{count}** chunks.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Failed: {e}")

st.markdown('<hr class="sap-divider">', unsafe_allow_html=True)

# ── Search preview ────────────────────────────────────────────
st.markdown("##### 🔎 Preview Similarity Search")
test_query = st.text_input("Test query", placeholder="Type a question to test retrieval…")
if test_query:
    with st.spinner("Searching…"):
        try:
            results = store.search(test_query, top_k=5)
            if results:
                for r in results:
                    score_color = "#1A7F40" if r["score"] >= 0.7 else "#E76500" if r["score"] >= 0.5 else "#BB0000"
                    st.markdown(f"""
                    <div style="border:1px solid #DDE5F0;border-radius:8px;padding:0.8rem 1rem;margin:6px 0;">
                        <span style="color:{score_color};font-weight:700;">Score: {r['score']}</span>
                        &nbsp;&nbsp;
                        <span class="source-pill">{r['source_type']}: {r['source_name']}</span>
                        &nbsp;&nbsp;
                        <span class="badge-info">chunk {r['chunk_index']}</span>
                        <div style="margin-top:6px;font-size:0.9rem;color:#333;">{r['content'][:300]}{'…' if len(r['content'])>300 else ''}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No results found. Try lowering the min_score or uploading more documents.")
        except Exception as e:
            st.error(f"Search failed: {e}")
