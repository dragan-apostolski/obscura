# Obscura — Fine Camera Supply

Storefront for the [photo-rag-assistant](../photo-rag-assistant/) store agent (L09). Next.js App Router + Tailwind v4 + Framer Motion.

The site renders the product catalog (copied from `../photo-rag-assistant/catalog/products.json`) and embeds "The Clerk" — a chat dock backed by the LangChain ReAct agent served by FastAPI. Assistant replies are scanned for catalog products and rendered as inline preview cards that link to product pages (same-tab navigation; the chat stays open thanks to App Router layout persistence).

## Run

```bash
# 1. Agent API (from photo-rag-assistant/)
uv run uvicorn app.main:app --reload          # http://127.0.0.1:8000

# 2. Storefront
npm install
npm run dev                                    # http://localhost:3000
```

Set `AGENT_API_URL` if the FastAPI server is not on `http://127.0.0.1:8000`.

## How the agent is wired

- `src/app/api/chat/route.ts` — proxies to `POST /ask`; folds the chat history into a single query string (the agent endpoint is stateless), and matches product mentions in the answer (`src/lib/match-products.ts`) to attach preview cards.
- `src/components/chat/ChatDock.tsx` — the floating chat panel; lives in the root layout so it survives page navigation.
- `src/components/chat/chat-bus.ts` — window-event bus so "Ask the clerk" buttons anywhere can open the dock with a pre-filled question.

## Product images

Photos are served from the Cloudflare R2 bucket `photo-store` (public r2.dev URL, base configured in `src/data/catalog.ts` and allow-listed in `next.config.ts`). They were originally collected by `scripts/fetch-images.mjs` (og:image from each product's `source_url`, official Fujifilm eShop / Wikimedia for the few that 404) and uploaded with `wrangler r2 object put` under `products/{slug}.jpg`. Wrangler auth lives in `.env` (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `R2_BUCKET_NAME`).
