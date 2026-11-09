"""Run-to-run consistency check for the risk stage.

LLMs are not perfectly deterministic even at temperature 0. Compliance needs to
know how often the same application gets a different tier. This runs only the
risk stage N times per application and reports where the model's tier changed.

  python consistency.py --runs 3
  python consistency.py --runs 5 --ids APP-2026-0305 APP-2026-0313
"""
import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llm import LLMClient
from pipeline import (Auditor, app_as_text, apply_guardrails, call_and_validate,
                      load_applications, load_prompt)
from rules import run_rules
from schemas import RiskAssessment

ROOT = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--input", type=Path, default=ROOT / "data" / "crestview_client_applications.csv")
    ap.add_argument("--prompt-version", default="v4")
    args = ap.parse_args()

    apps, _ = load_applications(args.input)
    if args.ids:
        apps = [a for a in apps if a.application_id in set(args.ids)]
    llm = LLMClient()
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    auditor = Auditor(out / "consistency_log.jsonl", "consistency")
    tpl, ver = load_prompt("risk_assessment", args.prompt_version)

    def one(app):
        hits, floor = run_rules(app.description)
        risk = call_and_validate(llm, tpl.replace("{application}", app_as_text(app)),
                                 RiskAssessment, "risk", app.application_id, ver, auditor)
        final, _ = apply_guardrails(risk, floor, app.description)
        return app.application_id, risk.risk_tier, final, risk.confidence

    jobs = [a for a in apps for _ in range(args.runs)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(one, jobs))

    by_app: dict[str, list] = {}
    for app_id, model, final, conf in rows:
        by_app.setdefault(app_id, []).append((model, final, conf))
    stable_model = stable_final = 0
    print(f"{'ID':<15}{'Model tiers':<34}{'Final tiers':<34}Confidence range")
    for app_id, runs in by_app.items():
        m, f = Counter(x[0] for x in runs), Counter(x[1] for x in runs)
        confs = [x[2] for x in runs]
        stable_model += len(m) == 1
        stable_final += len(f) == 1
        print(f"{app_id:<15}{json.dumps(dict(m)):<34}{json.dumps(dict(f)):<34}"
              f"{min(confs):.2f}-{max(confs):.2f}")
    n = len(by_app)
    print(f"\n{args.runs} runs each. Model tier identical across runs: {stable_model}/{n}. "
          f"Final tier (after guardrails) identical: {stable_final}/{n}.")


if __name__ == "__main__":
    main()
