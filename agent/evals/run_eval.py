"""Agent eval harness: run the golden dataset against the store agent and score it.

Two scoring paths, chosen per row by its `scoring` field:
  deterministic/behavioral -> plain asserts against the `expect` object (trajectory)
  ragas                    -> faithfulness + answer relevancy, judge = Gemini (end-to-end)

Retrieval quality (context precision/recall) is NOT scored here — that's measured
against the retriever directly, without the agent, in evals/retrieval_eval.py.

Usage:
  uv run python -m evals.run_eval                 # full run -> evals/e2e-baseline.md
  uv run python -m evals.run_eval --only <ids>    # subset (smoke test)
  uv run python -m evals.run_eval --skip-ragas    # asserts only, no judge calls
  uv run python -m evals.run_eval --from-runs     # re-score cached runs, no agent re-run
"""
# --- compat shim: ragas 0.4.3 imports Vertex AI symbols that langchain-community 0.4
# --- no longer ships; they are only referenced for isinstance checks.
import sys, types  # noqa: E401

try:
    from langchain_community.chat_models.vertexai import ChatVertexAI  # noqa: F401
except Exception:
    _m = types.ModuleType("langchain_community.chat_models.vertexai")

    class _ChatVertexAI:  # pragma: no cover
        pass

    _m.ChatVertexAI = _ChatVertexAI
    sys.modules["langchain_community.chat_models.vertexai"] = _m
    import langchain_community.llms as _ll

    if not hasattr(_ll, "VertexAI"):
        class _VertexAI:  # pragma: no cover
            pass

        _ll.VertexAI = _VertexAI
# --- end shim

import argparse
import asyncio
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

EVALS_DIR = Path(__file__).parent
GOLDEN = EVALS_DIR / "golden.jsonl"
RUNS_JSON = EVALS_DIR / "runs.json"
REPORT = EVALS_DIR / "e2e-baseline.md"
AGENT_CONCURRENCY = 3   # parallel store-agent runs; higher trips the Anthropic rate limit

# answer_relevancy hard-zeros hedged answers, which is wrong for categories where
# hedging is correct. Add {category: {metric_name}} here if that recurs. Skipped
# metrics show as "—" and are excluded from averages.
SKIP_METRICS_BY_CATEGORY = {}

REFUSAL_MARKERS = [
    "don't know", "do not know", "can't help", "cannot help", "not able to help",
    "outside", "unrelated", "decline", "not covered", "isn't covered",
    "no information", "don't have information",
]
CLARIFY_MARKERS = ["which camera", "which model", "what camera", "which one", "which body"]
STOCK_NEGATIONS = [
    "not in stock", "isn't in stock", "don't carry", "do not carry",
    "not carried", "don't have", "do not have", "not in our catalog", "couldn't find",
]


def load_golden() -> list[dict]:
    dec, s, i, rows = json.JSONDecoder(), GOLDEN.read_text(), 0, []
    while i < len(s):
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            break
        obj, i = dec.raw_decode(s, i)
        rows.append(obj)
    return rows


def norm(text: str) -> str:
    """Lowercase, normalize apostrophes, strip markdown emphasis, collapse whitespace —
    so intent checks aren't broken by **bold** or stray spacing."""
    text = text.replace("’", "'").lower()
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def run_agent(agent: str, question: str) -> dict:
    if agent == "manual_rag":
        from app.manual_rag_agent import ask
        out = ask(question)
        out.setdefault("tool_calls", [])
    else:
        from app.agent import ask_traced
        out = ask_traced(question)
    out.setdefault("retrieval_contexts", out.get("contexts", []))
    return out


# ---------- assert-based scoring ----------

