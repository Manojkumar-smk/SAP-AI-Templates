"""
============================================================
Router — POST /api/rag-query
============================================================
Document Q&A grounded in HANA Vector Store. Same 4-step
pattern as the hana_rag/rag_pipeline.py mini template:
  retrieve -> format -> generate -> cite sources.
============================================================
"""

from fastapi import APIRouter, HTTPException
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from schemas import RagRequest, RagResponse
from llm_client import get_llm, get_embedding_model
from hana_db import get_connection

router = APIRouter()

RAG_PROMPT = ChatPromptTemplate.from_template("""
Answer the question using ONLY the context below.
If the context doesn't contain the answer, say you don't know.
Context: {context}
Question: {question}
""")


@router.post("/api/rag-query", response_model=RagResponse)
def rag_query(req: RagRequest) -> RagResponse:
    conn = get_connection()
    try:
        embedder = get_embedding_model()
        query_vector = str(embedder.embed_query(req.question))

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP {req.top_k} "SOURCE_NAME", "CONTENT",
                COSINE_SIMILARITY("EMBEDDING", TO_REAL_VECTOR(?)) AS SCORE
            FROM "{req.table_name}" ORDER BY SCORE DESC
        """, (query_vector,))
        rows = cursor.fetchall()
        cursor.close()

        chunks = [{"source_name": r[0], "content": r[1], "score": round(float(r[2]), 4)} for r in rows]
        context = "\n\n".join(f"[{i+1}] {c['content']}" for i, c in enumerate(chunks)) or "No context found."

        llm = get_llm(temperature=0)
        chain = RAG_PROMPT | llm | StrOutputParser()
        answer = chain.invoke({"context": context, "question": req.question}).strip()

        return RagResponse(answer=answer, sources=chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"RAG query failed: {e}")
    finally:
        conn.close()
