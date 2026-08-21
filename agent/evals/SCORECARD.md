# Eval scorecard

One entry per change that moved a metric: what changed, the numbers, what regressed, and the
call. Newest first. Individual runs live in `results/<stamp>-{retrieval,e2e}.{md,json}`.

Metrics are `context precision / context recall` for retrieval, pass counts for trajectory
asserts, and `faithfulness / answer relevancy` for answers. Judge: `gemini-2.5-flash`,
deliberately a different model family from the generator.

---

## Generation model → Haiku 4.5 — 2026-08-13

Swapped `claude-sonnet-5` → `claude-haiku-4-5`, restructured the system prompt, and fixed two
bugs the swap exposed.

**Two bugs, both found by the harness rather than by eye:**

1. **Concept questions stopped retrieving.** g02 and g03 made zero tool calls and answered
   from parametric knowledge — faithfulness 0.00 behind correct-sounding text. Cause: the
   `explain_technique` docstring listed example topics, and the model read the list as an
   allowlist. Correlation was exact — keyword present, tool called; absent, not called.
   Fixed by replacing the enumeration with a scope statement marked non-exhaustive.
2. **Empty API answers.** `/ask` returned `{"answer": ""}` when the model wrote its reply
   alongside the tool call and closed with an empty turn. `_answer()` read `messages[-1]`
   blindly. Latent since it was written: Sonnet never triggered it (0 of 14 traces), Haiku hit
   it in 13 of 30. Fixed with `_final_text()`.

**Answer quality** (Sonnet 2026-07-22 → Haiku after fixes):

| slice | n | faithfulness | relevancy |
|---|---|---|---|
| concept | 5 | 0.86 → 0.75 | 0.92 → 0.86 |
| cross-section | 2 | 0.96 → 1.00 | 1.00 → 0.96 |
| entity | 6 | 0.85 → 0.85 | 0.99 → 0.97 |
| sparse-data | 1 | 0.71 → 0.87 | 0.96 → 0.94 |

**Trajectory asserts:** 15/17 → 15/15. **Latency** (from trace data, not vendor claims):
12.6s → 4.6s median single request.

**Decision: stay on Haiku.** Faster, cheaper, asserts improved, three of four slices
flat-or-better. The concept-faithfulness dip is the accepted cost — a tool-triggering
probability problem, recoverable with a system-prompt retrieval rule if it ever matters more
than speed.

**Caveats.** Routing is stochastic: g05 retrieved in two runs and skipped in a third. And the
Sonnet baseline predates the chunking and reranker fixes below, so Haiku is measured on better
retrieval than Sonnet had — the real gap is wider than the table shows.

---

## PDF text-extraction cleanup — 2026-07-27

Garbled text found in g09's chunks turned out to be several brand-isolated extraction bugs,
not one shared problem. The main one: ligature glyphs (fi/ff/fl) trip PyMuPDF's word-boundary
heuristic, inserting a stray space mid-word ("flash" → "fl ash"). Confirmed against the font's
own ToUnicode CMap, and it survives a PyMuPDF4LLM swap — a library change doesn't fix it.

Fixed in `app/textclean.py`: NFKC-normalize, then a dictionary-gated regex that rejoins the
break only when the merged word is real and the unmerged fragment isn't, so real word pairs
("turn off the") are never glued.

**Result: did not move g06 or g09.** Chunk text is verifiably cleaner, but the film-simulation
content still never reached the top-20 candidate pool. Text corruption was never the
bottleneck for that row.

**The real finding, while digging into why:** the X100V manual has zero embedded TOC entries,
so section-aware chunking silently fell back to fixed-size splitting. **34 of 66 manuals —
every Canon, every Sony, plus the X100V — have no embedded TOC** and are all on that fallback
path. Kept the cleanup (cheap, improves data quality regardless). The open lever is a fallback
section-detector for TOC-less PDFs.

---

## Reranker: base → large — 2026-07-27

Targeted the vocabulary-gap failures left after the chunking and HNSW fixes — g02, g09, g23 all
at 0.00 precision because `bge-reranker-base` wouldn't rank the right chunk top-5 despite it
being in the pool ("stabilization" vs manual text "vibration reduction / sensor shift").

| row | base | large | |
|---|---|---|---|
| g23 (Z8 IBIS) | 0.00 / 0.00 | 1.00 / 0.67 | fixed |
| g02, g09 | 0.00 | 0.25 | improved, not solved |
| g10, g11, g12 | 0.53–0.89 | 0.87–1.00 | improved |
| g03, g06 | 1.00 / 0.75 | 0.70 / 0.45 | −0.30 precision |

Both regressions are tail-end reordering, not lost signal: the correct chunk stays top-2 and
recall is unchanged, so neither would change the agent's answer.

**Decision: swapped the default to `bge-reranker-large`. g23 closed.** g02/g09 stay open — the
right chunk is now reachable but not top-5, and the next lever is query rewriting, not another
reranker.

---

## Section-aware chunking — 2026-07-23

Targeted g23 (0.00/0.00). Three stacked causes; fixed two:

1. **Chunk boundaries** — the answer line sat mid-chunk inside unrelated autofocus text. Fix:
   split PDFs along their TOC, prefix each chunk with its heading path.
2. **HNSW filtered recall** — with a product filter over 32k+ chunks, the approximate index
   discarded in-slice matches before the LIMIT was met, so the answer chunk never entered the
   pool despite exact vector rank 10. Fix: `ef_search=200` + iterative scan. Likely the real
   cause of the earlier 6→65-manual precision drop, not corpus dilution.

| row | before | after |
|---|---|---|
| g10 (Sony a7 IV WB) | 0.33 / 0.75 | 0.53 / 0.75 |
| g11 (Z6 II time-lapse) | 0.70 / 0.86 | 0.89 / 0.83 |
| g12 (S5 II format) | 0.70 / 1.00 | 0.64 / 1.00 |

Real precision win on manual retrieval, one small regression. **g23 still 0.00** — its third
cause survived, and it turned out to be the reranker, shared with g02 and g09. One disease,
not three bugs.

---

## 3-layer baseline — 2026-07-22

First baseline on the restructured pipeline: retrieval, trajectory and answers scored
separately. Not comparable to the entry below, where precision and recall were measured
through agent transcripts and are structurally distorted per row.

| layer | result |
|---|---|
| retrieval (13 rows) | precision 0.35–0.74, recall 0.72–0.80 by category |
| trajectory | 15/17 PASS |
| answers | faithfulness 0.71–0.96, relevancy 0.92–1.00 |

Worst rows, and the targets that drove everything above: **g02 0.00/0.00** (reranker scores
ISO chunks above shutter-speed ones), **g23 0.00/0.00** (VR page never retrieved), **g09**
precision 0.00.

---

## First clean baseline — 2026-07-10

Harness fixed to score Ragas only against genuine retrieval evidence — excluding
`search_products`, which is routing noise — and to skip relevancy on sparse-data rows, where
hedging is the correct behaviour rather than a miss.

| category | faithfulness | relevancy | precision | recall |
|---|---|---|---|---|
| concept | 0.88 | 0.92 | 1.00 | 0.87 |
| entity | 0.92 | 1.00 | 0.80 | 0.95 |
| cross-section | 0.90 | 0.98 | 1.00 | 0.75 |
| sparse-data | 0.70 | — | 0.38 | 0.83 |

Assert rows: 13/13 PASS. Weakest: sparse-data precision (0.38) — grounding evidence for "what
does the catalog know" questions is thin.
