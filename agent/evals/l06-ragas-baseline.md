# L06 — golden-set baseline

Judge: `gemini-2.5-flash` via Gemini's OpenAI-compatible endpoint (cross-model — generator is `claude-sonnet-5`, so no self-preference bias). Embeddings: local bge-small. Golden set: `golden.jsonl` (29 rows, all run through the store agent).

## Ragas scores

| id | agent | category | faithfulness | answer relevancy | context precision | context recall |
|---|---|---|---|---|---|---|
| g01 | store | concept | 0.88 | 0.91 | 1.00 | 1.00 |
| g02 | store | concept | 0.89 | 1.00 | 1.00 | 0.83 |
| g03 | store | concept | 0.90 | 0.91 | 1.00 | 1.00 |
| g04 | store | concept | 0.78 | 1.00 | 1.00 | 1.00 |
| g05 | store | concept | 0.96 | 0.78 | 1.00 | 0.50 |
| g06 | store | entity | 1.00 | 1.00 | 1.00 | 1.00 |
| g07 | store | entity | 0.95 | 1.00 | 1.00 | 1.00 |
| g08 | store | entity | 0.77 | 1.00 | 0.50 | 1.00 |
| g09 | store | cross-section | 0.80 | 0.96 | 1.00 | 0.67 |
| g10 | store | entity | 0.94 | 1.00 | 0.50 | 0.75 |
| g11 | store | cross-section | 1.00 | 1.00 | 1.00 | 0.83 |
| g12 | store | entity | 0.94 | 1.00 | 1.00 | 1.00 |
| g23 | store | sparse-data | 0.57 | — | 0.50 | 1.00 |
| g24 | store | sparse-data | 0.83 | — | 0.25 | 0.67 |

### Averages by category (agent=store)

| slice | n | faithfulness | answer relevancy | context precision | context recall |
|---|---|---|---|---|---|
| store / concept | 5 | 0.88 | 0.92 | 1.00 | 0.87 |
| store / cross-section | 2 | 0.90 | 0.98 | 1.00 | 0.75 |
| store / entity | 5 | 0.92 | 1.00 | 0.80 | 0.95 |
| store / sparse-data | 2 | 0.70 | — | 0.38 | 0.83 |

## Assert-based rows

| id | agent | category | result | detail |
|---|---|---|---|---|
| g14 | store | refusal | **PASS** | must_refuse:PASS |
| g15 | store | routing | **PASS** | called one of ['get_product_info', 'search_products']:PASS; numbers grounded in tool output:PASS |
| g16 | store | routing | **PASS** | called one of ['search_products']:PASS; tool args ⊇ {'sensor_format': 'full-frame', 'in_stock_only': True}:PASS |
| g17 | store | routing | **PASS** | called one of ['search_products']:PASS; tool args ⊇ {'type': 'cinema'}:PASS |
| g18 | store | routing | **PASS** | called one of ['explain_technique']:PASS; ≤1 tool calls:PASS |
| g19 | store | ambiguous | **PASS** | must_clarify:PASS; never called search_manual:PASS |
| g20 | store | ambiguous | **PASS** | must_clarify:PASS |
| g21 | store | routing | **PASS** | matches any:PASS; called one of ['search_products']:PASS |
| g22 | store | routing | **PASS** | matches any:PASS; not matches 'a6600(?:(?!\bnot\b)[^.])*in stock':PASS |
| g26 | store | routing | **PASS** | not contains 'don't have manual access':PASS; not contains 'no manual access':PASS; called one of ['search_manual']:PASS |
| g27 | store | routing | **PASS** | contains 'mirrorless':PASS; contains 'cinema':PASS; contains 'DSLR':PASS |
| g28 | store | routing | **PASS** | contains 'Canon':PASS; contains 'Sony':PASS; contains 'Nikon':PASS; contains 'Panasonic':PASS; contains 'OM System':PASS |
| g29 | store | routing | **PASS** | called one of ['search_products']:PASS; tool args ⊇ {'brand': 'Sony'}:PASS |

## Answers needing eyes (FAIL / REVIEW / metric errors)

