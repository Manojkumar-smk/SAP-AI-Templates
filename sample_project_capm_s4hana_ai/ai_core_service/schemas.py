"""
============================================================
Pydantic Schemas — request/response shapes for every endpoint
============================================================
Use this when: you want a single place that defines exactly
what JSON each AI Core service endpoint accepts and returns.
FastAPI uses these classes to auto-validate requests and to
generate the OpenAPI docs at /docs.
============================================================
"""

from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str                          # the user's plain-English message
    conversation_id: Optional[str] = None # lets CAP correlate this call with a stored Conversation


class ChatResponse(BaseModel):
    answer: str
    mode: str = "CHAT"


class RagRequest(BaseModel):
    question: str
    table_name: str = "VECTOR_STORE"      # HANA vector table to search (see hana_vector_store templates)
    top_k: int = 5


class RagResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    mode: str = "RAG"


class SqlQueryRequest(BaseModel):
    question: str
    tables: List[str]                     # which HANA tables the LLM is allowed to query


class SqlQueryResponse(BaseModel):
    sql: str
    row_count: int
    rows: List[dict]
    mode: str = "SQL"


class OrchestrateRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    detect_posting_intent: bool = True    # if True, also classifies whether this is a "create/post" request


class OrchestrateResponse(BaseModel):
    answer: str
    mode: str = "ORCHESTRATE"
    is_posting_intent: bool = False       # tells CAP whether it should call the S/4HANA RAP action next
    posting_payload: Optional[dict] = None  # structured fields extracted for the S/4HANA posting call
