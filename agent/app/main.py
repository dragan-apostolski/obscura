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
    """L02: return retrieved chunks for a query."""
    from app.retrieval import retrieve
    return {"query": req.query, "results": retrieve(req.query, req.k)}


@app.post("/ask")
def ask(req: SearchRequest):
    """L03: retrieve → rerank → generate a grounded answer. Becomes the agent in L04."""
    from app.generate import answer
    return {"query": req.query, **answer(req.query, req.k)}
