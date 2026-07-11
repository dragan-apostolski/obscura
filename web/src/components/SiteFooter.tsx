import { PRODUCTS, BRANDS } from "@/data/catalog";

export function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto grid max-w-[1400px] gap-10 px-4 py-14 md:grid-cols-[2fr_1fr_1fr] md:px-8">
        <div>
          <p className="font-display text-lg">Obscura — Fine Camera Supply</p>
          <p className="mt-3 max-w-[42ch] text-sm leading-relaxed text-muted">
            A demonstration storefront for an agentic RAG project. The clerk you can chat
            with is a real LangChain ReAct agent grounded in the store catalog, official
            camera manuals and technique guides.
          </p>
        </div>
        <div className="text-sm text-muted">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-faint">Brands</p>
          <ul className="space-y-1.5">
            {BRANDS.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
        <div className="text-sm text-muted">
          <p className="mb-3 text-xs uppercase tracking-[0.18em] text-faint">Catalog</p>
          <ul className="space-y-1.5">
            <li>{PRODUCTS.length} camera bodies</li>
            <li>{PRODUCTS.filter((p) => p.in_stock).length} in stock today</li>
            <li>New stock only — no used gear</li>
            <li>Bodies only — no lenses yet</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line py-5 text-center text-xs text-faint">
        Built as a learning project — photo-rag-assistant, week 1 flagship.
      </div>
    </footer>
  );
}
