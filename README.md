# Obscura

A camera store with an agent behind the counter.

**[`agent/`](agent/)** — an agentic RAG backend. A ReAct agent answers customer questions by
routing between a 65-product catalog and 65 official camera manuals plus photography
technique guides, grounding every answer in what it retrieved. FastAPI, hybrid retrieval over
pgvector with a cross-encoder reranker, conversations checkpointed to Postgres, and a
three-layer evaluation suite.

**[`web/`](web/)** — the storefront. Next.js App Router, with a chat dock wired to the agent
that renders product cards for anything it mentions.

```
                 web/  ──────►  agent/  ──────►  Postgres + pgvector
              Next.js          FastAPI            manuals, catalog,
              chat dock        ReAct agent        conversation state
                                  │
                                  ▼
                            Claude · Langfuse
```

## Why it's interesting

The retrieval is hybrid — pgvector similarity and Postgres full-text search fused with
Reciprocal Rank Fusion in a single query, with metadata filters pushed into both arms so one
camera's question can never surface another camera's manual. Manuals are chunked along their
table of contents and each chunk carries its heading path, so a section's topic is searchable
even when its body text never uses the reader's words.

The evaluation suite is the part worth reading. A 27-row golden set drives three separate
layers — retrieval, tool trajectory, and answer quality — because a good answer over bad
retrieval and a bad answer over good retrieval are different bugs, and one end-to-end score
hides both. `agent/evals/SCORECARD.md` is the running history, including the regressions.

Two findings from it that only the harness could have caught: a tool docstring's example list
being read as an allowlist, so questions whose keyword wasn't literally present were answered
from the model's own knowledge with nothing behind them; and an empty-answer bug that one
model never triggered and another hit in 13 of 30 traces.

## Running it

Each side has its own README and its own setup. The agent needs Postgres with pgvector and an
Anthropic key; the storefront needs the agent running.

```bash
cd agent && uv sync && uv run uvicorn app.main:app --reload
cd web   && npm install && npm run dev
```

## Layout

```
agent/    FastAPI + LangChain backend, evals, SQL migrations
web/      Next.js storefront
```

The catalog, pricing and stock are fictional. The camera manuals are the manufacturers'.
