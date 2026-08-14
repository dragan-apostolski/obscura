# Tests

Not yet written. `pytest` is in the dev dependencies and `pyproject.toml` points it here; there are no tests or fixtures yet.

The eval suite in `evals/` covers agent behaviour end to end, but it needs a database, a
model API and judge tokens, so it can't run on every commit. These tests are the fast,
hermetic layer that should:

- **`app/tools.py`** — the highest-value target. `search_products` filter combinations,
  `get_product_info` on an unknown slug (the suggestion path), `search_manual` when no
  manual exists for a product. Needs a seeded test database or a stubbed `get_conn`.
- **`app/agent.py`** — `_final_text` against a message list whose last turn is empty (the
  bug that shipped an empty answer), `_sources` de-duplication and ordering, `_trace`
  splitting evidence from routing calls. Pure functions over message fixtures; no model
  call required.
- **`app/retrieval.py`** — that `product` and `doc_type` filters reach both arms of the
  hybrid query. Assert on generated SQL rather than on results.
- **`app/chunking.py`, `app/textclean.py`** — deterministic and dependency-free, so
  straightforward: token budgets and overlap, ligature-spacing repairs.
- **API contract** — `httpx.ASGITransport` against the app with the agent stubbed:
  validation rejections, the error handler's shape, `thread_id` round-tripping.

Deliberately out of scope: anything asserting on model output. That belongs in `evals/`,
where it is scored rather than asserted.
