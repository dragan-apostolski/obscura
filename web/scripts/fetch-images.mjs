// One-shot: download each product's og:image from its source_url into public/products/{slug}.jpg
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const catalog = JSON.parse(
  readFileSync(resolve(here, "../../photo-rag-assistant/catalog/products.json"), "utf8")
);
const outDir = resolve(here, "../public/products");
mkdirSync(outDir, { recursive: true });

const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36";

async function ogImage(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA }, redirect: "follow" });
  if (!res.ok) throw new Error(`page ${res.status}`);
  const html = await res.text();
  const m =
    html.match(/<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']/i) ||
    html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:image["']/i);
  if (!m) throw new Error("no og:image");
  return m[1];
}

const failed = [];
for (const p of catalog) {
  const dest = resolve(outDir, `${p.slug}.jpg`);
  if (existsSync(dest)) {
    console.log(`skip ${p.slug}`);
    continue;
  }
  try {
    const img = await ogImage(p.source_url);
    const res = await fetch(img, { headers: { "User-Agent": UA } });
    if (!res.ok) throw new Error(`img ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length < 5000) throw new Error(`too small (${buf.length}b)`);
    writeFileSync(dest, buf);
    console.log(`ok   ${p.slug}  ${(buf.length / 1024).toFixed(0)}kb`);
  } catch (e) {
    failed.push(p.slug);
    console.log(`FAIL ${p.slug}: ${e.message}`);
  }
}
console.log(failed.length ? `\nFailed: ${failed.join(", ")}` : "\nAll images downloaded.");
