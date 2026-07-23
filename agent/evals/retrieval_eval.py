"""Retrieval eval: score the retriever alone, no agent in the loop.

Each golden row with a `retrieval` block declares the right arguments for
`hybrid_retrieve` (corpus scope). We call retrieve → rerank directly with them and
judge the returned chunks against the row's reference. Failures here are retrieval
failures by construction — the agent, its routing and its prompts are not involved.

Usage:
  uv run python -m evals.retrieval_eval               # full -> evals/results/<stamp>-retrieval.md
  uv run python -m evals.retrieval_eval --only <ids>  # subset
"""
import argparse
import asyncio
import json
import statistics
import sys
from collections import defaultdict

# run_eval also carries the ragas/vertex compat shim, which must load first
from evals.run_eval import RESULTS_DIR, RUN_STAMP, build_metrics, load_golden

REPORT = RESULTS_DIR / f"{RUN_STAMP}-retrieval.md"
RESULTS_JSON = RESULTS_DIR / f"{RUN_STAMP}-retrieval.json"
JUDGE_CONCURRENCY = 4
TOP_N = 5


def retrieve(row: dict) -> list[dict]:
    from app.rerank import rerank
    from app.retrieval import hybrid_retrieve
    scope = row["retrieval"]
    if unknown := set(scope) - {"doc_type", "product"}:
        raise ValueError(f"{row['id']}: unknown retrieval keys {unknown}")
    return rerank(row["question"], hybrid_retrieve(row["question"], k=20, **scope), top_n=TOP_N)


async def score_row(metrics: dict, row: dict, chunks: list[dict],
                    sem: asyncio.Semaphore) -> dict:
    contexts = [c["content"] for c in chunks] or ["(nothing retrieved)"]
    scores = {}
    async with sem:
        for name in ("context_precision", "context_recall"):
            try:
                r = await metrics[name].ascore(
                    user_input=row["question"], reference=row["reference"],
                    retrieved_contexts=contexts,
                )
                scores[name] = round(float(r.value), 3)
            except Exception as e:
                scores[name] = None
                scores[f"{name}_error"] = f"{type(e).__name__}: {e}"[:200]
    return scores


def write_report(results: list[dict]):
    from app.config import settings

    lines = [
        "# Retrieval baseline — retriever only, no agent",
        "",
        f"`hybrid_retrieve(k=20, **row.retrieval)` → `rerank(top_n={TOP_N})`, judged by "
        f"`{settings.judge_model}` against the row reference.",
        "",
        "| id | category | scope | context precision | context recall |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        s = r["scores"]
        scope = r["row"]["retrieval"].get("product", r["row"]["retrieval"]["doc_type"])
        fmt = lambda v: f"{v:.2f}" if isinstance(v, float) else "err"  # noqa: E731
        lines.append(f"| {r['row']['id']} | {r['row']['category']} | {scope} "
                     f"| {fmt(s.get('context_precision'))} | {fmt(s.get('context_recall'))} |")

    lines += ["", "### Averages by category", "",
              "| category | n | context precision | context recall |", "|---|---|---|---|"]
    groups = defaultdict(list)
    for r in results:
        groups[r["row"]["category"]].append(r["scores"])
    for cat, grp in sorted(groups.items()):
        cells = []
        for m in ("context_precision", "context_recall"):
            vals = [s[m] for s in grp if isinstance(s.get(m), float)]
            cells.append(f"{statistics.mean(vals):.2f}" if vals else "—")
        lines.append(f"| {cat} | {len(grp)} | " + " | ".join(cells) + " |")

    # per-chunk rerank scores: the raw material for diagnosing mis-ranking
    lines += ["", "## Retrieved chunks (rerank score | source)", ""]
    for r in results:
        lines.append(f"### {r['row']['id']} — {r['row']['question']}")
        lines.append("")
        for c in r["chunks"]:
            preview = c["content"][:110].replace("\n", " ")
            lines.append(f"- `{c['score']:.3f}` | {c['source']} | {preview}…")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated row ids")
    args = ap.parse_args()

    rows = [g for g in load_golden() if g.get("retrieval")]
    if args.only:
        wanted = set(args.only.split(","))
        if missed := wanted - {g["id"] for g in rows}:
            print(f"[warn] no retrieval row for: {', '.join(sorted(missed))}")
        rows = [g for g in rows if g["id"] in wanted]
    if not rows:
        sys.exit("no rows to score — report left untouched")

    print(f"[retrieve] {len(rows)} queries...", flush=True)
    runs = [(row, retrieve(row)) for row in rows]

    metrics = build_metrics()
    sem = asyncio.Semaphore(JUDGE_CONCURRENCY)
    print(f"[judge] scoring {len(runs)} rows x 2 metrics...", flush=True)
    scores = await asyncio.gather(*(score_row(metrics, row, chunks, sem)
                                    for row, chunks in runs))
    results = [{"row": row, "chunks": chunks, "scores": s}
               for (row, chunks), s in zip(runs, scores)]
    for r in results:
        print(f"  {r['row']['id']}: {r['scores']}")

    # raw results for scripts (deltas across runs); the .md is the human view of the same data
    RESULTS_JSON.write_text(json.dumps([
        {"row_id": r["row"]["id"], "category": r["row"]["category"],
         "retrieval": r["row"]["retrieval"], "question": r["row"]["question"],
         "scores": r["scores"], "chunks": r["chunks"]}
        for r in results
    ], indent=2, ensure_ascii=False))
    write_report(results)
    print(f"[saved] raw results -> {RESULTS_JSON}")
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    asyncio.run(main())
