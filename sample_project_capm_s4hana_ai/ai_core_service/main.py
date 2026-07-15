"""
============================================================
AI Core Service — FastAPI entry point
============================================================
This is the Python microservice that exposes every SAP AI
Core capability as a REST endpoint. It is deployed as its OWN
standalone Cloud Foundry app (see manifest.yml) and is called
by the CAP middleware (capm_middleware/) — never directly by
the UI5 app.

Endpoints:
  POST /api/chat         -> plain LLM chat
  POST /api/rag-query    -> document Q&A via HANA Vector Store
  POST /api/sql-query    -> natural language -> SQL -> HANA rows
  POST /api/orchestrate  -> safe chat + posting-intent detection
                             (this is the one the assistant flow uses)
  GET  /health            -> liveness check for CF

Run locally:
  pip install -r requirements.txt
  cp .env.example .env   (fill in AICORE_* + HANA_* values)
  uvicorn main:app --reload --port 8000

Deploy to Cloud Foundry:
  cf push   (uses manifest.yml in this folder)
============================================================
"""

from fastapi import FastAPI
from routers import chat, rag, sql_query, orchestrate

app = FastAPI(
    title="SAP AI Core Service",
    description="REST API over SAP AI Core — chat, RAG, NL-to-SQL, and safe orchestration.",
    version="1.0.0",
)

# Each router owns one capability — see routers/*.py for the implementation of each.
app.include_router(chat.router,        tags=["chat"])
app.include_router(rag.router,         tags=["rag"])
app.include_router(sql_query.router,   tags=["sql"])
app.include_router(orchestrate.router, tags=["orchestrate"])


@app.get("/health")
def health():
    return {"status": "UP"}
