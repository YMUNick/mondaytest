"""Compare pipeline output against hand-labelled expected tiers (the golden set).

  python evaluate.py                                   # output/results.json vs data/expected_tiers.csv
  python evaluate.py --results output_edge/results.json --expected data/expected_edge_tiers.csv

The metric compliance cares about most is MISSED HIGH-RISK: a case the labels
call high that the pipeline put lower. That number must be zero. Over-escalation
is tracked too, because it costs reviewer time, but it is the safer error.
Exit code is 1 if any high-risk case was missed, so this can gate CI.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ORDER = {"standard": 0, "enhanced": 1, "high": 2}


def evaluate(results: list[dict], expected: dict[str, list[str]], show=True) -> dict:
    stats = dict(ok=0, under=0, over=0, failed=0, missed_high=0, model_only_ok=0, total=0)
    if show:
        print(f"{'ID':<15}{'Expected':<18}{'Final':<10}{'Model':<10}Result")
    for r in results:
        want = expected.get(r["application_id"])
        if want is None:
            continue
        stats["total"] += 1
        got, model = r.get("final_risk_tier"), r.get("model_risk_tier")
        if model in want:
            stats["model_only_ok"] += 1
        if got is None:
            stats["failed"] += 1
            verdict = "FAILED"
        elif got in want:
            stats["ok"] += 1
            verdict = "ok"
        elif ORDER[got] < min(ORDER[t] for t in want):
            stats["under"] += 1
            verdict = "UNDER-ESCALATED"
            if "high" in want:
                stats["missed_high"] += 1
        else:
            stats["over"] += 1
            verdict = "over-escalated"
        if show:
            print(f"{r['application_id']:<15}{'|'.join(want):<18}{str(got):<10}{str(model):<10}{verdict}")
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=ROOT / "output" / "results.json")
    ap.add_argument("--expected", type=Path, default=ROOT / "data" / "expected_tiers.csv")
    args = ap.parse_args()

    with args.expected.open(encoding="utf-8") as f:
        expected = {row["application_id"]: row["acceptable_tiers"].split("|")
                    for row in csv.DictReader(f)}
    results = json.loads(args.results.read_text(encoding="utf-8"))
    s = evaluate(results, expected)
    print(f"\nWithin acceptable tiers: {s['ok']}/{s['total']}   "
          f"(model alone, before guardrails: {s['model_only_ok']}/{s['total']})")
    print(f"Under-escalated: {s['under']}   Over-escalated: {s['over']}   Failed: {s['failed']}")
    print(f"MISSED HIGH-RISK: {s['missed_high']}  (must be 0)")
    sys.exit(1 if s["missed_high"] else 0)


if __name__ == "__main__":
    main()