def check_expect(expect: dict, run: dict) -> list[dict]:
    """Evaluate every assert in `expect`; returns [{check, status, detail}]."""
    answer, calls = norm(run["answer"]), run["tool_calls"]
    results = []

    def add(check: str, status: str, detail: str = ""):
        results.append({"check": check, "status": status, "detail": detail})

    if expect.get("must_refuse"):
        hit = next((m for m in REFUSAL_MARKERS if m in answer), None)
        add("must_refuse", "PASS" if hit else "REVIEW",
            f"marker: {hit!r}" if hit else "no refusal marker found — read the answer")
    if expect.get("must_clarify"):
        asked = "?" in run["answer"]
        marker = next((m for m in CLARIFY_MARKERS if m in answer), None)
        status = "PASS" if (asked and marker) else ("REVIEW" if asked else "FAIL")
        add("must_clarify", status, f"marker: {marker!r}, has question: {asked}")
    for needle in expect.get("answer_must_contain_all", []):
        ok = norm(needle) in answer
        add(f"contains '{needle}'", "PASS" if ok else "FAIL")
    if pats := expect.get("answer_must_contain_any"):
        hit = next((p for p in pats if norm(p) in answer), None)
        add("contains any", "PASS" if hit else "FAIL", f"matched: {hit!r}")
    if pats := expect.get("answer_must_match_any"):
        # regex against the normalized answer — for intent that survives filler words/synonyms
        hit = next((p for p in pats if re.search(p, answer)), None)
        add("matches any", "PASS" if hit else "FAIL", f"matched: {hit!r}")
    for needle in expect.get("answer_must_not_contain", []):
        ok = norm(needle) not in answer
        add(f"not contains '{needle}'", "PASS" if ok else "FAIL")
    for pat in expect.get("answer_must_not_match", []):
        ok = re.search(pat, answer) is None
        add(f"not matches '{pat}'", "PASS" if ok else "FAIL")
    if names := expect.get("tools_any"):
        called = [c["name"] for c in calls]
        ok = any(n in called for n in names)
        add(f"called one of {names}", "PASS" if ok else "FAIL", f"called: {called}")
    for name in expect.get("tools_forbidden", []):
        called = [c["name"] for c in calls]
        add(f"never called {name}", "PASS" if name not in called else "FAIL",
            f"called: {called}")
    if (cap := expect.get("max_tool_calls")) is not None:
        add(f"≤{cap} tool calls", "PASS" if len(calls) <= cap else "FAIL",
            f"made {len(calls)}: {[c['name'] for c in calls]}")
    if args_want := expect.get("tool_args_contain"):
        def match(call):
            return all(
                norm(str(call["args"].get(k, ""))) == norm(str(v))
                for k, v in args_want.items()
            )
        ok = any(match(c) for c in calls)
        add(f"tool args ⊇ {args_want}", "PASS" if ok else "FAIL",
            f"calls: {[(c['name'], c['args']) for c in calls]}")
    if expect.get("answer_must_contain_tool_data"):
        # some >=3-digit number in the answer must originate from tool output
        tool_text = "".join(run["contexts"]).replace(",", "").replace(".", "")
        nums = re.findall(r"\d{3,}", run["answer"].replace(",", "").replace(".", ""))
        ok = bool(nums) and all(n in tool_text for n in nums)
        add("numbers grounded in tool output",
            "PASS" if ok else ("FAIL" if nums else "REVIEW"), f"numbers: {nums}")
    if expect.get("answer_must_not_claim_stock"):
        claims = "in stock" in answer and not any(n in answer for n in STOCK_NEGATIONS)
        add("no invented stock claim", "FAIL" if claims else "PASS")
    return results


# ---------- ragas scoring ----------

def build_metrics():
    from openai import AsyncOpenAI
    from ragas.llms import llm_factory
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.metrics.collections import (
        AnswerRelevancy, ContextPrecisionWithReference, ContextRecall, Faithfulness,
    )
    from app.config import settings

    # Gemini judge (cross-model vs the Claude generator) via its OpenAI-compatible endpoint.
    # reasoning_effort="none" disables 2.5 thinking so it doesn't eat the token budget.
    llm = llm_factory(
        settings.judge_model, provider="openai",
        client=AsyncOpenAI(api_key=settings.gemini_api_key, base_url=settings.judge_base_url),
        max_tokens=4096, reasoning_effort="none",
    )

    class LocalBge(BaseRagasEmbedding):
        """AnswerRelevancy needs embeddings; reuse the app's local bge model."""
        def embed_text(self, text: str, **kwargs) -> list[float]:
            from app.embeddings import embed_one
            return embed_one(text)

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return self.embed_text(text)

    # faithfulness + answer_relevancy are scored here (end-to-end);
    # context_precision + context_recall are used by evals/retrieval_eval.py
    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=LocalBge()),
        "context_precision": ContextPrecisionWithReference(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }


