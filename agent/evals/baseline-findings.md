# Golden-set baseline findings → action plan

Source: `ragas-baseline.md` + its runs dump (2026-07-10, 27 golden rows, all `store` agent, Gemini judge).

## Baseline headline

Strong on **concept** and **entity** after shipping the store agent + Fujifilm catalog fix. Weak on **sparse-data faithfulness**, **cross-section context precision/recall**, and **scope refusal** (g14).

| slice | faith | ans-rel | ctx-prec | ctx-recall |
|---|---|---|---|---|
| concept | 0.88 | 0.91 | 1.00 | 0.88 |
| entity | 0.94 | 0.99 | 0.62 | 0.95 |
| cross-section | 0.91 | 0.98 | 0.25 | 0.67 |
| sparse-data | 0.59 | 0.45* | 0.38 | 0.83 |

\* `answer_relevancy` misleading on sparse-data — hedging is correct but scores 0 (see B).

Assert rows: **12/13 PASS**, g14 **REVIEW** (poem compliance).

---

## What each slice tests

| category | rows | failure mode under test | primary metric |
|---|---|---|---|
| concept | g01–g05 | technique Q&A via `explain_technique` | all four |
| entity | g06–g12 | per-camera manual via `search_manual` | recall + precision |
| cross-section | g09, g11 | right manual, **wrong section** (film sim, time-lapse) | context recall |
| sparse-data | g23, g24 | tools lack the answer → **must not invent** | faithfulness |
| refusal | g14 | off-topic creative → must decline | deterministic asserts |
| routing / ambiguous | g15–g29 | tool choice, clarify, catalog | behavioral asserts |

**sparse-data** = generation honesty. **cross-section** = retrieval completeness.

---

## Findings A–E

### A — Routing noise in `contexts` (measurement)

For manual/how-to questions the agent calls `search_products` first (slug lookup). That catalog JSON is captured in `contexts` alongside real `search_manual` / `explain_technique` passages. Ragas **context_precision** then penalizes useful-but-irrelevant routing output.

Evidence: g09 `cp 0.0` (2 contexts: products + manual); g06/g08/g10/g11 often `cp 0.5`; g24 `cp 0.25` (includes two failed `get_product_info` error messages before retry).

**Action:** when scoring ragas, feed only retrieval-tool outputs (`search_manual`, `explain_technique`) as `retrieved_contexts`, not `search_products` / `get_product_info`.

---

### B — `answer_relevancy` on sparse-data (measurement)

Ragas flags hedged answers as **noncommittal** and hard-zeros `answer_relevancy`. For sparse-data rows, hedging ("can't verify from our data") is **desired** → g23 scored `0.0` relevancy despite mostly reasonable behavior.

**Action:** skip `answer_relevancy` for `category: sparse-data` in the harness (show `—`, exclude from averages). Judge those rows on **faithfulness** only.

---

### C — Comparison over-claims (g24, faithfulness 0.44)

**What happened:** agent fetched both products (after wrong-slug retries), built a comparison table from catalog specs, then added **world-knowledge editorial** ("best-in-class AF", "step behind Sony", "great low-light") not in tool output.

**Also:** Z6 II catalog has internal contradiction (description says 4K 60p, specs say 30p).

**Actions:**
1. **Prompt:** comparisons only from returned spec/description fields; say "not listed" for gaps; no qualitative opinions unless in source.
2. **Data:** fix contradictory Z6 II video fields in `catalog/products.json`.
3. **Tool:** make `get_product_info` resolve loose names → slug on single confident match (avoids failed-lookup error contexts; see below). Keep `search_products` for browse/filter/disambiguation.

---

### D — Scope refusal weak (g14 REVIEW)

**What happened:** asked for a poem about Ljubljana; agent **wrote the poem** (+ camera tie-in).

**Why REVIEW not FAIL:** `must_refuse` only checks `REFUSAL_MARKERS` in `run_eval.py` (`"can't help"`, `"outside"`, `"unrelated"`, etc.). Poem answer has none → REVIEW ("read the answer"), not auto-FAIL.

**Actions:**
1. **Prompt:** decline off-topic creative requests; same lever as strict out-of-catalog refusal.
2. **Eval:** strengthen g14 asserts — e.g. `answer_must_match_any` refusal regex + `must_refuse` miss → **FAIL** (not REVIEW); optional `max_tool_calls: 0`.

---

### E — Section recall still partial (cross-section + concept)

Even with correct manual/product scope, needed sections aren't fully retrieved (g09 film sim `recall 0.67`, g11 time-lapse `0.67`; g05 ISO `recall 0.5`). Deeper retrieval work — **after A** re-baselines precision.

**Actions:** section-aware chunking and/or tune `search_manual` top_n / rerank threshold. Prove on g09, g11, g05.

---

## Additional action points (catalog & policy)

### Coverage gap (user-identified)

Only **6/65** catalog products have manuals ingested (R5, X-T5, X100V, Z6 II, S5 II, a7 IV). For the other 59, the agent can only answer from catalog specs — not how-to / feature questions.

**Actions:**
1. Ingest manuals for catalog products (or a prioritized subset) + re-run `app.ingest`.
2. Add golden rows for **out-of-catalog** products → expect strict "we don't carry / not in our catalog."
3. **Prompt — two behaviors:**
   - **In catalog, detail missing** (e.g. g23 Z8 IBIS): state what catalog/manual data *does* contain; flag the gap; **no world-knowledge inference** ("likely has IBIS").
   - **Not in catalog:** strict refusal.

g23 faithfulness 0.73 = one ungrounded inference, not missing manual alone.

### `get_product_info` slug resolution

Agent called `get_product_info("a7 IV")` / `"Z6 II"` (wrong slugs) → error contexts → retried correctly. Self-corrects but wastes calls and pollutes metrics.

**Action:** `get_product_info` fuzzy-resolves loose names internally when one confident match; `search_products` remains for browse/filter/ambiguous names only.

---

## Suggested order

1. **A + B** — harness/measurement fixes (cheap); re-run `--from-runs` or full eval for clean baseline.
2. **D + catalog policy prompt** — scope refusal + in-catalog vs out-of-catalog + no inference on missing data.
3. **Catalog manuals + out-of-catalog golden rows** — ingest + re-embed + new eval rows.
4. **`get_product_info` name resolution** — tool robustness.
5. **C data fix** — Z6 II catalog contradiction.
6. **E** — chunking/rerank (after A shows true recall gap).

---

## Done since the baseline

- Golden set: all rows `agent: store`; dropped duplicate refusal rows g13/g25.
- Fujifilm added to catalog + prompt; g21 flipped to positive assert.
- Harness: regex asserts (g22), hardened `norm()`, parallel `ask_batch` (concurrency 3), per-item timeout, Gemini judge, `--from-runs`.
- Agent rename: `app/agent.py` = main store agent; `app/manual_rag_agent.py` = the deprecated hand-wired graph.

---

## Key row references

| id | issue | scores / assert |
|---|---|---|
| g09 | cross-section recall | cp 0.0, recall 0.67 |
| g11 | cross-section recall | cp 0.5, recall 0.67 |
| g14 | scope refusal | must_refuse REVIEW |
| g23 | sparse-data inference | faith 0.73, relevancy 0.0 |
| g24 | comparison grounding | faith 0.44, cp 0.25 |
