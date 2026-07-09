"""L01 ingestion pipeline: load → chunk → embed → store.

Run:  uv run python -m app.ingest
Reads everything from ./data (PDFs + .html/.txt), chunks, embeds, inserts into `chunks`.
You wire the TODOs during Lesson 01.
"""
from pathlib import Path

from pypdf import PdfReader
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
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
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
        print(f"  {path.name}: {n} chunks embedded + stored")

    print("Done. Verify:  select count(*), source from chunks group by source;")


if __name__ == "__main__":
    ingest()
