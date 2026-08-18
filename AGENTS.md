# AGENTS.md

Two projects, one repo. Each has its own `AGENTS.md` with the detail that matters for it —
**read the one for the side you are working on before touching anything.**

| Path | What | Read |
|------|------|------|
| `agent/` | FastAPI + LangChain agent, retrieval, evals | [`agent/AGENTS.md`](agent/AGENTS.md) |
| `web/` | Next.js storefront and chat dock | [`web/AGENTS.md`](web/AGENTS.md) |

## Working across both

The two are coupled at exactly two points. Change either side of these and you must change
the other:

- **The `/ask` contract.** `web/src/app/api/chat/route.ts` is the only place the storefront
  talks to the agent. Request and response shapes are defined in `agent/app/schemas.py`.
  Conversation state lives in the agent, keyed by a server-issued `thread_id`; the client
  sends one message and echoes the id back, never a transcript.
- **The product catalog.** `agent/catalog/products.json` is the source; `web/src/data/products.json`
  is a copy. If slugs drift, product preview cards silently stop matching. Update both.

Commands are per-project; run them from inside `agent/` or `web/`, not from the root.

## Conventions

- Name things after what they are, not when they were built. Analysis docs take their
  subject's name, commits describe the change.
- Don't commit `.env` anywhere, or `agent/data/`.
- Keep diffs tight and scoped to the task.
