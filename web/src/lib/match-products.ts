import { PRODUCTS, Product } from "@/data/catalog";

export type ToolCall = { name: string; args: Record<string, unknown> };

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Names the agent might use for a product: full name, name without brand,
 *  and name without series prefixes like "EOS" / "Lumix" / "Alpha". */
function aliases(p: Product): string[] {
  const out = new Set<string>();
  const clean = p.name
    .replace(/\s*\(.*?\)\s*/g, " ")
    .replace(/\s*\+.*$/, "")
    .replace(/\s+/g, " ")
    .trim();
  out.add(clean);
  const noBrand = clean.replace(new RegExp(`^${escapeRegex(p.brand)}\\s+`, "i"), "");
  out.add(noBrand);
  out.add(noBrand.replace(/^(EOS|Lumix|Alpha)\s+/i, ""));
  return [...out].filter((a) => a.length >= 3);
}

/**
 * Find catalog products referenced in an agent answer. Matches product names
 * (longest alias first, with the matched span masked so "EOS R5" cannot
 * re-match inside "EOS R5 C") plus slugs from single-product tool calls.
 * Order follows first appearance in the text; tool-call hits come last.
 */
export function matchProducts(
  answer: string,
  toolCalls: ToolCall[] = [],
  limit = 4
): Product[] {
  const bySlug = new Map(PRODUCTS.map((p) => [p.slug, p]));
  const found = new Map<string, number>();
  let masked = answer;

  const candidates = PRODUCTS.flatMap((p) => aliases(p).map((alias) => ({ p, alias }))).sort(
    (a, b) => b.alias.length - a.alias.length
  );

  for (const { p, alias } of candidates) {
    const re = new RegExp(`(?<![\\w-])${escapeRegex(alias)}(?![\\w-])`, "gi");
    let m: RegExpExecArray | null;
    while ((m = re.exec(masked)) !== null) {
      const prev = found.get(p.slug);
      if (prev === undefined || m.index < prev) found.set(p.slug, m.index);
      masked =
        masked.slice(0, m.index) +
        "\u0000".repeat(m[0].length) +
        masked.slice(m.index + m[0].length);
    }
  }

  for (const p of PRODUCTS) {
    if (!found.has(p.slug)) {
      const re = new RegExp(`(?<![\\w-])${escapeRegex(p.slug)}(?![\\w-])`, "i");
      const m = masked.match(re);
      if (m?.index !== undefined) found.set(p.slug, m.index);
    }
  }

  let tail = answer.length + 1;
  for (const tc of toolCalls) {
    const slug = tc.args?.product;
    if (typeof slug === "string" && bySlug.has(slug) && !found.has(slug)) {
      found.set(slug, tail++);
    }
  }

  return [...found.entries()]
    .sort((a, b) => a[1] - b[1])
    .map(([slug]) => bySlug.get(slug)!)
    .slice(0, limit);
}
