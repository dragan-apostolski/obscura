# Obscura — Fine Camera Supply

Storefront for the camera store assistant. Next.js App Router · Tailwind v4 · Framer Motion.

The site renders the product catalog and embeds **The Clerk** — a chat dock backed by the
agent API. Assistant replies are scanned for catalog products and rendered as inline preview
cards linking to product pages; the dock lives in the root layout, so it stays open across
navigation.

> Demonstration storefront. Catalog, pricing and stock are fictional.

## Run

Needs the agent API running first.

```bash
npm install
npm run dev        # http://localhost:3000
```

Set `AGENT_API_URL` if the agent is not on `http://127.0.0.1:8000`.

## How the agent is wired

The browser never talks to the agent directly. `src/app/api/chat/route.ts` proxies server-side:

- **History folding** — the agent endpoint is stateless, so the transcript is replayed into a
  single query string on every turn (`buildQuery`).
- **Product matching** — `src/lib/match-products.ts` scans the answer text and the agent's
  reported tool calls, and attaches preview cards for any catalog product mentioned.
- **Failure handling** — upstream errors and timeouts become a friendly message, never a
  leaked stack trace.

| File | Role |
|------|------|
| `src/app/api/chat/route.ts` | agent proxy; the only place `AGENT_API_URL` is read |
| `src/components/chat/ChatDock.tsx` | the floating chat panel |
| `src/components/chat/chat-bus.ts` | window-event bus so any component can open the dock with a pre-filled question |
| `src/lib/match-products.ts` | answer text + tool calls → product cards |
| `src/data/catalog.ts` | typed accessors over `products.json` |

## Product images

Photos are served from object storage and referenced by slug (`products/{slug}.jpg`). The base
URL is configured in `src/data/catalog.ts` and allow-listed in `next.config.ts` for
`next/image`. `scripts/fetch-images.mjs` is the one-shot collector that fetched them from each
product's source page.
