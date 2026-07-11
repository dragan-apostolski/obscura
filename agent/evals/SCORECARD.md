# Eval scorecard — running history

One entry per eval milestone. `l0N-ragas-baseline.md` gets overwritten on every run, so this
is the only persistent record of the before/after story — pull straight from here for the
L10 showcase (metric-backed win).

---

## L06 clean baseline — 2026-07-10

Golden set: 29 rows (`golden.jsonl`), store agent, judge = `gemini-2.5-flash` (cross-model vs
the Claude generator). Harness fixed to score Ragas only against genuine retrieval evidence
(`search_manual`, `explain_technique`, `get_product_info`) — excludes `search_products`
(routing/browse noise) — and to skip `answer_relevancy` on sparse-data rows (hedging is
correct there, not a relevancy miss).

| category | faithfulness | answer relevancy | context precision | context recall |
|---|---|---|---|---|
| concept | 0.88 | 0.92 | 1.00 | 0.87 |
| entity | 0.92 | 1.00 | 0.80 | 0.95 |
| cross-section | 0.90 | 0.98 | 1.00 | 0.75 |
| sparse-data | 0.70 | — | 0.38 | 0.83 |

Assert rows (routing / ambiguous / refusal): **13/13 PASS**.

**Weakest points, in order — these are the L07 targets:**
1. sparse-data context precision (0.38) — grounding evidence for "what does the catalog know"
   questions is thin/noisy.
2. sparse-data faithfulness (0.70) — some inference beyond tool output still slips through.
3. entity context precision (0.80, dragged by two rows at 0.50) — manual retrieval pulls in
   some irrelevant passages alongside the right one.
4. cross-section context recall (0.75) — right manual, but not all needed sections retrieved.

Full per-row detail: `l06-ragas-baseline.md`. Root-cause analysis: `l06-findings-and-action-points.md`.
