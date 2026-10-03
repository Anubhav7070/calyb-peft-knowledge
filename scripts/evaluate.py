"""Qualitative evaluation: run eval/eval_set.json, compare to hand-written expectations, write eval/eval_report.json.
Pass/fail counts are over a tiny hand-written set and are NOT a performance metric."""
import _path  # noqa
import json, time
from peft_kb import knowledge as K
from peft_kb.reasoning import InputError, reason

ks = K.load("knowledge/knowledge_state.json")
rows = []
for case in json.load(open("eval/eval_set.json", encoding="utf-8")):
    t0 = time.perf_counter()
    try:
        r = reason(case["input"], ks)
    except InputError as e:
        r = {"status": "error", "error": str(e), "candidates": []}
    ms = (time.perf_counter() - t0) * 1000
    top = [c["id"] for c in r.get("candidates", [])]
    ok = r["status"] == case["expect_status"] and all(x in top for x in case["expect_top_contains"])
    rows.append({"id": case["id"], "input": case["input"], "expected_status": case["expect_status"],
                 "expected_top_contains": case["expect_top_contains"], "actual_status": r["status"],
                 "actual_top": top, "matches_expectation": ok, "latency_ms": round(ms, 2),
                 "known_limitation": case.get("known_limitation"),
                 "trace": r.get("reasoning_trace"), "why_top": [c["why"] for c in r.get("candidates", [])[:1]]})
    print(f"{case['id']}: {'match' if ok else 'MISMATCH'} (status={r['status']}, top={top[:3]})")
json.dump(rows, open("eval/eval_report.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"{sum(r['matches_expectation'] for r in rows)}/{len(rows)} cases matched expectations (qualitative, tiny set)")
