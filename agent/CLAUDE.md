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

uv run python -m evals.retrieval_eval             # retriever only, no agent → evals/results/<stamp>-retrieval.md
uv run python -m evals.run_eval --only <ids>      # smoke eval on a subset
uv run python -m evals.run_eval --skip-ragas      # deterministic asserts only
uv run python -m evals.run_eval --from-runs       # rescore cached runs, no agent calls
uv run python -m evals.run_eval                   # full agent run → evals/results/<stamp>-e2e.md

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
                         ↓
                  L05 ReAct store agent
                  tools: search_products, get_product_info,
                         search_manual, explain_technique
                  POST /ask · POST /store/ask (alias)
```

The L04 StateGraph (`app/manual_rag_agent.py`, retrieve→grade→rewrite→answer) is deprecated — kept for comparison only, no endpoint.

Product catalog lives in the `products` table + `catalog/products.json`, seeded via `sql/003_product_catalog.sql`. Manual slugs in `MANUAL_META` (`app/ingest.py`) must match `products.slug`.

## Stack

FastAPI · LangGraph (L04 graph) + LangChain `create_agent` (L05 ReAct) · Supabase Postgres + pgvector · local sentence-transformer embeddings (no OpenAI key needed) · local cross-encoder reranker · Claude via Anthropic SDK / `langchain-anthropic` · Ragas + deterministic asserts for evals · Langfuse for tracing. Package manager: uv, Python ≥ 3.11. Exact model names/dims live in `app/config.py`, the source of truth — don't duplicate them here.

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
  agent.py          ReAct store agent — `ask()` is the API contract, `ask_traced()` adds the eval trace
  manual_rag_agent.py  deprecated L04 graph (retrieve → grade → rewrite → answer)
  tools.py          tool definitions — docstrings are routing logic; treat edits as prompt engineering
  main.py           FastAPI endpoints
sql/              schema migrations, run in order in Supabase
catalog/          product seed data
evals/            golden set, harness, run logs (l03–l07-*.md)
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

## Known open issues (L07)

- Reranker mis-scores some rows: off-topic chunks outrank the right ones (seen on `g02`, shutter speed).
- `search_manual` never surfaces the Z8 vibration-reduction page (`g23`) — a real retrieval miss.
- `get_product_info`'s docstring says "spec comparisons", so the agent uses it for feature
  questions ("does it have IBIS") that belong in the manual, not the sparse catalog `specs`.
- Catalog contradicts itself on Z6 II video (description 4K 60p vs specs 4K 30p).
- No tests exist yet — `pytest` collects nothing.
