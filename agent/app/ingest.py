"""Ingestion pipeline: load → chunk → embed → store.

Run:  uv run python -m app.ingest
Reads everything from ./data (PDFs + .html/.txt), chunks, embeds, inserts into `chunks`.
You wire the TODOs during Lesson 01.
"""
from pathlib import Path

import fitz
from bs4 import BeautifulSoup

from app.chunking import chunk_text, count_tokens
from app.embeddings import embed
from app.db import insert_chunks

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Manual filename → catalog metadata. product must match products.slug (see sql/003).
# Technique guides (technique-*.txt) are derived below, everything else must be listed here.
MANUAL_META = {
    "fujifilm-x100v-manual.pdf":        {"brand": "Fujifilm",  "product": "fujifilm-x100v"},
    "canon-eos-r5-user-guide.pdf":      {"brand": "Canon",     "product": "canon-eos-r5"},
    "sony-a7-iv-manual.pdf":            {"brand": "Sony",      "product": "sony-a7-iv"},
    "nikon-z6-ii-manual.pdf":           {"brand": "Nikon",     "product": "nikon-z6-ii"},
    "fujifilm-x-t5-manual.pdf":         {"brand": "Fujifilm",  "product": "fujifilm-x-t5"},
    "panasonic-lumix-s5-ii-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-s5-ii"},
    "canon-eos-r5-c-manual.pdf": {"brand": "Canon", "product": "canon-eos-r5-c"},
    "canon-eos-c400-manual.pdf": {"brand": "Canon", "product": "canon-eos-c400"},
    "canon-eos-c80-manual.pdf": {"brand": "Canon", "product": "canon-eos-c80"},
    "canon-eos-c300-iii-manual.pdf": {"brand": "Canon", "product": "canon-eos-c300-iii"},
    "canon-eos-c70-manual.pdf": {"brand": "Canon", "product": "canon-eos-c70"},
    "canon-eos-r7-manual.pdf": {"brand": "Canon", "product": "canon-eos-r7"},
    "canon-eos-r10-manual.pdf": {"brand": "Canon", "product": "canon-eos-r10"},
    "canon-eos-r50-manual.pdf": {"brand": "Canon", "product": "canon-eos-r50"},
    "canon-eos-r50-v-manual.pdf": {"brand": "Canon", "product": "canon-eos-r50-v"},
    "canon-eos-r100-manual.pdf": {"brand": "Canon", "product": "canon-eos-r100"},
    "canon-eos-r1-manual.pdf": {"brand": "Canon", "product": "canon-eos-r1"},
    "canon-eos-r3-manual.pdf": {"brand": "Canon", "product": "canon-eos-r3"},
    "canon-eos-r5-ii-manual.pdf": {"brand": "Canon", "product": "canon-eos-r5-ii"},
    "canon-eos-r6-ii-manual.pdf": {"brand": "Canon", "product": "canon-eos-r6-ii"},
    "canon-eos-r6-iii-manual.pdf": {"brand": "Canon", "product": "canon-eos-r6-iii"},
    "canon-eos-r6-v-manual.pdf": {"brand": "Canon", "product": "canon-eos-r6-v"},
    "canon-eos-r8-manual.pdf": {"brand": "Canon", "product": "canon-eos-r8"},
    "canon-eos-rp-manual.pdf": {"brand": "Canon", "product": "canon-eos-rp"},
    "canon-eos-c50-manual.pdf": {"brand": "Canon", "product": "canon-eos-c50"},
    "sony-fx2-manual.pdf": {"brand": "Sony", "product": "sony-fx2"},
    "sony-fx3-manual.pdf": {"brand": "Sony", "product": "sony-fx3"},
    "sony-fx30-manual.pdf": {"brand": "Sony", "product": "sony-fx30"},
    "sony-a6700-manual.pdf": {"brand": "Sony", "product": "sony-a6700"},
    "sony-a6400-manual.pdf": {"brand": "Sony", "product": "sony-a6400"},
    "sony-a6100-manual.pdf": {"brand": "Sony", "product": "sony-a6100"},
    "sony-zv-e10-manual.pdf": {"brand": "Sony", "product": "sony-zv-e10"},
    "sony-zv-e10-ii-manual.pdf": {"brand": "Sony", "product": "sony-zv-e10-ii"},
    "sony-a7-iii-manual.pdf": {"brand": "Sony", "product": "sony-a7-iii"},
    "sony-a7-v-manual.pdf": {"brand": "Sony", "product": "sony-a7-v"},
    "sony-a7r-v-manual.pdf": {"brand": "Sony", "product": "sony-a7r-v"},
    "sony-a7r-vi-manual.pdf": {"brand": "Sony", "product": "sony-a7r-vi"},
    "sony-a7s-iii-manual.pdf": {"brand": "Sony", "product": "sony-a7s-iii"},
    "sony-a7c-ii-manual.pdf": {"brand": "Sony", "product": "sony-a7c-ii"},
    "sony-a7cr-manual.pdf": {"brand": "Sony", "product": "sony-a7cr"},
    "sony-a9-ii-manual.pdf": {"brand": "Sony", "product": "sony-a9-ii"},
    "sony-a9-iii-manual.pdf": {"brand": "Sony", "product": "sony-a9-iii"},
    "sony-a1-manual.pdf": {"brand": "Sony", "product": "sony-a1"},
    "sony-a1-ii-manual.pdf": {"brand": "Sony", "product": "sony-a1-ii"},
    "nikon-zr-manual.pdf": {"brand": "Nikon", "product": "nikon-zr"},
    "nikon-d7500-manual.pdf": {"brand": "Nikon", "product": "nikon-d7500"},
    "nikon-d850-manual.pdf": {"brand": "Nikon", "product": "nikon-d850"},
    "nikon-d780-manual.pdf": {"brand": "Nikon", "product": "nikon-d780"},
    "nikon-z30-manual.pdf": {"brand": "Nikon", "product": "nikon-z30"},
    "nikon-z-fc-manual.pdf": {"brand": "Nikon", "product": "nikon-z-fc"},
    "nikon-z50-ii-manual.pdf": {"brand": "Nikon", "product": "nikon-z50-ii"},
    "nikon-z9-manual.pdf": {"brand": "Nikon", "product": "nikon-z9"},
    "nikon-z8-manual.pdf": {"brand": "Nikon", "product": "nikon-z8"},
    "nikon-z7-ii-manual.pdf": {"brand": "Nikon", "product": "nikon-z7-ii"},
    "nikon-z6-iii-manual.pdf": {"brand": "Nikon", "product": "nikon-z6-iii"},
    "nikon-z5-manual.pdf": {"brand": "Nikon", "product": "nikon-z5"},
    "nikon-z5-ii-manual.pdf": {"brand": "Nikon", "product": "nikon-z5-ii"},
    "nikon-zf-manual.pdf": {"brand": "Nikon", "product": "nikon-zf"},
    "panasonic-lumix-s5-iix-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-s5-iix"},
    "panasonic-lumix-s1r-ii-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-s1r-ii"},
    "panasonic-lumix-s1-ii-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-s1-ii"},
    "panasonic-lumix-s1-iie-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-s1-iie"},
    "panasonic-lumix-g9-ii-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-g9-ii"},
    "panasonic-lumix-gh7-manual.pdf": {"brand": "Panasonic", "product": "panasonic-lumix-gh7"},
    "om-system-om-1-ii-manual.pdf": {"brand": "OM System", "product": "om-system-om-1-ii"},
}


