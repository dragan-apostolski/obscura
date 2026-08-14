# AGENTS.md

Orientation for coding agents working in this repo. Humans: start with `README.md`.

## What this is

An agentic RAG assistant over camera manuals and photography technique guides, served as a
FastAPI app. A ReAct agent picks between four tools — catalog search, product lookup,
manual search, and technique search — and answers from what they return. The manual and
technique corpus is real; the camera store (catalog, prices, stock) is synthetic, so the
agent has to do routing and grounding, not just document Q&A.

Retrieval is hybrid (vector + keyword, fused with RRF) over pgvector, followed by a
cross-encoder rerank. Answers are evaluated with a golden set — Ragas metrics plus
deterministic asserts — and every run is traced to Langfuse.

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI (`app/main.py`) |
| Agent | LangChain `create_agent` (ReAct) — `app/agent.py` |
| DB | Postgres + pgvector (Supabase) |
| Embeddings | Local `BAAI/bge-small-en-v1.5` (384-dim) — no embedding API key needed |
| Reranker | Local cross-encoder `BAAI/bge-reranker-large` |
| Generation | Claude (`claude-haiku-4-5`) via `langchain-anthropic` |
| Evals | Ragas + deterministic asserts (`evals/run_eval.py`), Gemini as judge |
| Observability | Langfuse — spans, session grouping, trace ids |

Package manager: **uv**. Python ≥ 3.11. Exact model names and dims live in `app/config.py`,
which is the source of truth — don't duplicate them here or anywhere else.

## Architecture

```
data/  →  ingest  →  chunks (pgvector)
                         ↓
              hybrid_retrieve (vector + keyword + RRF, sql/002)
                         ↓
                    rerank (cross-encoder)
                         ↓
                   ReAct agent (app/agent.py)
                   tools: search_products, get_product_info,
                          search_manual, explain_technique
                         ↓
                   POST /ask
```

Endpoints: `GET /health`, `POST /search` (retriever only, no agent), `POST /ask` (the agent),
`POST /ask/stream` (the same, as server-sent events), `POST /store/ask` (alias of `/ask`,
kept for the storefront client).

**Conversation state.** History lives in Postgres via a LangGraph checkpointer, keyed by
`thread_id` — clients send one message, not a replayed transcript. Ids are server-issued
UUID4s and a client may only echo one back; a thread id is a bearer token for a conversation,
so client-invented ids are rejected. Omitting `thread_id` starts a fresh thread and returns
its id. Eval rows each get their own thread so one row cannot contaminate the next.

Persisted history is still resent to the model on every turn, tool results included, so
`ContextEditingMiddleware` drops stale tool outputs past `context_edit_trigger_tokens`.
Without it a long conversation grows until it hits the context limit. Checkpointing is not
a token optimisation — it is a correctness and ownership one.

The product catalog lives in the `products` table plus `catalog/products.json`, seeded by
`sql/003_product_catalog.sql`. Manual slugs in `MANUAL_META` (`app/ingest.py`) must match
`products.slug` — a mismatch silently breaks `search_manual`.

## Layout

```
app/
  config.py            pydantic-settings from .env — keys, model names, chunk sizes
  db.py                psycopg 3 + pgvector helpers
  chunking.py          token-aware splits (tiktoken)
  embeddings.py        local sentence-transformers; embed_query() applies the bge prefix
  textclean.py         repairs PyMuPDF ligature-spacing artifacts in extracted PDF text
  ingest.py            load PDFs/HTML/txt → section-aware chunks → embed → store
  retrieval.py         vector search + hybrid search (RRF, metadata-filtered)
  rerank.py            cross-encoder rerank of the candidate pool
  tools.py             agent tool definitions — docstrings carry the routing rules
  agent.py             the ReAct agent; ask() / astream() serve, ask_traced() adds eval data
  schemas.py           request + response models — the API contract
  main.py              FastAPI app, lifespan, middleware, endpoints
sql/                   schema migrations, run in order
catalog/               product seed data
evals/                 golden set, harnesses, scorecard, run history
data/                  source documents (gitignored)
```

## Commands

