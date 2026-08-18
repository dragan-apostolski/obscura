import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { PRODUCTS, getProduct, productImage, relatedProducts } from "@/data/catalog";
import { ProductCard, StockBadge } from "@/components/ProductCard";
import { AskClerkCta } from "@/components/AskClerkCta";
import { formatPrice, specLabel } from "@/lib/format";

export function generateStaticParams() {
  return PRODUCTS.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const product = getProduct(slug);
  if (!product) return { title: "Not found — Obscura" };
  return {
    title: `${product.name} — Obscura`,
    description: product.description,
  };
}

const TYPE_LABEL: Record<string, string> = {
  mirrorless: "Mirrorless",
  dslr: "DSLR",
  cinema: "Cinema",
};

const FORMAT_LABEL: Record<string, string> = {
  "full-frame": "Full frame",
  "aps-c": "APS-C",
  "micro-four-thirds": "Micro Four Thirds",
};

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = getProduct(slug);
  if (!product) notFound();

  const specs = Object.entries(product.specs);
  const related = relatedProducts(product);

  return (
    <div className="mx-auto max-w-[1400px] px-4 pb-20 pt-8 md:px-8">
      {/* Breadcrumb */}
      <nav className="mb-8 flex items-center gap-2 text-sm text-faint">
        <Link href="/" className="transition-colors hover:text-foreground">
          Catalog
        </Link>
        <span>/</span>
        <Link
          href={`/#${product.type}`}
          className="transition-colors hover:text-foreground"
        >
          {TYPE_LABEL[product.type]}
        </Link>
        <span>/</span>
        <span className="text-muted">{product.name}</span>
      </nav>

      <div className="grid gap-10 lg:grid-cols-[1.15fr_1fr] lg:gap-16">
        {/* Image */}
        <div className="relative aspect-[4/3] self-start overflow-hidden rounded-[2rem] bg-card lg:sticky lg:top-24">
          <Image
            src={productImage(product.slug)}
            alt={product.name}
            fill
            priority
            sizes="(max-width: 1024px) 100vw, 55vw"
            className="object-contain p-10 mix-blend-multiply md:p-14"
          />
          <span className="absolute left-5 top-5 rounded-full border border-line bg-background/90 px-3 py-1 text-xs text-muted backdrop-blur-sm">
            {FORMAT_LABEL[product.sensor_format]} · {TYPE_LABEL[product.type]}
          </span>
        </div>

        {/* Details */}
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-faint">{product.brand}</p>
          <h1 className="mt-2 font-display text-3xl tracking-tight md:text-5xl md:leading-[1.05]">
            {product.name}
          </h1>

          <div className="mt-5 flex items-center gap-5">
            <p className="font-mono text-2xl">{formatPrice(product.price_eur)}</p>
            <StockBadge inStock={product.in_stock} />
          </div>

          <p className="mt-6 max-w-[58ch] text-[15px] leading-relaxed text-muted">
            {product.description}
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <AskClerkCta
              label="Ask the clerk about this camera"
              prompt={`Tell me more about the ${product.name}. What is it best at, and is it in stock?`}
            />
            <AskClerkCta
              label="What should I compare it to?"
              variant="outline"
              prompt={`What would you compare the ${product.name} against in your catalog, and why?`}
            />
          </div>

          <p className="mt-4 text-xs leading-relaxed text-faint">
            The clerk checks live stock and pricing, and can search this camera&apos;s manual
            if we have it on file.
          </p>

          {/* Specs */}
          {specs.length > 0 ? (
            <div className="mt-12">
              <h2 className="text-xs uppercase tracking-[0.2em] text-faint">
                Technical specifications
              </h2>
              <dl className="mt-4 divide-y divide-line border-y border-line">
                {specs.map(([key, value]) => (
                  <div key={key} className="grid grid-cols-[minmax(120px,1fr)_2fr] gap-4 py-3">
                    <dt className="text-sm text-muted">{specLabel(key)}</dt>
                    <dd className="text-sm leading-relaxed">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : (
            <div className="mt-12 rounded-2xl border border-line bg-card px-5 py-4">
              <p className="text-sm text-muted">
                Full specification sheet pending — the clerk can still tell you what this
                body is about.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Related */}
      {related.length > 0 && (
        <section className="mt-20 border-t border-line pt-10 md:mt-28">
          <div className="mb-8 flex items-end justify-between gap-4">
            <h2 className="font-display text-2xl tracking-tight md:text-3xl">
              Shelved nearby
            </h2>
            <Link
              href={`/#${product.type}`}
              className="text-sm text-muted transition-colors hover:text-foreground"
            >
              All {TYPE_LABEL[product.type].toLowerCase()} bodies
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
            {related.map((p) => (
              <ProductCard key={p.slug} product={p} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
