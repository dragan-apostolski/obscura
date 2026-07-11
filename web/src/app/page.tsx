import Image from "next/image";
import Link from "next/link";
import { PRODUCTS, BRANDS, getProduct, productImage } from "@/data/catalog";
import { ProductCard } from "@/components/ProductCard";
import { AskClerkCta } from "@/components/AskClerkCta";
import { formatPrice } from "@/lib/format";

const HERO_SLUG = "sony-a7-iv";

const SECTIONS = [
  {
    id: "mirrorless",
    type: "mirrorless" as const,
    title: "Mirrorless",
    blurb:
      "The core of the modern kit — from pocketable APS-C bodies to 61-megapixel full-frame flagships.",
  },
  {
    id: "dslr",
    type: "dslr" as const,
    title: "DSLR",
    blurb:
      "Optical viewfinders, legendary battery life. The workhorses that refuse to retire.",
  },
  {
    id: "cinema",
    type: "cinema" as const,
    title: "Cinema",
    blurb:
      "Purpose-built video bodies with internal RAW, ND filters and cooling for unlimited takes.",
  },
];

export default function HomePage() {
  const hero = getProduct(HERO_SLUG)!;
  const inStockCount = PRODUCTS.filter((p) => p.in_stock).length;

  return (
    <div>
      {/* Hero — asymmetric split, left copy / right product */}
      <section className="mx-auto grid max-w-[1400px] items-center gap-10 px-4 pb-16 pt-12 md:grid-cols-[1.1fr_1fr] md:gap-6 md:px-8 md:pb-24 md:pt-20">
        <div>
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-breathe" />
            {inStockCount} of {PRODUCTS.length} bodies in stock today
          </p>
          <h1 className="font-display text-4xl leading-[1.05] tracking-tight md:text-6xl">
            Cameras, chosen
            <br />
            the slow way.
            <span className="text-accent-ink italic"> Asked</span>
            <br />
            <span className="text-accent-ink italic">the fast way.</span>
          </h1>
          <p className="mt-6 max-w-[52ch] text-base leading-relaxed text-muted">
            Every body in this catalog is here on purpose. And behind the counter sits a
            clerk who has actually read the manuals — ask about prices, stock, autofocus
            menus or metering, and it answers from the source, not from vibes.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <AskClerkCta
              label="Talk to the clerk"
              prompt="I'm looking for a camera. Can you help me pick one?"
            />
            <Link
              href="#mirrorless"
              className="inline-flex items-center gap-2 rounded-full border border-foreground/20 px-5 py-2.5 text-sm transition-colors hover:border-foreground/50 active:scale-[0.98]"
            >
              Browse the catalog
            </Link>
          </div>
        </div>

        <Link href={`/products/${hero.slug}`} className="group relative block">
          <div className="relative aspect-[4/3] overflow-hidden rounded-[2rem] bg-card">
            <Image
              src={productImage(hero.slug)}
              alt={hero.name}
              fill
              priority
              sizes="(max-width: 768px) 100vw, 45vw"
              className="object-contain p-10 mix-blend-multiply transition-transform duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-[1.03]"
            />
          </div>
          <div className="absolute bottom-4 left-4 rounded-2xl border border-line bg-background/90 px-4 py-3 backdrop-blur-sm">
            <p className="text-xs uppercase tracking-[0.16em] text-faint">This week&apos;s pick</p>
            <div className="mt-1 flex items-baseline gap-3">
              <p className="text-sm font-medium">{hero.name}</p>
              <p className="font-mono text-sm text-muted">{formatPrice(hero.price_eur)}</p>
            </div>
          </div>
        </Link>
      </section>

      {/* Brand marquee */}
      <div className="overflow-hidden border-y border-line py-4">
        <div className="flex w-max animate-marquee gap-14 whitespace-nowrap">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="flex gap-14 pr-14" aria-hidden={i === 1}>
              {[...BRANDS, ...BRANDS].map((b, j) => (
                <span
                  key={`${b}-${j}`}
                  className="text-sm uppercase tracking-[0.3em] text-faint"
                >
                  {b}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Agent explainer band */}
      <section className="mx-auto max-w-[1400px] px-4 py-16 md:px-8 md:py-20">
        <div className="grid gap-8 md:grid-cols-[1fr_2fr] md:gap-16">
          <h2 className="font-display text-2xl tracking-tight md:text-3xl">
            Not a chatbot.
            <br />A clerk with the manuals open.
          </h2>
          <div className="grid gap-x-10 gap-y-8 sm:grid-cols-3">
            {[
              {
                n: "01",
                t: "Live catalog",
                d: "Prices and stock come from the store database at the moment you ask — never memorized, never stale.",
              },
              {
                n: "02",
                t: "Real manuals",
                d: "How-to answers are retrieved from official user manuals, reranked, and cited back to the page they came from.",
              },
              {
                n: "03",
                t: "Technique guides",
                d: "Exposure, bokeh, metering, white balance — grounded in the store's own photography guides.",
              },
            ].map((f) => (
              <div key={f.n} className="border-t border-line pt-5">
                <p className="font-mono text-xs text-accent">{f.n}</p>
                <p className="mt-2 text-sm font-medium">{f.t}</p>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Catalog sections */}
      {SECTIONS.map((section, si) => {
        const items = PRODUCTS.filter((p) => p.type === section.type).sort((a, b) => {
          if (a.in_stock !== b.in_stock) return a.in_stock ? -1 : 1;
          return (a.price_eur ?? Infinity) - (b.price_eur ?? Infinity);
        });
        return (
          <section
            key={section.id}
            id={section.id}
            className="mx-auto max-w-[1400px] scroll-mt-20 px-4 pb-16 md:px-8 md:pb-24"
          >
            <div className="mb-8 grid items-end gap-3 border-t border-line pt-10 md:grid-cols-[1fr_auto]">
              <div>
                <p className="font-mono text-xs text-accent">
                  {String(si + 1).padStart(2, "0")} / {items.length} bodies
                </p>
                <h2 className="mt-2 font-display text-3xl tracking-tight md:text-4xl">
                  {section.title}
                </h2>
              </div>
              <p className="max-w-[46ch] text-sm leading-relaxed text-muted md:text-right">
                {section.blurb}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
              {items.map((p, i) => (
                <ProductCard key={p.slug} product={p} priority={si === 0 && i < 4} />
              ))}
            </div>
          </section>
        );
      })}

      {/* Closing CTA */}
      <section className="border-t border-line">
        <div className="mx-auto flex max-w-[1400px] flex-col items-start gap-6 px-4 py-16 md:flex-row md:items-center md:justify-between md:px-8">
          <div>
            <h2 className="font-display text-2xl tracking-tight md:text-3xl">
              Can&apos;t decide between two bodies?
            </h2>
            <p className="mt-2 max-w-[52ch] text-sm leading-relaxed text-muted">
              The clerk compares specs side by side, checks what&apos;s actually in stock, and
              will tell you when the honest answer is &quot;neither.&quot;
            </p>
          </div>
          <AskClerkCta
            label="Compare two cameras"
            prompt="Can you compare the Sony a7 IV and the Canon EOS R6 Mark II for me?"
          />
        </div>
      </section>
    </div>
  );
}