def file_metadata(path: Path) -> dict:
    """Resolve {doc_type, brand, product} for a source file. Unknown files raise."""
    if path.name.startswith("technique-"):
        return {"doc_type": "technique", "brand": None, "product": None}
    if path.name in MANUAL_META:
        return {"doc_type": "manual", **MANUAL_META[path.name]}
    raise ValueError(f"{path.name}: not in MANUAL_META and not a technique guide — add it before ingesting")


def load_document(path: Path) -> str:
    """Extract raw text from a source file (PDF or HTML/text)."""
    if path.suffix.lower() == ".pdf":
        with fitz.open(str(path)) as doc:
            return "\n".join(page.get_text() for page in doc)
    if path.suffix.lower() in {".html", ".htm"}:
        return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser").get_text(" ")
    return path.read_text(encoding="utf-8")


def ingest() -> None:
    files = [p for p in DATA_DIR.iterdir() if p.suffix.lower() in {".pdf", ".html", ".htm", ".txt"}]
    if not files:
        print(f"No source docs in {DATA_DIR}. Drop a manual PDF + a technique article there first.")
        return

    for path in files:
        meta = file_metadata(path)
        text = load_document(path)
        chunks = chunk_text(text)
        vectors = embed(chunks)                         # batches to the embedding API
        rows = [
            {"source": path.name, "content": c, "token_count": count_tokens(c), "embedding": v, **meta}
            for c, v in zip(chunks, vectors)
        ]
        n = insert_chunks(path.name, rows)
        print(f"  {path.name}: {n} chunks embedded + stored", flush=True)

    print("Done. Verify:  select count(*), source from chunks group by source;")


if __name__ == "__main__":
    ingest()
