# Eval scorecard — running history

One entry per eval milestone. Individual runs land in `results/<stamp>-{retrieval,e2e}.{md,json}`;
this file is the curated before/after story — pull straight from here for the L10 showcase.

---

## Section-aware chunking — 2026-07-23

**Weakest cell targeted:** g23 (Nikon Z8 IBIS) retrieval, 0.00/0.00. Root-caused to three
stacked failures, fixed the first two:

1. **Chunk boundaries** — the "5-axis sensor shift" answer line sat mid-chunk inside
   autofocus text (fixed 400-tok splitter). Fix: TOC-section-aware chunking (`app/ingest.py`
   `load_pdf_sections`/`chunk_document`) — each chunk = one manual section, prefixed with its
   heading path. PDFs with a usable TOC only; `.txt` technique guides stay fixed-size.
2. **HNSW filtered recall** — with a product filter over 32k+ chunks, the approximate index
   discarded in-slice matches before the LIMIT was met; g23's answer chunk was absent from the
   candidate pool despite exact vector rank 10. Fix: `hnsw.ef_search=200` + iterative scan
   (`app/retrieval.py`). **Likely the real cause of the 6→65-manual precision drop**, not
   corpus dilution. (Isolated run 07-23_1137: fixed pool membership but moved no top-5 score —
   necessary, not sufficient.)

**Delta — layer 1 (retriever alone), full corpus re-ingested with section chunking:**

| row | before | after | |
|---|---|---|---|
| g10 (Sony a7 IV WB) | 0.33 / 0.75 | **0.53** / 0.75 | +0.21 precision |
| g11 (Z6 II time-lapse) | 0.70 / 0.86 | **0.89** / 0.83 | +0.19 precision |
| g12 (S5 II format) | 0.70 / 1.00 | 0.64 / 1.00 | −0.06 precision |
| g02, g09, g23 | 0.00 | 0.00 | unchanged |
| others | — | flat | |

**Outcome:** a real precision win on manual retrieval (g10, g11), one small regression (g12),
no others. **g23 itself still 0.00** — its third failure survives: the reranker
(`bge-reranker-base`) won't rank "vibration reduction / sensor shift" top-5 for a
"stabilization" query. Same vocabulary-gap disease as g02 and g09 — a shared reranker
limitation, not three separate bugs. Next lever (deferred): stronger reranker, tested offline
on saved (query, chunk) pairs first. Run: `results/2026-07-23_1153-retrieval.*`.

---

## 3-layer baseline — 2026-07-22

First baseline on the restructured pipeline; not comparable to the L06 entry below
(precision/recall there were measured through agent transcripts — bundled contexts,
routing noise — and are structurally overstated/understated per row). Golden set:
28 rows. Judge: `gemini-2.5-flash`.

**Layer 1 — retrieval alone** (`retrieval_eval.py`, 13 rows):

| category | n | ctx precision | ctx recall |
|---|---|---|---|
| concept | 5 | 0.74 | 0.80 |
| cross-section | 2 | 0.35 | 0.76 |
| entity | 6 | 0.55 | 0.72 |

Worst rows — the open fix targets: **g02 0.00/0.00** (reranker scores ISO chunks 0.96
above true shutter-speed chunks 0.35), **g23 0.00/0.00** (real VR page never retrieved,
only menu-listing noise), **g09 0.00 precision** (film-sim; new finding).

**Layer 2 — trajectory** (asserts): 15/17 PASS. g14 REVIEW (refusal marker wording),
g20 FAIL (no clarify question on "my photos look blurry") — both are the flaky
marker-list asserts flagged at L06; candidates for judged asserts (`answer_must_affirm`
pattern). New passes: g23 reaches the manual + affirms IBIS, g30 answers from catalog
specs, g06 no wasted wrong-slug call.

**Layer 3 — answer quality** (faithfulness / answer relevancy):

| category | n | faithfulness | ans relevancy |
|---|---|---|---|
| concept | 5 | 0.86 | 0.92 |
| cross-section | 2 | 0.96 | 1.00 |
| entity | 6 | 0.85 | 0.99 |
| sparse-data | 1 | 0.71 | 0.96 |

Weakest: g24 comparison faithfulness 0.71 (known editorializing row), g07 0.72, g23 0.75.

**Next targets, in order:** g02 + g23 retrieval (reranker/chunking — iterate via the
free layer-1 loop), g09 precision, then g14/g20 assert hardening.

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
