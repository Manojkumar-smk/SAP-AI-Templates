"""
============================================================
Router — POST /api/chat
============================================================
Plain LLM chat, no HANA/RAG/SQL involved. This is the
simplest possible AI Core endpoint — good starting point for
understanding how every other router in this service works.
============================================================
"""

from fastapi import APIRouter, HTTPException
from langchain.schema import HumanMessage
from schemas import ChatRequest, ChatResponse
from llm_client import get_llm

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        llm = get_llm()                                    # cached — reused across requests
        response = llm.invoke([HumanMessage(content=req.message)])
        return ChatResponse(answer=response.content.strip())
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Core call failed: {e}")
