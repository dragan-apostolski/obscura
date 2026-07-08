# Photo RAG Assistant

An agentic RAG assistant over photography/videography gear manuals + technique guides —
retrieval-augmented, **evaluated**, and **observable**. Week-1 flagship of the AI-engineering
learning program (see `../PROGRAM.md`).

> Status: **scaffold**. Each lesson fills in a slice. TODO markers below map to the program.

## Stack
| Layer | Choice |
|-------|--------|
| API | FastAPI |
| Agent | LangGraph |
| Vector store | pgvector on Supabase (Postgres) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) — swappable |
| Generation | Claude (Anthropic) |
| Evals | Ragas + DeepEval |
| Observability | Langfuse |
| Deploy | Render / HF Spaces + thin Next.js UI |

## Build order (maps to lessons)
- [ ] **L01** — ingestion: load → chunk → embed → store (`app/ingest.py`, `sql/001_init.sql`)
- [ ] **L02** — vector search + `/search` endpoint (`app/retrieval.py`)
- [ ] **L03** — hybrid search + reranker + naive `/ask`
- [ ] **L04–05** — LangGraph agent + tools (`app/agent.py`)
- [ ] **L06–07** — golden set + Ragas/DeepEval (`evals/`)
- [ ] **L08** — Langfuse tracing
- [ ] **L09–10** — deploy + Next.js UI + showcase

## Setup
```bash
# 1. Install uv if needed:  https://docs.astral.sh/uv/
uv sync

# 2. Copy env and fill in keys
cp .env.example .env

# 3. Create a Supabase project, then run the init SQL (SQL editor or psql):
#    sql/001_init.sql   (enables pgvector + creates the chunks table)

# 4. Drop 2–3 source docs into ./data/ (one manual PDF + one technique article)

# 5. Ingest (L01)
uv run python -m app.ingest

# 6. Run the API
uv run uvicorn app.main:app --reload
```

## Layout
```
app/
  config.py      settings (keys, model names) via pydantic-settings
  db.py          Postgres/pgvector connection + helpers
  chunking.py    text → chunks
  embeddings.py  text → vectors
  ingest.py      L01 pipeline: load → chunk → embed → store
  retrieval.py   L02+ retrieve(query) → chunks
  agent.py       L04+ LangGraph agent (placeholder)
  main.py        FastAPI app + endpoints
sql/001_init.sql schema + pgvector index
data/            source documents (gitignored)
evals/           golden set + eval runners (L06+)
```