async def score_sample(metrics: dict, sample: dict, sem: asyncio.Semaphore,
                        category: str | None = None) -> dict:
    # judge sees ONLY these three fields — nothing from notes/category/expect
    assert set(sample) == {"user_input", "response", "retrieved_contexts"}
    ui, resp = sample["user_input"], sample["response"]
    ctx = sample["retrieved_contexts"] or ["(the system retrieved no context)"]
    skip = SKIP_METRICS_BY_CATEGORY.get(category, set())
    scores = {}
    async with sem:
        for name in ("faithfulness", "answer_relevancy"):
            if name in skip:
                continue
            metric = metrics[name]
            try:
                if name == "faithfulness":
                    r = await metric.ascore(user_input=ui, response=resp, retrieved_contexts=ctx)
                else:  # answer_relevancy
                    r = await metric.ascore(user_input=ui, response=resp)
                scores[name] = round(float(r.value), 3)
            except Exception as e:  # keep the run alive; record the failure
                scores[name] = None
                scores[f"{name}_error"] = f"{type(e).__name__}: {e}"[:200]
    return scores


# ---------- report ----------

def write_report(rows: list[dict], report_path: Path):
    from app.config import settings

    ragas_rows = [r for r in rows if r.get("scores")]
    assert_rows = [r for r in rows if r.get("checks")]
    metric_names = ["faithfulness", "answer_relevancy"]

    def fmt(v):
        return f"{v:.2f}" if isinstance(v, float) else "—"

    lines = [
        "# Agent baseline — trajectory asserts + end-to-end answer quality",
        "",
        f"Judge: `{settings.judge_model}` via Gemini's OpenAI-compatible endpoint "
        f"(cross-model — generator is `{settings.generation_model}`, so no self-preference bias). "
        "Embeddings: local bge-small. Golden set: `golden.jsonl`. "
        "Retrieval metrics live in `retrieval-baseline.md` (evals/retrieval_eval.py).",
        "",
        "## Answer quality (judge)",
        "",
        "| id | agent | category | " + " | ".join(m.replace("_", " ") for m in metric_names) + " |",
        "|---|---|---|" + "---|" * len(metric_names),
    ]
    for r in ragas_rows:
        cells = " | ".join(fmt(r["scores"].get(m)) for m in metric_names)
        lines.append(f"| {r['row_id']} | {r['agent']} | {r['category']} | {cells} |")

    lines += ["", "### Averages by category (agent=store)", "",
              "| slice | n | " + " | ".join(m.replace("_", " ") for m in metric_names) + " |",
              "|---|---|" + "---|" * len(metric_names)]
    groups = defaultdict(list)
    for r in ragas_rows:
        groups[(r["agent"], r["category"])].append(r)
    for (agent, cat), grp in sorted(groups.items()):
        cells = []
        for m in metric_names:
            vals = [g["scores"][m] for g in grp if isinstance(g["scores"].get(m), float)]
            cells.append(f"{statistics.mean(vals):.2f}" if vals else "—")
        lines.append(f"| {agent} / {cat} | {len(grp)} | " + " | ".join(cells) + " |")

    lines += ["", "## Assert-based rows", "",
              "| id | agent | category | result | detail |", "|---|---|---|---|---|"]
    for r in assert_rows:
        statuses = [c["status"] for c in r["checks"]]
        overall = ("FAIL" if "FAIL" in statuses else
                   "REVIEW" if "REVIEW" in statuses else "PASS")
        detail = "; ".join(f"{c['check']}:{c['status']}" for c in r["checks"])
        lines.append(f"| {r['row_id']} | {r['agent']} | {r['category']} | **{overall}** | {detail} |")

    lines += ["", "## Answers needing eyes (FAIL / REVIEW / metric errors)", ""]
    for r in rows:
        flagged = any(c["status"] != "PASS" for c in r.get("checks", [])) or \
                  any(k.endswith("_error") for k in (r.get("scores") or {}))
        if flagged:
            lines += [f"### {r['row_id']} ({r['agent']}) — {r['question']}",
                      "", f"> {r['answer'][:1200]}", ""]
            if r.get("checks"):
                for c in r["checks"]:
                    if c["status"] != "PASS":
                        lines.append(f"- {c['check']}: **{c['status']}** {c['detail']}")
                lines.append("")
            for k, v in (r.get("scores") or {}).items():
                if k.endswith("_error"):
                    lines.append(f"- {k}: {v}")
    report_path.write_text("\n".join(lines) + "\n")


