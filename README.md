# Obscura

A camera store with an agent behind the counter.

**[`agent/`](agent/)** — an agentic RAG backend. A ReAct agent answers customer questions by
routing between the product catalog and a corpus of official camera manuals and photography
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

## Architecture

A request enters the storefront's server-side proxy, which forwards a single message and a
thread id to the agent. The agent decides what to do — it is a ReAct loop, not a fixed
pipeline — calling catalog and retrieval tools until it can answer, then returns text plus
the sources it used.

```
        catalog lookup ──┐
                         ├──►  ReAct agent  ──►  answer + sources
   hybrid retrieval ─────┘      (Claude)
   + rerank
```

Four things carry most of the weight:

**Hybrid retrieval.** pgvector similarity and Postgres full-text search run as two arms of a
single query, fused with Reciprocal Rank Fusion. Metadata filters are pushed into *both*
arms, so a question about one camera cannot surface another camera's manual — a constraint by
construction rather than a post-filter. A cross-encoder then reranks the candidate pool.

**Section-aware chunking.** Manuals are split along their table of contents, and every chunk
is prefixed with its heading path. The section's topic therefore enters both the embedding
and the keyword index, so a passage stays findable even when its body text never uses the
words a customer would.

**Tool docstrings as the control surface.** Nothing hand-wires the routing; the model picks
tools, and their descriptions are all it sees. That makes those docstrings prompt
engineering, and they are regression-tested as such — one example list, read by the model as
an allowlist, silently stopped retrieval for a whole class of question.

**Server-side conversation state.** Turns are checkpointed to Postgres and addressed by a
thread id, so the client sends one message rather than replaying a transcript. Context
editing drops stale tool results once a conversation grows past a threshold.

### Evaluation

A golden set drives three separate layers — retrieval, tool trajectory, and answer quality —
because a good answer over bad retrieval and a bad answer over good retrieval are different
bugs, and a single end-to-end score hides both. `agent/evals/SCORECARD.md` is the running
history, regressions included.

Two bugs that only the harness could have caught: the allowlist reading above, where
correct-sounding answers had no evidence behind them; and an empty-answer bug one model never
triggered and another hit in 13 of 30 traces.

**[Full case study →](https://apostolski-dragan.com/projects/ai-sales-assistant)**

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
