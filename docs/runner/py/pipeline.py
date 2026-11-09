"""Crestview intelligent client intake: raw applications in, enriched records out.

For each application:
  1. Load       validate and normalise the row; bad rows are reported, not fatal
  2. Rules      deterministic red-flag rules set a minimum risk tier
  3. Risk       the model assesses risk and complexity, quoting its evidence
  4. Guardrails final tier = max(rules, model); low confidence goes up a tier;
                every quoted piece of evidence is checked against the source text;
                the routing queue is set by code from the final tier
  5. Summary    the model writes an operations brief FROM the final risk result
  6. Checks     the brief is checked against policy (routing first, tier stated,
                no "approved" language) and corrected in code if needed
  7. Output     results.json, results.csv, report.html, audit_log.jsonl
                (+ optional monday.com board)

Usage:
  python pipeline.py                          # all applications, v4 prompts (default)
  python pipeline.py --ids APP-2026-0303      # one or more ids (live demo)
  python pipeline.py --prompt-version v1      # the original prompts, for comparison
  python pipeline.py --monday                 # also write to the monday.com board
  python pipeline.py --monday --dry-run       # print the monday.com calls, send nothing
  LLM_PROVIDER=mock python pipeline.py        # offline plumbing test
"""
import argparse
import csv
import hashlib
import json
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

import mock_llm
from llm import LLMClient, LLMError, LLMResponse
from rules import policy_tier, run_rules
from schemas import (ROUTING, TIER_ORDER, TIERS, Application, OnboardingSummary,
                     ProcessedApplication, RiskAssessment)

ROOT = Path(__file__).parent
PROMPTS = ROOT / "prompts"
CONFIDENCE_THRESHOLD = 0.7
DEFAULT_PROMPT_VERSION = "v4"


# ---------- loading ----------

def load_applications(path: Path) -> tuple[list[Application], list[str]]:
    """Read the CSV. Invalid rows are skipped and described, never fatal."""
    apps, errors, seen = [], [], set()
    with path.open(newline="", encoding="utf-8-sig") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            row = {(k or "").strip(): v for k, v in row.items()}
            try:
                app = Application(**row)
            except ValidationError as exc:
                err = exc.errors()[0]
                field = ".".join(str(p) for p in err["loc"])
                errors.append(f"line {line_no} ({row.get('application_id') or '?'}): "
                              f"{field}: {err['msg']}")
                continue
            if app.application_id in seen:
                errors.append(f"line {line_no}: duplicate application_id {app.application_id}")
                continue
            seen.add(app.application_id)
            apps.append(app)
    return apps, errors


def app_as_text(app: Application) -> str:
    text = "\n".join([
        f"Application ID: {app.application_id}",
        f"Client name: {app.client_name}",
        f"Client type: {app.client_type}",
        f"Requested services: {app.requested_services}",
        f"Estimated AUM (USD): {app.estimated_aum:,.0f}",
        f"Submitted: {app.submission_date}",
        f"Description: {app.description}",
    ])
    # The application sits inside <application> tags; stop it from closing them.
    return re.sub(r"</?\s*application\s*>", "[tag removed]", text, flags=re.IGNORECASE)


# ---------- audit ----------

class Auditor:
    """Append-only JSONL log of every model call. Thread-safe."""

    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self._lock = threading.Lock()
        self.input_tokens = 0
        self.output_tokens = 0

    def log(self, **record):
        record = {"ts": datetime.now(timezone.utc).isoformat(), "run_id": self.run_id, **record}
        with self._lock:
            self.input_tokens += record.get("input_tokens", 0)
            self.output_tokens += record.get("output_tokens", 0)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------- model calls with validation ----------