```bash
uv sync
cp .env.example .env          # fill DATABASE_URL, ANTHROPIC_API_KEY

# Schema — run in order: sql/001_init.sql → 002 → 003
uv run python -m app.ingest                       # all of ./data
uv run python -m app.ingest nikon-z8-manual.pdf   # re-ingest one file
uv run uvicorn app.main:app --reload

# Evals — results land in evals/results/<stamp>-*.{md,json}
uv run python -m evals.retrieval_eval             # retriever only — no agent, but the judge scores it
uv run python -m evals.run_eval --only g01,g23    # smoke a subset
uv run python -m evals.run_eval --skip-ragas      # deterministic asserts only
uv run python -m evals.run_eval --from-runs       # rescore cached runs, no agent calls
uv run python -m evals.run_eval                   # full run

uv run ruff check app evals
```

## Conventions

### Code
- Match what's there: plain functions, minimal abstraction.
- **Nothing expensive at import time.** Models and pools are built on first use and warmed
  in the lifespan — both models, the query pool and the agent. A module-level
  `SentenceTransformer(...)` is how you make the app un-runnable with more than one worker.
  Lazy globals reached from tools need a lock: tools execute in the thread pool, so first
  calls race across threads, not just tasks.
- The agent path is async end to end. The checkpointer is async-only; don't add a sync twin.
- All configuration through `app.config.settings`. Never hardcode a key, model name, or dim.
- **Tool docstrings in `app/tools.py` are routing logic.** The model sees nothing else about
  a tool. Treat edits there as prompt engineering and re-run evals — a topic list read as an
  allowlist has already caused a silent retrieval regression (see `evals/SCORECARD.md`).
- Ruff, line length 100. Run from the repo root.

### Scope
- Keep diffs tight and focused; don't refactor modules the task didn't touch.
- Never commit `.env` or `data/`.
- Don't change the embedding model or dim without a migration plan — `001_init.sql` builds a
  384-dim HNSW index.

### Eval golden set
- `evals/golden.jsonl` — 27 rows of multi-line JSON objects (not strict JSONL). Each has a
  `scoring` of `ragas`, `deterministic`, or `behavioral`.
- References must be written **source → reference**, never copied from an agent answer.
  Rationale and the audit trail are in `evals/golden-references-review.md`.
- Keep page numbers out of reference text — they break Ragas context recall.
- `evals/run_eval.py` carries a Vertex AI compatibility shim. Leave it unless you are
  deliberately upgrading ragas or langchain-community.
- `evals/SCORECARD.md` is the curated before/after history. Add an entry for any change that
  moves a metric; individual runs stay in `evals/results/`.
- **Naming:** harness output is timestamped automatically (`results/<stamp>-{e2e,retrieval}.*`)
  — don't rename it. A hand-written analysis doc is named after its subject
  (`retrieval-baseline.md`, `store-agent-run-log.md`), never after a sequence number, date, or
  iteration index. Scorecard entries are headed by what changed, with the date after it.

## Testing changes

1. Hit `/health`, then the endpoint you touched (`/search`, `/ask`).
2. For agent or tool changes, run a small eval subset before a full Ragas pass — the judge
   costs tokens.
3. For retrieval-only changes, `retrieval_eval.py` is the fast loop — it takes the agent out of
   the picture, though it still spends judge tokens on context precision/recall.
4. Record anything that moves a metric in `evals/SCORECARD.md`.

## Known open issues

- The reranker mis-scores some rows: off-topic chunks outrank the right ones (reproducible on
  `g02`, shutter speed).
- `g23` (Z8 IBIS) answers from the manual's *Specifications* table, not the dedicated
  *Vibration Reduction* section, which still doesn't rank — context recall sits at 0.67.
  The row passes; the grounding is thinner than it should be.
- `get_product_info`'s docstring mentions "spec comparisons", so the agent reaches for it on
  feature questions ("does it have IBIS") that belong in the manual rather than the sparse
  catalog `specs` field.
- The catalog contradicts itself on Nikon Z6 II video: description says 4K 60p, specs say
  4K 30p.
- No test suite yet — see `tests/README.md` for what it should cover.
- `/ask/stream` has no client: the storefront still uses the blocking `/ask`. It also
  streams every AI message, so it shows pre-tool-call preamble that `/ask` omits — the two
  endpoints can return different text for the same question.
- Checkpoints are never pruned. Every one-shot `/ask` and every eval row writes a thread
  that stays forever; `sql/004_checkpoint_retention.sql` has the cleanup.
- The API never returns tool calls, so the storefront's slug-based product matching
  (`matchProducts`, second argument) has never had data to work with — it matches on
  answer text alone.
