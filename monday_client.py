"""Write pipeline results to a monday.com board through the GraphQL API.

  export MONDAY_API_TOKEN=...            # monday.com > Avatar > Developers > API token
  python monday_client.py setup          # creates the board, groups and columns once
  python pipeline.py --monday            # pushes results to it
  python pipeline.py --monday --dry-run  # prints the GraphQL calls, sends nothing

Board design:
  - One group per risk tier, so each compliance queue is a group on the board.
  - One item per application. Writes are idempotent: the item is found by its
    Application ID column and updated, so re-running never creates duplicates.
  - The full brief and the model's reasoning go in as an item update, so the
    reviewer sees the "why" next to the record, and every run leaves a dated trail.
  - The pipeline writes "Review status = Awaiting human review" and nothing else.
    Only a person changes it to Cleared / Rejected; monday.com's activity log
    records who did it and when (the human sign-off Priya asked for).
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://api.monday.com/v2"
API_VERSION = "2025-04"
CONFIG = Path(__file__).parent / "monday_board.json"

COLUMNS = [  # (key, title, monday column type)
    ("app_id", "Application ID", "text"),
    ("client_type", "Client type", "text"),
    ("aum", "AUM (USD)", "numbers"),
    ("submitted", "Submitted", "date"),
    ("risk", "Risk tier", "status"),
    ("model_risk", "Model tier", "text"),
    ("confidence", "AI confidence", "numbers"),
    ("complexity", "Complexity", "status"),
    ("queue", "Queue", "text"),
    ("review", "Review status", "status"),
    ("flags", "Red flags", "long_text"),
    ("next_step", "Next step", "long_text"),
]
GROUPS = [("high", "High risk - escalation"),
          ("enhanced", "Enhanced due diligence"),
          ("standard", "Standard review")]

_DRY_RUN = False
_fake_id = 1000


def gql(query: str, variables: dict | None = None, retries: int = 4) -> dict:
    global _fake_id
    if _DRY_RUN:
        print("  [dry-run] " + " ".join(query.split())[:110] + " ...")
        print("            variables: " + json.dumps(variables or {}, ensure_ascii=False)[:300])
        _fake_id += 1
        return _DryRunData(str(_fake_id))
    token = os.environ.get("MONDAY_API_TOKEN")
    if not token:
        sys.exit("Set MONDAY_API_TOKEN first (or use --dry-run)")
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(API_URL, json={"query": query, "variables": variables or {}},
                                 headers={"Authorization": token, "API-Version": API_VERSION},
                                 timeout=30)
        except requests.RequestException as exc:
            if attempt == retries:
                raise RuntimeError(f"monday.com unreachable: {exc}") from exc
            time.sleep(2 ** attempt)
            continue
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(int(resp.headers.get("Retry-After", 2 ** attempt)))
            continue
        body = resp.json()
        if body.get("errors") or body.get("error_code"):
            text = json.dumps(body)
            if ("Complexity" in text or "RATE_LIMIT" in text.upper()) and attempt < retries:
                time.sleep(20)  # complexity budget resets per minute
                continue
            raise RuntimeError(f"monday.com API error: {text[:500]}")
        return body["data"]
    raise RuntimeError("monday.com API: retries exhausted")


class _DryRunData(dict):
    """Answers any lookup with a fake id so dry runs exercise the whole flow."""

    def __init__(self, fake_id):
        super().__init__()
        self.fake_id = fake_id

    def __missing__(self, key):
        if key in ("items_page_by_column_values",):
            return {"items": []}
        return {"id": self.fake_id}


def setup(board_name: str = "Crestview Client Onboarding - AI Intake"):
    board_id = gql('mutation ($n: String!) { create_board(board_name: $n, board_kind: private) { id } }',
                   {"n": board_name})["create_board"]["id"]
    groups = {}
    for key, title in GROUPS:
        groups[key] = gql("mutation ($b: ID!, $t: String!) { create_group(board_id: $b, "
                          "group_name: $t) { id } }", {"b": board_id, "t": title})["create_group"]["id"]
    columns = {}
    for key, title, col_type in COLUMNS:
        q = ("mutation ($b: ID!, $t: String!) { create_column(board_id: $b, title: $t, "
             f"column_type: {col_type}) {{ id }} }}")
        columns[key] = gql(q, {"b": board_id, "t": title})["create_column"]["id"]
    cfg = {"board_id": board_id, "groups": groups, "columns": columns}
    if not _DRY_RUN:
        CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print(f"Created board {board_id}; ids saved to {CONFIG.name}")
    return cfg


def column_values(result, cols: dict) -> dict:
    ra, s = result.risk_assessment, result.summary
    flags = "\n".join(f"- {f.flag}: \"{f.evidence}\"" for f in ra.red_flags) or "None found"
    values = {
        cols["app_id"]: result.application_id,
        cols["client_type"]: result.client_type,
        cols["aum"]: str(int(result.estimated_aum)),
        cols["submitted"]: {"date": result.submission_date} if result.submission_date else None,
        cols["risk"]: {"label": result.final_risk_tier.capitalize()},
        cols["model_risk"]: result.model_risk_tier,
        cols["confidence"]: str(round(ra.confidence, 2)),
        cols["complexity"]: {"label": ra.complexity.capitalize()},
        cols["queue"]: result.routing_queue,
        cols["review"]: {"label": "Awaiting human review"},
        cols["flags"]: {"text": flags},
        cols["next_step"]: {"text": s.next_steps[0] if s.next_steps else ""},
    }
    return {k: v for k, v in values.items() if v is not None}


def update_body(result) -> str:
    ra, s = result.risk_assessment, result.summary
    lines = [f"<b>{s.headline}</b>", s.client_profile, "",
             f"<b>Risk: {result.final_risk_tier}</b> (model: {result.model_risk_tier}, "
             f"rules floor: {result.rule_floor_tier}, confidence {ra.confidence:.2f})",
             ra.reasoning]
    lines += [f"Guardrail: {a}" for a in result.tier_adjustments + result.policy_checks]
    if ra.red_flags:
        lines += ["", "<b>Red flags</b>"] + [
            f"- {f.flag}: \"{f.evidence}\"" + ("" if f.evidence_verified else " (not verified)")
            for f in ra.red_flags]
    lines += ["", "<b>Next steps</b>"] + [f"{i}. {step}" for i, step in enumerate(s.next_steps, 1)]
    if ra.missing_information:
        lines += ["", "<b>Missing</b>: " + ", ".join(ra.missing_information)]
    if ra.other_compliance_considerations:
        lines += ["<b>Other compliance items</b>: " + "; ".join(ra.other_compliance_considerations)]
    lines += ["", f"<i>AI pre-screen by {result.model}, prompts "
                  f"{', '.join(result.prompt_versions.values())}, {result.processed_at}. "
                  "Not a compliance decision.</i>"]
    return "<br>".join(lines)


def find_item(board_id: str, app_col: str, app_id: str) -> str | None:
    data = gql("query ($b: ID!, $c: String!, $v: String!) { items_page_by_column_values("
               "limit: 1, board_id: $b, columns: [{column_id: $c, column_values: [$v]}]) "
               "{ items { id } } }", {"b": board_id, "c": app_col, "v": app_id})
    items = data["items_page_by_column_values"]["items"]
    return items[0]["id"] if items else None


def push_results(results, dry_run: bool = False):
    global _DRY_RUN
    _DRY_RUN = dry_run
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    elif dry_run:
        print("No monday_board.json; dry run will show setup calls too")
        cfg = setup()
    else:
        sys.exit("No monday_board.json: run `python monday_client.py setup` first")
    board, cols = cfg["board_id"], cfg["columns"]
    for r in results:
        values = json.dumps(column_values(r, cols), ensure_ascii=False)
        group = cfg.get("groups", {}).get(r.final_risk_tier)
        item_id = find_item(board, cols["app_id"], r.application_id)
        if item_id:
            gql("mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values("
                "board_id: $b, item_id: $i, column_values: $v, create_labels_if_missing: true) { id } }",
                {"b": board, "i": item_id, "v": values})
            if group:
                gql("mutation ($i: ID!, $g: String!) { move_item_to_group(item_id: $i, group_id: $g) { id } }",
                    {"i": item_id, "g": group})
            action = "updated"
        else:
            q = ("mutation ($b: ID!, $n: String!, $v: JSON!" + (", $g: String!" if group else "") +
                 ") { create_item(board_id: $b, item_name: $n, column_values: $v, "
                 + ("group_id: $g, " if group else "") +
                 "create_labels_if_missing: true) { id } }")
            variables = {"b": board, "n": f"{r.client_name}", "v": values}
            if group:
                variables["g"] = group
            item_id = gql(q, variables)["create_item"]["id"]
            action = "created"
        gql("mutation ($i: ID!, $body: String!) { create_update(item_id: $i, body: $body) { id } }",
            {"i": item_id, "body": update_body(r)})
        print(f"  monday.com item {item_id} {action}: {r.application_id}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "setup":
        setup(*sys.argv[2:3])
    else:
        print(__doc__)
