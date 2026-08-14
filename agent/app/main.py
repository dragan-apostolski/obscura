"""FastAPI entrypoint.  Run: uv run uvicorn app.main:app --reload"""
import json
import logging
import uuid
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app import embeddings, rerank
from app.agent import ask as agent_ask
from app.agent import astream as agent_astream
from app.agent import close_agent, get_agent
from app.db import close_pool, get_pool
from app.retrieval import retrieve
from app.schemas import AskRequest, AskResponse, ErrorResponse, SearchRequest

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pay the expensive costs at startup, not on the first request.

    The embedding and reranker models are loaded here, off the event loop — each is
    hundreds of MB and every worker process holds its own copy. Building the agent also
    creates the checkpointer's tables if they don't exist yet. Opening the query pool
    here too means the first concurrent requests don't race to create it.
    """
    await anyio.to_thread.run_sync(embeddings.warmup)
    await anyio.to_thread.run_sync(rerank.warmup)
    await anyio.to_thread.run_sync(get_pool)
    await get_agent()
    log.info("startup complete: models loaded, pool open, agent ready")
    yield
    await close_agent()
    await anyio.to_thread.run_sync(close_pool)


app = FastAPI(title="Camera Store Assistant", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Tag every request so a user-visible error can be matched to a server log line."""
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log the detail, return an opaque message. Stack traces are not a public API."""
    request_id = getattr(request.state, "request_id", "unknown")
    log.exception("unhandled error [request_id=%s]", request_id)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal error.", request_id=request_id).model_dump(),
        headers={"x-request-id": request_id},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/search")
async def search(req: SearchRequest) -> dict:
    """Retrieved chunks for a query — the retriever alone, no agent."""
    results = await anyio.to_thread.run_sync(retrieve, req.query, req.k)
    return {"query": req.query, "results": results}


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Ask the store agent. Pass a thread_id to continue an existing conversation."""
    result = await agent_ask(req.query, req.thread_id)
    return AskResponse(query=req.query, **result)


@app.post("/ask/stream")
async def ask_stream(req: AskRequest) -> StreamingResponse:
    """Server-sent events: answer tokens as the model writes them, plus a `tool` event
    whenever the agent starts a tool call, so a slow turn isn't a silent one."""
    async def events():
        try:
            async for event in agent_astream(req.query, req.thread_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:
            log.exception("stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Stream failed.'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


@app.post("/store/ask", response_model=AskResponse)
async def store_ask(req: AskRequest) -> AskResponse:
    """Alias of /ask, kept for the storefront client."""
    return await ask(req)
