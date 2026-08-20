<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# AGENTS.md

Orientation for coding agents working in this repo. Humans: start with `README.md`.

## What this is

**Obscura** — the storefront for the camera-store agent. A Next.js App Router site that
renders the product catalog and embeds "The Clerk", a chat dock backed by the FastAPI agent
API. Assistant replies are scanned for catalog products and rendered as inline preview cards
linking to product pages.

Next.js App Router · Tailwind v4 · Framer Motion · TypeScript.

## How the agent is wired

The site never talks to the agent directly from the browser. `src/app/api/chat/route.ts` is a
server-side proxy that:

1. Sends `{message, threadId}` — one message, not a transcript. Conversation state lives
   in the agent, keyed by thread id; the first turn omits the id and adopts the one the
   response carries. Ids are server-issued UUID4s and the API rejects anything else.
2. `POST`s to `${AGENT_API_URL}/ask` with a 120s timeout.
3. Runs `matchProducts()` (`src/lib/match-products.ts`) over the answer text and the agent's
   `tool_calls` to attach product preview cards.
4. Maps agent failures to a friendly `502` — never leaks the upstream error.

The agent also exposes `POST /ask/stream` (server-sent events). The dock does not use it
yet — it waits for the whole answer.

Key files:

```
src/app/api/chat/route.ts        agent proxy — the only place AGENT_API_URL is read
src/components/chat/ChatDock.tsx floating chat panel; mounted in the root layout so it
                                 survives navigation
src/components/chat/chat-bus.ts  window-event bus — any component can open the dock with a
                                 pre-filled prompt, no global state
src/lib/match-products.ts        answer text + tool calls → product cards
src/data/catalog.ts              typed accessors over products.json; image URL base
src/data/products.json           catalog copy (gitignored; see products.example.json)
```

## Run

```bash
npm install
npm run dev        # http://localhost:3000
npm run build
npm run lint
```

Requires the agent API running. Set `AGENT_API_URL` if it is not on `http://127.0.0.1:8000`.

## Conventions

- Server components by default; `"use client"` only where interactivity demands it.
- Tailwind utilities inline. No CSS modules, no styled-components.
- `src/data/products.json` mirrors the agent's catalog — if slugs drift, product preview cards
  silently stop matching. Update both sides together.
- Product images are served from object storage; the base URL lives in `src/data/catalog.ts`
  and must be allow-listed in `next.config.ts` for `next/image`.
- Keep the agent contract in one place. If the API response shape changes, `ChatResponse` in
  `route.ts` is the single point of update.
