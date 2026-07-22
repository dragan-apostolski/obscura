"""FastAPI entrypoint.  Run: uv run uvicorn app.main:app --reload"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Photo RAG Assistant")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query: str
    k: int = 5


@app.post("/search")
def search(req: SearchRequest):
    """Return retrieved chunks for a query."""
    from app.retrieval import retrieve
    return {"query": req.query, "results": retrieve(req.query, req.k)}


@app.post("/ask")
def ask(req: SearchRequest):
    """The main agent — camera-store ReAct: catalog, availability, manuals, technique."""
    from app.agent import ask as agent_ask
    return {"query": req.query, **agent_ask(req.query)}


@app.post("/store/ask")
def store_ask(req: SearchRequest):
    """Backward-compat alias for /ask (the store agent is now the main agent)."""
    from app.agent import ask as agent_ask
    return {"query": req.query, **agent_ask(req.query)}
