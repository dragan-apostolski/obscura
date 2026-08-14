# Camera Store Assistant

An agentic RAG backend for a camera retailer. A ReAct agent answers customer questions by
routing between a 65-product catalog and a corpus of 65 official camera manuals plus
photography technique guides — then grounds every answer in what it retrieved.

Built as a working system rather than a demo: hybrid retrieval with a reranker, a
three-layer evaluation suite, and full request tracing.

```
Customer: "Do you have the a7 IV in stock, and how do I change its ISO?"

→ search_products("a7 IV")     → sony-a7-iv | Sony a7 IV | … | in stock | manual: yes
→ search_manual("change ISO sensitivity", "sony-a7-iv")
→ answer, citing the manual section it used
```

## How it works

```
data/  →  ingest  →  chunks (pgvector)
                         ↓
              hybrid retrieve — vector + keyword, fused with RRF
                         ↓
                    cross-encoder rerank
                         ↓
                   ReAct agent (Claude)
                   tools: search_products, get_product_info,
                          search_manual, explain_technique
                         ↓
                POST /ask · POST /ask/stream
```

**Conversation state.** Turns are checkpointed to Postgres and addressed by `thread_id`,
so a follow-up resolves against what was actually said rather than against a transcript the
client reassembles and resends. That moves the source of truth server-side; it does not make
history free — persisted turns are still replayed to the model, and tool results dominate
them. A manual search is roughly 2k tokens, so context editing drops stale tool outputs once
a conversation crosses a threshold, keeping the recent ones and the dialogue itself.

**Retrieval.** Two arms run in one SQL statement — pgvector cosine similarity and Postgres
full-text search — merged by Reciprocal Rank Fusion. Metadata filters (`product`, `doc_type`)
are pushed into *both* arms, so a question about one camera can never surface another
camera's manual. A cross-encoder then re-scores the candidate pool.

**Chunking.** PDF manuals with a usable table of contents are split along it, and each chunk
is prefixed with its heading path (`[nikon-z6-ii manual — Menu Guide > The Photo Shooting
Menu: Shooting Options > Time-Lapse Movie]`). The section's topic therefore enters both the
embedding and the keyword index even when the body text never uses the user's vocabulary.

**The agent.** Tool selection is the model's job, not a hand-wired graph. That makes the tool
docstrings the real control surface — they are treated as prompt engineering and are
regression-tested (see below for why).

## Evaluation

A 27-row golden set drives three layers, each isolating a different failure mode:

| Layer | Measures | Method |
|-------|----------|--------|
| Retrieval | Did the right chunk come back? | context precision/recall, judged |
| Trajectory | Did the agent call the right tools? | deterministic asserts + judged asserts |
| Answer | Is the answer faithful and relevant? | Ragas, with a cross-model judge |

Layers are separated because a good answer over bad retrieval and a bad answer over good
retrieval are different bugs with different fixes — a single end-to-end score hides both.
References are written from the source documents, never copied from an agent answer, so the
set cannot silently grade the system against itself.

`evals/SCORECARD.md` is the running before/after history. Two findings from it worth calling
out, both caught by the harness rather than by eye:

- **A tool docstring's example list was read as an allowlist.** Concept questions whose
  keyword appeared literally in `explain_technique`'s topic list triggered retrieval; ones
  that didn't were answered from the model's own knowledge — faithfulness 0.00 behind
  correct-sounding text. The trailing ellipsis meant nothing. Fixed by replacing the
  enumeration with a scope statement that marks its examples as non-exhaustive.
- **A latent bug that only one model exposed.** `/ask` occasionally returned an empty answer,
  because the reply was written *alongside* the tool call and the final turn was empty. The
  code read the last message blindly. One model never hit it; another hit it in 13 of 30
  traces.

Swapping the generation model to Claude Haiku 4.5 cut median request latency from 12.6s to
4.6s while trajectory asserts went from 15/17 to 15/15 — latency measured from trace data,
not vendor figures. Full reasoning, including the regressions the swap caused and the
caveats on the comparison, is in the scorecard.

## Setup

Requires Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), and a Postgres database with
pgvector (Supabase works out of the box).

```bash
uv sync
cp .env.example .env          # DATABASE_URL, ANTHROPIC_API_KEY

# Schema, in order
psql "$DATABASE_URL" -f sql/001_init.sql
psql "$DATABASE_URL" -f sql/002_keyword_search.sql
psql "$DATABASE_URL" -f sql/003_product_catalog.sql

# Add source documents to ./data, then
uv run python -m app.ingest
uv run uvicorn app.main:app --reload
```

Embeddings (`bge-small-en-v1.5`) and reranking (`bge-reranker-large`) run locally — no
embedding API key, no per-query retrieval cost. Only generation and the eval judge call out.

```bash
# one-shot; the response carries a thread_id
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query": "Does the Nikon Z8 have IBIS?"}'

# continue that conversation
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"query": "And is it in stock?", "thread_id": "<id from above>"}'

# same thing as server-sent events: {"type":"tool"|"token"|"done", ...}
curl -N -X POST localhost:8000/ask/stream -H 'content-type: application/json' \
  -d '{"query": "Which Fujifilm cameras do you have?"}'
```

### Running the evals

```bash
uv run python -m evals.retrieval_eval          # retriever only — no agent in the loop
uv run python -m evals.run_eval --skip-ragas   # + trajectory asserts
uv run python -m evals.run_eval                # full run, including the judge
uv run python -m evals.run_eval --from-runs    # rescore cached runs
```

Results land in `evals/results/<timestamp>-*.md`.

## Layout

```
app/
  config.py            settings — keys, model names, chunk sizes
  db.py                psycopg 3 + pgvector
  chunking.py          token-aware splits
  embeddings.py        local sentence-transformers
  textclean.py         repairs PDF extraction artifacts
  ingest.py            load → chunk → embed → store
  retrieval.py         vector + hybrid search
  rerank.py            cross-encoder rerank
  tools.py             agent tools — docstrings carry the routing rules
  agent.py             the ReAct agent
  schemas.py           request + response models
  main.py              FastAPI app, lifespan, endpoints
sql/                   schema migrations
catalog/               product seed data
evals/                 golden set, harnesses, scorecard, run history
```

## Stack

FastAPI · LangChain / LangGraph · Postgres + pgvector · sentence-transformers ·
Claude · Ragas · Langfuse

## Known limitations

- The reranker mis-scores some rows — off-topic chunks occasionally outrank the right ones
  (`g02`, `g09`).
- Stabilisation questions are answered from a manual's specification tables rather than its
  dedicated feature section, which still doesn't rank. Correct answers, thinner grounding.
- Tool selection is probabilistic. A docstring shapes how likely a call is; it does not
  guarantee one. Making retrieval deterministic for a class of question needs a system-prompt
  rule, not a better description.
- The catalog is synthetic and contains one deliberate inconsistency (Nikon Z6 II video
  specs), kept as an eval fixture.
- No unit tests yet. Behaviour is covered by the eval suite, which needs a database and a
  model API; `tests/README.md` sets out the hermetic layer that should sit under it.
