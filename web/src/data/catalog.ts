import productsJson from "./products.json";

export type Product = {
  slug: string;
  name: string;
  brand: string;
  type: "mirrorless" | "dslr" | "cinema";
  sensor_format: "full-frame" | "aps-c" | "micro-four-thirds";
  description: string;
  price_eur: number | null;
  in_stock: boolean;
  specs: Record<string, string>;
  source_url: string;
};

/** Slim shape passed to client components and chat previews. */
export type ProductSummary = {
  slug: string;
  name: string;
  brand: string;
  type: Product["type"];
  sensor_format: Product["sensor_format"];
  price_eur: number | null;
  in_stock: boolean;
};

export const PRODUCTS = productsJson as unknown as Product[];

export const BRANDS = [...new Set(PRODUCTS.map((p) => p.brand))];

export function getProduct(slug: string): Product | undefined {
  return PRODUCTS.find((p) => p.slug === slug);
}

/** Product photos live in the Cloudflare R2 bucket `photo-store` (public r2.dev URL). */
const IMAGE_BASE = "https://pub-83751d58d6b3424681fe2e8013206003.r2.dev/products";

export function productImage(slug: string): string {
  return `${IMAGE_BASE}/${slug}.jpg`;
}

export function toSummary(p: Product): ProductSummary {
  return {
    slug: p.slug,
    name: p.name,
    brand: p.brand,
    type: p.type,
    sensor_format: p.sensor_format,
    price_eur: p.price_eur,
    in_stock: p.in_stock,
  };
}

export function relatedProducts(p: Product, count = 4): Product[] {
  const sameBrand = PRODUCTS.filter(
    (o) => o.slug !== p.slug && o.brand === p.brand && o.type === p.type
  );
  const sameFormat = PRODUCTS.filter(
    (o) =>
      o.slug !== p.slug &&
      o.brand !== p.brand &&
      o.sensor_format === p.sensor_format &&
      o.type === p.type
  );
  return [...sameBrand, ...sameFormat].slice(0, count);
}
