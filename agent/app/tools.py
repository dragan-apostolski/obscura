"""The camera-store agent's tools.

Each tool returns a string that becomes a ToolMessage. The docstrings are the model's
only view of these functions — they carry the routing rules.

The two search tools also return the chunk list itself as the ToolMessage's `artifact`:
same text to the model, but callers that need the chunks as data (sources, evals) read
them instead of re-parsing the formatted string.
"""
import json
from typing import Literal

from langchain_core.tools import tool

from app.db import get_conn
from app.rerank import rerank
from app.retrieval import hybrid_retrieve


def _manual_slugs() -> set[str]:
    """Products that actually have a manual in the vector store."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("select distinct product from chunks where doc_type = 'manual'")
        return {row[0] for row in cur.fetchall()}


def _format_chunks(chunks: list[dict]) -> str:
    return "\n\n".join(f"[source: {c['source']}]\n{c['content']}" for c in chunks)


def _closest_slugs(product: str, limit: int = 3) -> list[str]:
    """Suggest slugs whose name or slug shares tokens with a missed lookup."""
    tokens = [t for t in product.replace("-", " ").split() if t]
    if not tokens:
        return []
    hits = " + ".join("(slug ilike %s or name ilike %s)::int" for _ in tokens)
    params = [f"%{t}%" for t in tokens for _ in range(2)]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"select slug from products where {hits} > 0 order by {hits} desc limit %s",
            (*params, *params, limit),
        )
        return [r[0] for r in cur.fetchall()]


@tool
def search_products(query: str | None = None, brand: str | None = None,
                    type: Literal["mirrorless", "dslr", "cinema"] | None = None,
                    sensor_format: Literal["full-frame", "aps-c", "micro-four-thirds"] | None = None,
                    in_stock_only: bool = False) -> str:
    """Search the store's camera catalog. Returns matching products as compact rows:
    slug | name | price EUR | stock | whether a user manual is on file.
    Use `query` with a product name to find a specific camera (e.g. "a7 IV");
    use the filters to browse (brands: Canon, Sony, Nikon, Panasonic, OM System).
    All arguments are optional and combine with AND. Prefer this tool first for any
    question about what the store sells; use get_product_info for full details."""
    conds, params = [], []
    if query:
        for token in query.split():
            conds.append("name ilike %s")
            params.append(f"%{token}%")
    if brand:
        conds.append("brand ilike %s")
        params.append(brand)
    if type:
        conds.append("type = %s")
        params.append(type)
    if sensor_format:
        conds.append("sensor_format = %s")
        params.append(sensor_format)
    if in_stock_only:
        conds.append("in_stock")
    where = ("where " + " and ".join(conds)) if conds else ""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"select slug, name, price_eur, in_stock from products {where} order by price_eur",
            params,
        )
        rows = cur.fetchall()
    if not rows:
        return "No products match."
    manuals = _manual_slugs()
    return "\n".join(
        f"{slug} | {name} | {f'{price:.0f} EUR' if price is not None else 'price on request'}"
        f" | {'in stock' if stock else 'back-order'}"
        f" | manual: {'yes' if slug in manuals else 'no'}"
        for slug, name, price, stock in rows
    )


@tool
def get_product_info(product: str) -> str:
    """Look up a camera in the store catalog: current price, stock availability,
    description and technical specifications. Use for any question about what the
    store sells, prices, stock, or spec comparisons. `product` is the exact slug
    from a search_products result — if you don't have one from earlier in the
    conversation, call search_products first. If the user's question doesn't
    clearly map to one product, ask them which camera they mean instead of guessing."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "select name, brand, type, sensor_format, description, price_eur, in_stock, specs "
            "from products where slug = %s",
            (product,),
        )
        row = cur.fetchone()
    if row is None:
        suggestions = _closest_slugs(product)
        hint = f" Closest matches: {', '.join(suggestions)}." if suggestions else ""
        return f"No product with slug '{product}' in the catalog.{hint}"
    name, brand, type_, sensor_format, description, price_eur, in_stock, specs = row
    return json.dumps({
        "name": name,
        "brand": brand,
        "type": type_,
        "sensor_format": sensor_format,
        "description": description,
        "price_eur": float(price_eur) if price_eur is not None else None,
        "in_stock": in_stock,
        "specs": specs,
    })


@tool(response_format="content_and_artifact")
def search_manual(query: str, product: str) -> tuple[str, list[dict]]:
    """Search a camera's official user manual. Use for how-to, settings, menu and
    feature questions about a SPECIFIC camera (e.g. "how do I set ISO on the a7 IV").
    `product` is the exact slug from a search_products result — call search_products
    first if you don't have one. If the user didn't say which camera they mean,
    ask — do not guess. Only some cameras have a manual on file; if this one
    doesn't, the tool says so and lists the ones that do."""
    available = _manual_slugs()
    if product not in available:
        return (f"No manual on file for '{product}'. Manuals are available for: "
                f"{', '.join(sorted(available))}.", [])
    chunks = rerank(query, hybrid_retrieve(query, k=20, product=product, doc_type="manual"), top_n=5)
    if not chunks:
        return f"The {product} manual has no passages matching '{query}'.", []
    return _format_chunks(chunks), chunks


@tool(response_format="content_and_artifact")
def explain_technique(query: str) -> tuple[str, list[dict]]:
    """Search the store's photography technique guides (exposure, aperture, ISO,
    bokeh, composition, white balance, metering...). Use for general photography
    questions that are not about one specific camera's controls or menus."""
    chunks = rerank(query, hybrid_retrieve(query, k=20, doc_type="technique"), top_n=5)
    if not chunks:
        return f"No technique guide covers '{query}'.", []
    return _format_chunks(chunks), chunks


TOOLS = [search_products, get_product_info, search_manual, explain_technique]
