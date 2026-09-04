"""FastAPI boundary. Secrets and model calls remain server-side."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from secrets import compare_digest
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .service import RagService


class HistoryItem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=200)
    task_id: str = Field(pattern="^(task_1|task_2|task_3)$")
    message: str = Field(min_length=1, max_length=8000)
    history: list[HistoryItem] = Field(default_factory=list, max_length=20)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag = RagService.create()
    yield


app = FastAPI(title="Sepid Island RAG", version="0.7.0", lifespan=lifespan)
allowed_origins = [
    item.strip()
    for item in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if item.strip() and "REPLACE_" not in item
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def require_api_access(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """Protect model-backed routes without exposing the secret to browsers."""
    service: RagService = request.app.state.rag
    expected = service.settings.api_shared_secret
    if not expected:
        return
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied or not compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health(request: Request) -> dict:
    service: RagService = request.app.state.rag
    return {
        "status": "ok",
        "environment": service.settings.app_env,
        "source_count": service.retriever.source_count,
        "chunk_count": len(service.retriever.documents),
        "top_k": service.settings.top_k,
        "embedding_model": service.retriever.embeddings.model_identity,
        "llm_provider": service.settings.llm_provider,
    }


@app.post("/chat", dependencies=[Depends(require_api_access)])
def chat(payload: ChatRequest, request: Request) -> dict:
    service: RagService = request.app.state.rag
    request_id = str(uuid4())
    try:
        response = service.chat(
            payload.message,
            payload.task_id,
            [item.model_dump() for item in payload.history],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": str(exc), "request_id": request_id},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "rag_generation_failed", "request_id": request_id},
        ) from exc
    return {
        "request_id": request_id,
        "session_id": payload.session_id,
        "task_id": payload.task_id,
        **response,
    }


@app.get("/debug/retrieve", dependencies=[Depends(require_api_access)])
def debug_retrieve(q: str, request: Request, task_id: str | None = None) -> dict:
    service: RagService = request.app.state.rag
    if not service.settings.enable_debug_retrieval:
        raise HTTPException(status_code=404, detail="Not found")
    if not q.strip():
        raise HTTPException(status_code=400, detail="q cannot be empty")
    return {
        "query": q,
        "results": [
            {
                "source_id": item.source_id,
                "source_ids": list(item.source_ids),
                "chunk_id": item.chunk_id,
                "node_type": item.node_type,
                "topic": item.topic,
                "entities": list(item.entities),
                "parent_ids": list(item.parent_ids),
                "rank": item.rank,
                "score": round(item.score, 6),
                "relative_path": item.relative_path,
            }
            for item in service.retriever.search(q, task_id)
        ],
    }
