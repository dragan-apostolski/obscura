# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A week-1 flagship portfolio project: an agentic RAG assistant over photography/videography gear manuals + technique guides. The corpus is real; the camera store (`/store/ask`) is a synthetic layer on top to demo catalog lookup, stock/pricing, and tool routing — not just document Q&A. Part of the `learn-ai-engineering` curriculum (`../MISSION.md`, `../PROGRAM.md`); this subproject has its own git repo, separate from the parent.

Success criteria: deployed URL, eval suite with metric-backed wins, Langfuse traces, showcase README.

## Commands

```bash
uv sync
cp .env.example .env          # fill DATABASE_URL, ANTHROPIC_API_KEY

# Schema (Supabase SQL editor, run in order): sql/001_init.sql → 002 → 003
uv run python -m app.ingest
uv run uvicorn app.main:app --reload

pytest                                            # tests
uv run python -m evals.run_eval --only g01,g13    # smoke eval
uv run python -m evals.run_eval --skip-ragas      # deterministic asserts only
uv run python -m evals.run_eval                   # full run → evals/l06-ragas-baseline.md

uv run ruff check app evals                       # lint, line length 100
```

## Architecture

```
data/  →  ingest  →  chunks (pgvector)
                         ↓
              hybrid_retrieve (vector + keyword, sql/002)
                         ↓
                    rerank (cross-encoder)
                         ↓
        ┌────────────────┴────────────────┐
        ↓                                 ↓
  L04 StateGraph                   L05 ReAct agent
  retrieve→grade→rewrite→answer    tools: search_products,
  POST /ask                        get_product_info,
                                   search_manual, explain_technique
                                   POST /store/ask
```

`POST /store/ask` is the primary demo path. `POST /ask` (LangGraph agent) remains for eval comparison and Ragas baselines.

Product catalog lives in the `products` table + `catalog/products.json`, seeded via `sql/003_product_catalog.sql`. Manual slugs in `MANUAL_META` (`app/ingest.py`) must match `products.slug`.

## Stack

FastAPI · LangGraph (L04 graph) + LangChain `create_agent` (L05 ReAct) · Supabase Postgres + pgvector · local `BAAI/bge-small-en-v1.5` embeddings (384-dim, no OpenAI key needed) · local `BAAI/bge-reranker-base` · Claude via Anthropic SDK / `langchain-anthropic` · Ragas + deterministic asserts for evals · Langfuse for tracing (not yet instrumented). Package manager: uv, Python ≥ 3.11.

## Module layout

```
app/
  config.py       pydantic-settings (.env) — never hardcode keys or model names
  db.py           psycopg + pgvector helpers
  chunking.py     token-aware splits (tiktoken)
  embeddings.py   local sentence-transformers
  ingest.py       load PDFs/HTML/txt → store
  retrieval.py    vector + hybrid search
  rerank.py       cross-encoder rerank
  agent.py        LangGraph agent (retrieve → grade → rewrite loop → answer)
  store_agent.py  ReAct store agent
  tools.py        tool definitions — docstrings are routing logic; treat edits as prompt engineering
  main.py         FastAPI endpoints
sql/              schema migrations, run in order in Supabase
catalog/          product seed data
evals/            golden set, harness, run logs (l03–l06-*.md)
data/             source docs (gitignored)
```

## Conventions

- Match existing patterns: plain functions, minimal abstraction, module-level clients where already used.
- Don't commit `.env` or `data/`. Don't change embedding model/dim without a migration plan (384-dim index in `001_init.sql`).
- `evals/golden.jsonl`: multi-line JSON objects (not strict JSONL), ~29 rows with `scoring` of `ragas`, `deterministic`, or `behavioral`. References must be built source → reference, never copied from agent answers (see `evals/golden-references-review.md`). Keep page numbers out of reference text — breaks Ragas context recall.
- `evals/run_eval.py` has a Vertex AI compat shim — leave it unless upgrading ragas/langchain-community.
- `.mcp.json` configures Supabase MCP for this project (`project_ref=fynxpcweahncdwywphnj`).

## Testing changes

1. Hit `/health`, then the relevant endpoint (`/search`, `/ask`, `/store/ask`).
2. For agent changes, run a small eval subset before full Ragas (costs judge tokens).
3. Log results in `evals/l0N-*.md` following the existing run-log format.

## Known open issues (from L05 log)

- Ungrounded spec claims when the manual lacks the fact — agent should say "not in manual", not invent.
- X100V manual exists but the agent sometimes declines film-simulation questions.
- Scope refusal followed by answering anyway on off-topic questions.
- `g24`: `reference_verified: false` — spec numbers need catalog verification.
