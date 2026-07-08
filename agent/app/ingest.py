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
        text = load_document(path)
        chunks = chunk_text(text)                      # TODO L01: implement chunk_text
        vectors = embed(chunks)                         # batches to the embedding API
        rows = [
            {"source": path.name, "content": c, "token_count": count_tokens(c), "embedding": v}
            for c, v in zip(chunks, vectors)
        ]
        n = insert_chunks(rows)
        print(f"  {path.name}: {n} chunks embedded + stored")

    print("Done. Verify:  select count(*), source from chunks group by source;")


if __name__ == "__main__":
    ingest()
