# AGENTS.md — Photo RAG Assistant

Agent orientation for this repo. Part of the [learn-ai-engineering](../) curriculum — see `../MISSION.md`, `../PROGRAM.md`, and `../NOTES.md` for learner goals and teaching style.

## What this is

A **week-1 flagship portfolio project**: an agentic RAG assistant over photography/videography gear manuals + technique guides. The corpus is real; the **camera store** (`/store/ask`) is a synthetic layer on top so we can demo catalog lookup, stock/pricing, and tool routing — not just document Q&A.

**Success criteria:** deployed URL, eval suite with metric-backed wins, Langfuse traces, showcase README.

## Learner context

- Senior full-stack engineer learning the **application layer** (RAG, agents, evals, observability) — not ML theory.
- Wants concepts explained briefly **before** building; then targeted review, not hand-holding.
- **Concise, peer-level** communication. Propose and move; don't ask lots of clarifying questions.
- Each lesson should leave something that **runs**. Evals (L06–07) are non-negotiable — never cut them.

## Current progress

| Lesson | Topic | Status |
|--------|-------|--------|
| L01 | Ingestion pipeline | ✅ `app/ingest.py`, `sql/001_init.sql` |
| L02 | Vector search + `/search` | ✅ `app/retrieval.py` |
| L03 | Hybrid search + rerank + naive generate | ✅ `app/rerank.py`, hybrid in `retrieval.py` |
| L04 | LangGraph agent + `/ask` | ✅ `app/agent.py` — retrieve → grade → rewrite loop → answer |
| L05 | ReAct store agent + `/store/ask` | ✅ `app/store_agent.py`, `app/tools.py`, `sql/003_product_catalog.sql` |
| L06 | Golden set + Ragas harness | ✅ `evals/golden.jsonl` (29 rows), `evals/run_eval.py` |
| L07 | Eval-driven iteration + DeepEval CI | 🔲 |
| L08 | Langfuse tracing | 🔲 keys in `config.py`, not wired |
| L09 | Deploy + thin Next.js UI | 🔲 |
| L10 | Showcase (README, GIF, LinkedIn draft) | 🔲 |

**Active agent surface:** `POST /store/ask` is the primary demo path. `POST /ask` (L04 graph) remains for eval comparison and Ragas baselines.

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI (`app/main.py`) |
| Agents | LangGraph (L04 graph), LangChain `create_agent` (L05 ReAct) |
| DB | Supabase Postgres + pgvector |
| Embeddings | Local `BAAI/bge-small-en-v1.5` (384-dim) — no OpenAI key needed |
| Reranker | Local `BAAI/bge-reranker-base` |
| Generation | Claude via Anthropic SDK / `langchain-anthropic` |
| Evals | Ragas + deterministic asserts in `evals/run_eval.py` |
| Observability | Langfuse (L08, not yet instrumented) |

Package manager: **uv**. Python ≥ 3.11.

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

**Product catalog** lives in `products` table + `catalog/products.json`, seeded via `sql/003_product_catalog.sql`. Manual slugs in `MANUAL_META` (`app/ingest.py`) must match `products.slug`.

## Layout

```
app/
  config.py       pydantic-settings (.env)
  db.py           psycopg + pgvector helpers
  chunking.py     token-aware splits (tiktoken)
  embeddings.py   local sentence-transformers
  ingest.py       L01: load PDFs/HTML/txt → store
  retrieval.py    vector + hybrid search
  rerank.py       cross-encoder rerank
  agent.py        L04 LangGraph agent
  store_agent.py  L05 ReAct store agent
  tools.py        L05 tool definitions (docstrings = routing rules)
  main.py         FastAPI endpoints
sql/              schema migrations (run in order in Supabase)
catalog/          product seed data
evals/            golden set, harness, run logs (l03–l06-*.md)
data/             source docs (gitignored)
```

## Commands

```bash
uv sync
cp .env.example .env          # fill DATABASE_URL, ANTHROPIC_API_KEY

# Schema (Supabase SQL editor): sql/001_init.sql → 002 → 003
uv run python -m app.ingest
uv run uvicorn app.main:app --reload

# Evals
uv run python -m evals.run_eval --only g01,g13   # smoke
uv run python -m evals.run_eval --skip-ragas     # asserts only
uv run python -m evals.run_eval                  # full run → evals/l06-ragas-baseline.md
```

## Conventions for agents

### Code style
- Match existing patterns: plain functions, minimal abstraction, module-level clients where already used.
- Settings via `app.config.settings` — never hardcode keys or model names.
- Tool **docstrings are routing logic** in L05 — treat edits there as prompt engineering.
- Ruff line length 100. Run from repo root with `uv run ruff check app evals`.

### Scope discipline
- **Minimize diff** — this is a learning repo; one lesson's slice at a time.
- Don't refactor unrelated modules. Don't add features from future lessons without being asked.
- Don't commit `.env` or `data/`. Don't change embedding model/dim without a migration plan (384-dim index in `001_init.sql`).

### Eval golden set
- `evals/golden.jsonl` — multi-line JSON objects (not strict JSONL). ~29 rows with `scoring`: `ragas`, `deterministic`, `behavioral`.
- References must be built **source → reference**, never copied from agent answers. See `evals/golden-references-review.md`.
- Keep page numbers out of reference text (breaks Ragas context recall).
- `evals/run_eval.py` has a Vertex AI compat shim — leave it unless upgrading ragas/langchain-community.

### Known open issues (from L05 log)
- **F1:** Ungrounded spec claims when manual lacks the fact — agent should say "not in manual" not invent.
- **F3:** X100V manual exists but agent sometimes declines film-simulation questions.
- **F4:** Scope refusal then answers anyway on off-topic questions.
- **g24:** `reference_verified: false` — spec numbers need catalog verification.

### Skills to load (from `../.agents/skills/`)
- **Always start agent work:** `ecosystem-primer`
- RAG/retrieval: `langchain-rag`
- LangGraph (L04): `langgraph-fundamentals`, `langgraph-human-in-the-loop`
- LangChain agents (L05): `langchain-fundamentals`
- Evals: read `evals/run_eval.py` + Ragas docs; no dedicated skill yet
- Supabase/Postgres: `supabase`, `supabase-postgres-best-practices`
- Deploy (L09): TBD

### MCP
- `.mcp.json` configures Supabase MCP for this project (`project_ref=fynxpcweahncdwywphnj`).

## Testing changes

1. Hit `/health`, then the relevant endpoint (`/search`, `/ask`, `/store/ask`).
2. For agent changes, run a **small eval subset** before full Ragas (costs judge tokens).
3. Log results in `evals/l0N-*.md` following existing run-log format.
4. Use `@browser` for any UI work (L09+), not curl.

## Parent repo

Lessons live in `../lessons/`. Reference cheat sheets in `../reference/` (when created). This subproject has its **own git repo** — commits here are separate from `learn-ai-engineering`.

## Session context from prior tools

Claude Code history for this project is **not** auto-loaded. If continuing work from Claude Code sessions, see `docs/SESSION_CONTEXT.md` (if present) or ask the user to `@`-mention exported transcripts. Distilled decisions beat raw chat dumps.