def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in ``` fences or add a sentence; take the object."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("no JSON object in model output")
    return json.loads(match.group(0))


def call_and_validate(llm, prompt, model_cls, stage, app_id, prompt_version, auditor,
                      mock_text=None):
    """Call the model, validate against the schema, retry once with the error message."""
    attempt_prompt = prompt
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:12]
    for attempt in (1, 2):
        resp = (LLMResponse(mock_text) if llm.provider == "mock"
                else llm.complete(attempt_prompt))
        meta = dict(stage=stage, application_id=app_id, attempt=attempt,
                    provider=llm.provider, model=llm.model, prompt_version=prompt_version,
                    input_sha256=prompt_hash, input_tokens=resp.input_tokens,
                    output_tokens=resp.output_tokens, latency_ms=resp.latency_ms,
                    output=resp.text)
        try:
            result = model_cls(**parse_json(resp.text))
            auditor.log(**meta, valid=True)
            return result
        except (ValueError, ValidationError, TypeError) as exc:
            auditor.log(**meta, valid=False, error=str(exc)[:500])
            attempt_prompt = (prompt + "\n\nYour previous answer was invalid: "
                              f"{str(exc)[:300]}\nReturn only the corrected JSON object.")
    raise LLMError(f"{stage}: model output failed validation twice")


def load_prompt(name: str, version: str) -> tuple[str, str]:
    path = PROMPTS / f"{name}_{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    data = path.read_bytes()
    return data.decode("utf-8"), f"{path.stem}@{hashlib.sha256(data).hexdigest()[:8]}"


# ---------- guardrails ----------

def normalise(text: str) -> str:
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def apply_guardrails(risk: RiskAssessment, floor: str, description: str):
    """Decide the final tier. The model can raise the tier, never lower it."""
    adjustments = []
    final = risk.risk_tier
    if TIER_ORDER[floor] > TIER_ORDER[final]:
        adjustments.append(f"Raised from {final} to {floor}: deterministic rules set a floor")
        final = floor
    if risk.high_risk_checks is not None:  # v3+: escalation policy applied in code
        policy, reasons = policy_tier(risk)
        if TIER_ORDER[policy] > TIER_ORDER[final]:
            adjustments.append(f"Raised from {final} to {policy}: escalation policy "
                               f"({'; '.join(reasons)})")
            final = policy
    if risk.confidence < CONFIDENCE_THRESHOLD and final != "high":
        raised = TIERS[TIER_ORDER[final] + 1]
        adjustments.append(f"Raised from {final} to {raised}: model confidence "
                           f"{risk.confidence:.2f} below {CONFIDENCE_THRESHOLD}")
        final = raised

    source = normalise(description)
    for flag in risk.red_flags:
        flag.evidence_verified = bool(normalise(flag.evidence)) and normalise(flag.evidence) in source
    unverified = [f.flag for f in risk.red_flags if not f.evidence_verified]
    if unverified:
        adjustments.append("Evidence not found verbatim in the application for: "
                           + ", ".join(unverified) + " (reviewer should check)")
    return final, adjustments


APPROVAL_LANGUAGE = re.compile(
    r"\b(client|account|application|onboarding)\s+(is|has been|was|been)\s+"
    r"(pre-?)?(approved|cleared|accepted)\b", re.IGNORECASE)


def check_summary(summary: OnboardingSummary, final_tier: str, queue: str) -> list[str]:
    """Deterministic checks on the brief. Fixes what it can and says what it did."""
    notes = []
    first = summary.next_steps[0] if summary.next_steps else ""
    if not first.lower().startswith("[compliance]"):
        summary.next_steps.insert(0, f"[Compliance] Route to {queue} before any account "
                                     "opening or funding.")
        notes.append("First next step did not route to compliance; routing step added by code")
    if final_tier not in summary.risk_note.lower():
        summary.risk_note = f"Pre-screen tier: {final_tier}. {summary.risk_note}"
        notes.append("Risk note did not state the final tier; tier prefixed by code")
    text = " ".join([summary.headline, summary.client_profile, summary.risk_note,
                     *summary.next_steps])
    if APPROVAL_LANGUAGE.search(text):
        notes.append("Brief contains approval language; reviewer must not rely on it")
    if summary.owner and summary.owner != queue:
        notes.append(f"Model suggested owner '{summary.owner}', routing set by code to '{queue}'")
    summary.owner = queue
    return notes


# ---------- one application ----------

def process(app: Application, llm: LLMClient, auditor: Auditor,
            version: str = DEFAULT_PROMPT_VERSION) -> ProcessedApplication:
    base = dict(application_id=app.application_id, client_name=app.client_name,
                client_type=app.client_type, requested_services=app.requested_services,
                estimated_aum=app.estimated_aum, submission_date=app.submission_date,
                model=f"{llm.provider}:{llm.model}",
                processed_at=datetime.now(timezone.utc).isoformat())
    try:
        risk_tpl, risk_ver = load_prompt("risk_assessment", version)
        sum_tpl, sum_ver = load_prompt("onboarding_summary", version)
        base["prompt_versions"] = {"risk": risk_ver, "summary": sum_ver}

        hits, floor = run_rules(app.description)
        app_text = app_as_text(app)

        risk = call_and_validate(
            llm, risk_tpl.replace("{application}", app_text), RiskAssessment, "risk",
            app.application_id, risk_ver, auditor,
            mock_text=mock_llm.mock_risk(app, hits, floor) if llm.provider == "mock" else None)
        model_tier = risk.risk_tier
        final_tier, adjustments = apply_guardrails(risk, floor, app.description)
        queue = ROUTING[final_tier]

        # The summary sees the FINAL tier, so it can never describe a lower risk.
        risk_for_summary = risk.model_dump()
        risk_for_summary["risk_tier"] = final_tier
        risk_for_summary["guardrail_adjustments"] = adjustments
        summary_prompt = (sum_tpl.replace("{application}", app_text)
                          .replace("{routing_queue}", queue)
                          .replace("{risk_assessment}", json.dumps(risk_for_summary, indent=2)))
        summary = call_and_validate(
            llm, summary_prompt, OnboardingSummary, "summary", app.application_id,
            sum_ver, auditor,
            mock_text=mock_llm.mock_summary(app, final_tier, queue) if llm.provider == "mock" else None)
        policy_notes = check_summary(summary, final_tier, queue)

        return ProcessedApplication(
            **base, status="processed", final_risk_tier=final_tier,
            model_risk_tier=model_tier, rule_floor_tier=floor, routing_queue=queue,
            tier_adjustments=adjustments, policy_checks=policy_notes, rule_hits=hits,
            risk_assessment=risk, summary=summary)
    except Exception as exc:  # one bad record must not stop the batch
        return ProcessedApplication(**base, status="failed",
                                    error=f"{type(exc).__name__}: {str(exc)[:480]}")


# ---------- output ----------

def write_outputs(results: list[ProcessedApplication], out_dir: Path):
    (out_dir / "results.json").write_text(
        json.dumps([r.model_dump() for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8")
    with (out_dir / "results.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["application_id", "client_name", "client_type", "estimated_aum", "status",
                    "final_risk_tier", "model_risk_tier", "rule_floor_tier", "confidence",
                    "complexity", "routing_queue", "red_flags", "missing_information",
                    "other_compliance_considerations", "headline", "next_steps",
                    "adjustments", "policy_checks", "needs_human_review", "error"])
        for r in results:
            ra, s = r.risk_assessment, r.summary
            w.writerow([
                r.application_id, r.client_name, r.client_type, int(r.estimated_aum),
                r.status, r.final_risk_tier, r.model_risk_tier, r.rule_floor_tier,
                ra.confidence if ra else "", ra.complexity if ra else "", r.routing_queue or "",
                "; ".join(fl.flag for fl in ra.red_flags) if ra else "",
                "; ".join(ra.missing_information) if ra else "",
                "; ".join(ra.other_compliance_considerations) if ra else "",
                s.headline if s else "",
                " | ".join(s.next_steps) if s else "",
                " | ".join(r.tier_adjustments), " | ".join(r.policy_checks),
                r.needs_human_review, r.error or ""])


def print_table(results: list[ProcessedApplication]):
    print(f"\n{'ID':<15}{'Client':<34}{'Tier':<11}{'Model':<10}{'Rules':<10}"
          f"{'Conf':<6}{'Cmplx':<8}Queue")
    for r in results:
        if r.status == "failed":
            print(f"{r.application_id:<15}{r.client_name[:32]:<34}FAILED     {r.error}")
            continue
        changed = " *" if r.final_risk_tier != r.model_risk_tier else ""
        print(f"{r.application_id:<15}{r.client_name[:32]:<34}{r.final_risk_tier + changed:<11}"
              f"{r.model_risk_tier:<10}{r.rule_floor_tier:<10}"
              f"{r.risk_assessment.confidence:<6.2f}{r.risk_assessment.complexity:<8}"
              f"{r.routing_queue}")
    print("* final tier raised by guardrails")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--input", default=ROOT / "data" / "crestview_client_applications.csv", type=Path)
    ap.add_argument("--out", default=ROOT / "output", type=Path)
    ap.add_argument("--ids", nargs="*", help="only process these application ids")
    ap.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION, choices=["v1", "v2", "v3", "v4"])
    ap.add_argument("--workers", type=int, default=4, help="parallel applications (default 4)")
    ap.add_argument("--monday", action="store_true", help="write results to the monday.com board")
    ap.add_argument("--dry-run", action="store_true", help="with --monday: print calls, send nothing")
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    apps, load_errors = load_applications(args.input)
    for err in load_errors:
        print(f"Skipped invalid row, {err}", file=sys.stderr)
    if args.ids:
        wanted = set(args.ids)
        apps = [a for a in apps if a.application_id in wanted]
    if not apps:
        sys.exit("No valid applications to process.")

    try:
        llm = LLMClient()
    except LLMError as exc:
        sys.exit(f"Model provider not available: {exc}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    auditor = Auditor(args.out / "audit_log.jsonl", run_id)
    print(f"Run {run_id}: {len(apps)} applications, {llm.provider}:{llm.model}, "
          f"prompts {args.prompt_version}, {args.workers} workers")

    started = time.perf_counter()
    lock = threading.Lock()

    def run_one(app):
        result = process(app, llm, auditor, args.prompt_version)
        with lock:
            print(f"  {app.application_id} {app.client_name[:40]:<40} "
                  f"{result.final_risk_tier or 'FAILED'}", flush=True)
        return result

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(run_one, apps))  # keeps input order
    elapsed = time.perf_counter() - started

    write_outputs(results, args.out)
    from report import write_report
    write_report(results, args.out / "report.html", run_id=run_id,
                 load_errors=load_errors)
    print_table(results)
    ok = sum(r.status == "processed" for r in results)
    print(f"\n{ok}/{len(results)} processed, {len(results) - ok} failed, "
          f"{len(load_errors)} rows skipped at load | {elapsed:.1f}s | "
          f"tokens in {auditor.input_tokens:,} out {auditor.output_tokens:,}")
    print(f"Wrote {args.out / 'results.json'}, results.csv, report.html, audit_log.jsonl")

    if args.monday:
        from monday_client import push_results
        push_results([r for r in results if r.status == "processed"], dry_run=args.dry_run)
    return results


if __name__ == "__main__":
    main()
