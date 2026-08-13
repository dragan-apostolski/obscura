# Eval scorecard — running history

One entry per eval milestone. Individual runs land in `results/<stamp>-{retrieval,e2e}.{md,json}`;
this file is the curated before/after story — pull straight from here when writing up results.

---

## Generation model → Haiku 4.5, prompt + tool-description fixes — 2026-08-13

**Changed:** generation model `claude-sonnet-5` → `claude-haiku-4-5` (1/3 the token cost,
lower latency), system prompt restructured (explicit answer-length rule; the catch-all
"Answers" block split into Grounding / Store facts / When you can't help), and two
routing/robustness fixes found by the first Haiku run.

**Two regressions surfaced by the model swap, both root-caused and fixed:**

1. **Concept questions stopped retrieving.** g02 (shutter speed) and g03 (rule of thirds)
   made *zero* tool calls and answered from parametric knowledge — faithfulness 0.00 with
   no evidence behind correct-sounding text. Cause was the `explain_technique` docstring:
   its topic list (`exposure, aperture, ISO, bokeh, composition, white balance, metering...`)
   was being read as an **allowlist** despite the trailing ellipsis. The correlation was
   exact — every question whose keyword appeared literally got the call, both that didn't,
   didn't. Note "shutter speed" was missing from a list that already had exposure, aperture
   and ISO. Corpus coverage was never the issue (`technique-shutter-speed.txt`,
   `technique-composition-rule-of-thirds.txt` both exist). Fixed by replacing the
   enumeration with a categorical scope statement that explicitly marks the examples as
   non-exhaustive.

2. **Empty API answers.** `/ask` returned `{"answer": ""}` when the model wrote its full
   reply *alongside* the tool call and then closed with an empty turn once the tool result
   added nothing. `_answer()` read `messages[-1].text` blindly. A latent bug since it was
   written — Sonnet never left the last turn empty (0 of 14 traces), Haiku did (13 of 30
   traces wrote text alongside a tool call). Fixed with `_final_text()`, which walks back to
   the last AI turn that actually has text.

**Delta — layer 3 (answer quality), Sonnet baseline (2026-07-22) → Haiku after fixes:**

| slice | n | faithfulness | ans relevancy | |
|---|---|---|---|---|
| concept | 5 | 0.86 → **0.75** | 0.92 → 0.86 | down; see stochasticity note |
| cross-section | 2 | 0.96 → **1.00** | 1.00 → 0.96 | |
| entity | 6 | 0.85 → **0.85** | 0.99 → 0.97 | flat |
| sparse-data | 1 | 0.71 → **0.87** | 0.96 → 0.94 | improved |

**Layer 2 — trajectory asserts: 15/15 PASS** (Sonnet baseline: 15/17, with g14 REVIEW and
g20 FAIL — both now pass). Routing, refusal and clarify behavior are unaffected by the swap.

**Known caveat — retrieval routing is stochastic, not fixed.** The docstring fix raised
concept-row retrieval from 3/5 to 4/5, but g05 ("What is ISO?") retrieved in two runs and
skipped in a third, despite ISO being named in the new description. Haiku reaches for tools
less readily than Sonnet; the description shapes the probability, it doesn't guarantee the
call. If concept faithfulness must be deterministic, the lever is a system-prompt rule
requiring retrieval for general-photography questions — not another description edit.

**Cost and latency — the reason for the swap.** Latency measured from Langfuse trace metrics,
not vendor claims:

| | Sonnet 5 | Haiku 4.5 | |
|---|---|---|---|
| eval runs (concurrency 3) | 15.2 s median | **7.3 s** | 2.1× faster |
| single requests | 12.6 s median | **4.6 s** | 2.8× faster |
| price per MTok (in / out) | $3 / $15 | **$1 / $5** | 3× cheaper |

Sonnet latency samples are small (n=8 and n=4, different question mixes) — the direction is
solid, the exact multiples are approximate.

**DECISION: staying on Haiku 4.5.** ~2.5× faster and 3× cheaper, trajectory asserts improved
(15/17 → 15/15), and three of four quality slices flat-or-better. The concept-faithfulness dip
is the accepted cost. It is a tool-triggering probability problem — Haiku reaches for
`explain_technique` less reliably than Sonnet — not a reasoning deficit, and it is recoverable
later with a system-prompt retrieval rule if it ever matters more than speed.

**Caveat on the comparison:** the Sonnet baseline (2026-07-22) predates the section-aware
chunking (07-23) and the reranker swap (07-27), so Haiku is measured with better retrieval
underneath it than Sonnet had. The real quality gap is somewhat wider than the table shows.
Re-baselining Sonnet on the current retrieval stack would settle it, at the cost of a full run.

Runs: `results/2026-08-13_1254-e2e.md` (before fixes), `results/2026-08-13_1338-e2e.md` (after).

---

## PDF text-extraction cleanup + TOC-coverage finding — 2026-07-27

**Investigated:** whether garbled PDF text (found while looking at g09's retrieved chunks) was
a corpus-wide problem. Corpus-wide scan (66 PDFs + live `chunks` table) found several distinct,
brand-isolated extraction bugs, not one shared problem:

- **Fujifilm (2 files, X100V + X-T5):** ligature glyphs (fi/ff/fl) trip PyMuPDF's word-boundary
  heuristic, inserting a stray space mid-word ("flash" → "fl ash"). Root cause confirmed via the
  font's own ToUnicode CMap — the ligature decodes correctly, the *following space* is spurious.
  Same bug survives a PyMuPDF4LLM swap (shared underlying engine) — a library switch doesn't fix it.
- **OM-System (1 file):** menu arrow "→" decoded as the letter "U" — silent corruption, no golden
  coverage to measure against.
- **Panasonic (7 files):** UI button labels garbled into Japanese Katakana / `�` — no golden
  coverage, g12 (Panasonic) already at 1.00/1.00 with the large reranker, no room to test.
- Duplicated table-header lines (`"Options\nOptions"`) and non-breaking spaces: low-grade noise
  everywhere, worst in Fujifilm.

**Fix implemented (`app/textclean.py`):** NFKC-normalize raw ligature glyphs, then a
dictionary-gated regex (`pyspellchecker`) that rejoins the ligature+space break only when the
merged word is real and the un-merged left fragment isn't (protects real word pairs like
"turn off the camera" from being wrongly glued). Also rejoins line-break hyphenation
("cam-\nera" → "camera"). Wired into both PDF load paths in `app/ingest.py`. Re-ingested only
`fujifilm-x100v-manual.pdf` + `fujifilm-x-t5-manual.pdf` to test.

**Result — did NOT move g06/g09:**

| row | before | after | |
|---|---|---|---|
| g06 (X100V white balance) | 0.45 / 1.00 | 0.50 / 1.00 | flat, within noise |
| g09 (X100V film simulation) | 0.25 / 0.67 | 0.00 / 0.67 | flat/noise |

Chunk text is verifiably cleaner now (confirmed in DB — "different kinds of film", "file size"
etc. now read correctly). But the actual film-simulation content chunk still never reaches the
top-20 candidate pool pre-rerank (vector-arm rank 57, keyword-arm rank 48) — text corruption
was never the bottleneck for this row.

**Real root cause found while digging into *why*:** `fujifilm-x100v-manual.pdf` has **zero
embedded TOC entries**, so `load_pdf_sections` (the section-aware chunker from the 2026-07-23
fix) never applies to it — it silently falls back to plain fixed-400-token chunking, which is
what merged "RAW RECORDING" and "FILM SIMULATION" (two separate menu items) into one chunk,
diluting the embedding. Checked the whole corpus: **34 of 66 manuals — every Canon file, every
Sony file, plus the X100V — have no embedded TOC** and are all on this same fallback path. This
is a bigger, uninvestigated lever than anything fixed so far; g10/g11's earlier gains likely came
from the HNSW fix alone, not chunking, since Sony a7 IV has no TOC either.

**Outcome:** kept the text-cleanup fix (cheap, safe, genuinely improves data quality
independent of this specific eval row) but did not chase it further — this is a demo project,
not a perfection target. **Next lever, not yet started:** a fallback section-detector for
TOC-less PDFs (e.g. detect in-body bold/caps heading spans via `get_text("dict")` font info)
to extend section-aware chunking to the other 34 files.

---

## Reranker swap: base → large — 2026-07-27

**Targeted:** the vocabulary-gap failures left after chunking/HNSW fixes — g02, g09, g23 all
scored 0.00 precision because `bge-reranker-base` wouldn't rank the correct chunk top-5 despite
it being in the candidate pool (e.g. query "stabilization" vs manual text "vibration
reduction / sensor shift"). Tested `BAAI/bge-reranker-large` on the full 13-row retrieval-eval
set (only rows with a `retrieval` scope) before swapping anything.

| row | base | large | |
|---|---|---|---|
| g23 (Z8 IBIS) | 0.00 / 0.00 | **1.00** / 0.67 | fixed |
| g02 (ISO vs shutter) | 0.00 / 0.00 | 0.25 / 0.83 | improved, not solved |
| g09 (film-sim) | 0.00 / 0.67 | 0.25 / 0.67 | improved, not solved |
| g10 | 0.53 / 0.75 | 0.87 / 1.00 | improved |
| g11 | 0.89 / 0.83 | 1.00 / 0.83 | improved |
| g12 | 0.64 / 1.00 | 1.00 / 1.00 | improved |
| g03 (rule of thirds) | 1.00 / 1.00 | 0.70 / 1.00 | −0.30 precision |
| g06 (X100V white balance) | 0.75 / 1.00 | 0.45 / 1.00 | −0.30 precision |
| g01, g04, g05, g07, g08 | — | flat | |

**On the two regressions:** checked the actual retrieved chunks (`results/2026-07-27_1302-retrieval.md`
vs `2026-07-23_1153-retrieval.md`). Both are tail-end reordering, not lost signal — g03's
correct chunk is still rank 1 (0.999→0.993), the precision hit comes from near-zero-relevance
chunks at ranks 3-5 swapping order; g06's correct chunk drops rank 1→2 but stays in the top-5
(recall unchanged at 1.00 for both). Neither would change the agent's actual answer.

**Outcome:** net positive, no real regression. Swapped `settings.reranker_model` default to
`BAAI/bge-reranker-large` (`app/config.py`). **g23 fully closed.** g02/g09 still open — right
chunk is now reachable (recall up) but not ranked top-5; next lever is genuinely different
(query rewriting / synonym expansion for the vocabulary gap), not another reranker swap.
Run: `results/2026-07-27_1302-retrieval.*`.

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

First baseline on the restructured pipeline; not comparable to the 2026-07-10 entry below
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
marker-list asserts flagged in the 2026-07-10 baseline; candidates for judged asserts (`answer_must_affirm`
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

## Clean golden-set baseline — 2026-07-10

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

**Weakest points, in order — these are the next targets:**
1. sparse-data context precision (0.38) — grounding evidence for "what does the catalog know"
   questions is thin/noisy.
2. sparse-data faithfulness (0.70) — some inference beyond tool output still slips through.
3. entity context precision (0.80, dragged by two rows at 0.50) — manual retrieval pulls in
   some irrelevant passages alongside the right one.
4. cross-section context recall (0.75) — right manual, but not all needed sections retrieved.

Full per-row detail: `ragas-baseline.md`. Root-cause analysis: `baseline-findings.md`.