# ---------- main ----------

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated row ids")
    ap.add_argument("--skip-ragas", action="store_true")
    ap.add_argument("--from-runs", action="store_true",
                    help="score cached runs json instead of re-running agents")
    args = ap.parse_args()

    # score the cached runs — skip the (slow, occasionally-stalling) agent phase
    if args.from_runs:
        if not RUNS_JSON.exists():
            sys.exit(f"no cached runs at {RUNS_JSON} — run without --from-runs first")
        runs = json.loads(RUNS_JSON.read_text())
        if args.only:
            wanted = set(args.only.split(","))
            runs = [r for r in runs if r["row_id"] in wanted]
        await score_and_report(runs, args)
        return

    golden = load_golden()
    if args.only:
        wanted = set(args.only.split(","))
        golden = [g for g in golden if g["id"] in wanted]

    # 1. run agents. Store rows go through the API concurrently (abatch); the model API
    #    is the bottleneck, so this is ~Nx faster. Any non-store rows run sequentially.
    store_out = {}
    store_rows = [g for g in golden if g["agent"] == "store"]
    if store_rows:
        from app.agent import ask_batch
        print(f"[run] {len(store_rows)} store questions (concurrency={AGENT_CONCURRENCY})...",
              flush=True)
        outs = await ask_batch([g["question"] for g in store_rows], AGENT_CONCURRENCY)
        store_out = {g["id"]: o for g, o in zip(store_rows, outs)}

    runs = []
    for g in golden:
        if g["agent"] == "store":
            out = store_out[g["id"]]
        else:
            print(f"[run] {g['id']} ({g['agent']}): {g['question'][:50]}...", flush=True)
            try:
                out = run_agent(g["agent"], g["question"])
            except Exception as e:
                print(f"  ERROR: {e}")
                out = {"answer": f"(agent error: {e})", "sources": [], "contexts": [],
                       "retrieval_contexts": [], "tool_calls": []}
        runs.append({
            "row_id": g["id"], "agent": g["agent"], "category": g["category"],
            "scoring": g["scoring"], "question": g["question"],
            "reference": g.get("reference"), "expect": g.get("expect"),
            "answer": out["answer"], "sources": out["sources"],
            "contexts": out["contexts"],
            "retrieval_contexts": out.get("retrieval_contexts", out["contexts"]),
            "tool_calls": out["tool_calls"],
        })
    RUNS_JSON.write_text(json.dumps(runs, indent=2, ensure_ascii=False))
    print(f"[saved] raw runs -> {RUNS_JSON}")

    await score_and_report(runs, args)


async def score_and_report(runs: list[dict], args):
    # asserts
    for r in runs:
        if r["scoring"] in ("deterministic", "behavioral") and r["expect"]:
            r["checks"] = check_expect(r["expect"], r)

    # ragas
    if not args.skip_ragas:
        metrics = build_metrics()
        sem = asyncio.Semaphore(4)
        ragas_runs = [r for r in runs if r["scoring"] == "ragas"]
        tasks = []
        for r in ragas_runs:
            sample = {"user_input": r["question"], "response": r["answer"],
                      "retrieved_contexts": r.get("retrieval_contexts", r["contexts"])}
            tasks.append(score_sample(metrics, sample, sem, category=r["category"]))
        print(f"[ragas] scoring {len(ragas_runs)} samples x 2 metrics...", flush=True)
        all_scores = await asyncio.gather(*tasks)
        for r, s in zip(ragas_runs, all_scores):
            r["scores"] = s
            print(f"  {r['row_id']}: {s}")

    RUNS_JSON.write_text(json.dumps(runs, indent=2, ensure_ascii=False))
    write_report(runs, REPORT)
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    asyncio.run(main())
