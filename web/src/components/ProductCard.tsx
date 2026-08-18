import Image from "next/image";
import Link from "next/link";
import { Product, productImage } from "@/data/catalog";
import { formatPrice } from "@/lib/format";

export function StockBadge({ inStock, subtle = false }: { inStock: boolean; subtle?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs ${
        subtle ? "text-faint" : inStock ? "text-emerald-700" : "text-faint"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          inStock ? "bg-emerald-500 animate-breathe" : "bg-stone-300"
        }`}
      />
      {inStock ? "In stock" : "Back-order"}
    </span>
  );
}

export function ProductCard({ product, priority = false }: { product: Product; priority?: boolean }) {
  return (
    <Link
      href={`/products/${product.slug}`}
      className="group block active:scale-[0.99] transition-transform"
    >
      <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-card">
        <Image
          src={productImage(product.slug)}
          alt={product.name}
          fill
          priority={priority}
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
          className="object-contain p-6 mix-blend-multiply transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:scale-[1.045]"
        />
      </div>
      <div className="mt-3 flex items-baseline justify-between gap-3 px-0.5">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.16em] text-faint">{product.brand}</p>
          <p className="mt-0.5 truncate text-[15px] font-medium">{product.name}</p>
        </div>
        <p className="shrink-0 font-mono text-sm text-foreground/80">
          {formatPrice(product.price_eur)}
        </p>
      </div>
      <div className="mt-1 px-0.5">
        <StockBadge inStock={product.in_stock} subtle />
      </div>
    </Link>
  );
}
