"""Write pipeline results to a monday.com board through the GraphQL API.

  export MONDAY_API_TOKEN=...             # monday.com > Avatar > Developers > API token
  python monday_client.py link <board id> # use a board you already have (maps its columns)
  python monday_client.py setup           # or create a new board, groups and columns once
  python pipeline.py --monday             # pushes results, then opens the board
  python pipeline.py --monday --dry-run   # prints the GraphQL calls, sends nothing

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
import re
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
    ("services", "Requested services", "text"),
    ("tier_source", "Tier source", "status"),  # who set the tier: always "AI" (a pre-screen)
]
DEFAULT_TYPES = {key: col_type for key, _, col_type in COLUMNS}
GROUPS = [("high", "High risk - escalation"),
          ("enhanced", "Enhanced due diligence"),
          ("standard", "Standard review")]

# Titles an existing board may use for each column (compared case- and punctuation-blind).
ALIASES = {
    "app_id": ["application id", "app id", "application"],
    "client_type": ["client type", "type"],
    "aum": ["aum usd", "aum", "estimated aum"],
    "submitted": ["submitted", "submission date", "date submitted"],
    "risk": ["risk tier", "risk", "tier", "final tier", "final risk tier"],
    "model_risk": ["model tier", "ai tier", "model risk tier", "model risk"],
    "confidence": ["ai confidence", "confidence"],
    "complexity": ["complexity"],
    "queue": ["queue", "routing", "routed to", "compliance queue", "owner"],
    "review": ["review status", "review"],
    "flags": ["red flags", "flags"],
    "next_step": ["next step", "next steps"],
    "services": ["requested services", "services"],
    "tier_source": ["tier source", "tier resource", "risk source", "tier origin", "source"],
}
# When a status column has its own labels, pick the one that means this value.
LABEL_HINTS = {"review": r"^await", "tier_source": r"\bai\b"}
APP_ID = re.compile(r"\b(?:APP-\d{4}-\d{4}|EDGE-\d{3}|CUSTOM-\d{3})\b")
GROUP_WORDS = {"high": ("high", "escalat"), "enhanced": ("enhanced", "edd", "due diligence"),
               "standard": ("standard",)}

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


def fmt(col_type: str, value):
    """Shape one value the way monday.com expects for that column type."""
    if value is None or value == "":
        return None
    if col_type in ("status", "color"):
        return {"label": str(value)}
    if col_type == "dropdown":
        return {"labels": [str(value)]}
    if col_type in ("long_text", "long-text"):
        return {"text": str(value)}
    if col_type == "date":
        return {"date": str(value)}
    return str(value)  # text, numbers and anything else take a plain string


def pick_label(key: str, value, options: list[str] | None):
    """Use the board's own label for a value: exact match first, then the key's hint."""
    if not options or value is None:
        return value
    for option in options:
        if option.lower() == str(value).lower():
            return option
    hint = LABEL_HINTS.get(key)
    if hint:
        for option in options:
            if re.search(hint, option, re.IGNORECASE):
                return option
    return value


def column_values(result, cols: dict, types: dict | None = None, labels: dict | None = None) -> dict:
    ra, s = result.risk_assessment, result.summary
    types = {**DEFAULT_TYPES, **(types or {})}
    flags = "\n".join(f"- {f.flag}: \"{f.evidence}\"" for f in ra.red_flags) or "None found"
    raw = {
        "app_id": result.application_id,
        "client_type": result.client_type,
        "aum": int(result.estimated_aum),
        "submitted": result.submission_date or None,
        "risk": result.final_risk_tier.capitalize(),
        "model_risk": result.model_risk_tier,
        "confidence": round(ra.confidence, 2),
        "complexity": ra.complexity.capitalize(),
        "queue": result.routing_queue,
        "review": "Awaiting human review",
        "flags": flags,
        "next_step": s.next_steps[0] if s.next_steps else "",
        "services": result.requested_services,
        "tier_source": "AI",
    }
    labels = labels or {}
    values = {cols[k]: fmt(types[k], pick_label(k, v, labels.get(k)) if types[k] in ("status", "dropdown") else v)
              for k, v in raw.items() if k in cols}
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


def _norm(text: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in text.lower()).split())


def _labels(col: dict) -> list[str]:
    try:
        settings = json.loads(col.get("settings_str") or "{}")
    except ValueError:
        return []
    raw = settings.get("labels") or {}
    if isinstance(raw, dict):
        return [str(v) for v in raw.values()]
    return [str(x.get("name")) for x in raw if isinstance(x, dict) and x.get("name")]


def link(board_id: str, create: bool = False):
    """Use an existing board as it is: map its columns and groups by title.

    Nothing is added unless create=True. Without an Application ID column, items
    are matched by the application id written in the item name ("APP-2026-0306 · ...").
    """
    data = gql("query ($b: [ID!]) { boards(ids: $b) { id name url columns { id title type settings_str } "
               "groups { id title } } }", {"b": [str(board_id)]})
    if not data["boards"]:
        sys.exit(f"Board {board_id} not found, or the token cannot see it")
    board = data["boards"][0]
    by_title = {_norm(c["title"]): c for c in board["columns"]}
    columns, types, labels = {}, {}, {}
    for key, title, col_type in COLUMNS:
        match = next((by_title[a] for a in ALIASES[key] if a in by_title), None)
        if match:
            columns[key], types[key] = match["id"], match["type"]
            if match["type"] in ("status", "dropdown"):
                labels[key] = _labels(match)
            print(f"  {title:<20} -> {match['title']!r} ({match['type']})")
        elif create:
            q = ("mutation ($b: ID!, $t: String!) { create_column(board_id: $b, title: $t, "
                 f"column_type: {col_type}) {{ id }} }}")
            columns[key] = gql(q, {"b": board["id"], "t": title})["create_column"]["id"]
            types[key] = col_type
            print(f"  {title:<20} -> created ({col_type})")
        else:
            note = "matched by item name" if key == "app_id" else "not on the board; kept in the item update"
            print(f"  {title:<20} -> {note}")
    groups = {}
    for tier, title in GROUPS:
        match = next((g for g in board["groups"]
                      if any(w in g["title"].lower() for w in GROUP_WORDS[tier])), None)
        if match:
            groups[tier] = match["id"]
            print(f"  group {tier:<14} -> {match['title']!r}")
        elif create:
            groups[tier] = gql("mutation ($b: ID!, $t: String!) { create_group(board_id: $b, "
                               "group_name: $t) { id } }",
                               {"b": board["id"], "t": title})["create_group"]["id"]
            print(f"  group {tier:<14} -> created {title!r}")
    if not groups:
        print("  groups: none per tier; items stay in their group, the Risk tier column carries the tier")
    cfg = {"board_id": board["id"], "name": board["name"], "url": board.get("url"),
           "groups": groups, "columns": columns, "types": types, "labels": labels}
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"Linked board {board['name']!r} ({board['id']}); mapping saved to {CONFIG.name}")
    return cfg


def find_item(board_id: str, app_col: str, app_id: str) -> str | None:
    data = gql("query ($b: ID!, $c: String!, $v: String!) { items_page_by_column_values("
               "limit: 1, board_id: $b, columns: [{column_id: $c, column_values: [$v]}]) "
               "{ items { id } } }", {"b": board_id, "c": app_col, "v": app_id})
    items = data["items_page_by_column_values"]["items"]
    return items[0]["id"] if items else None


def existing_items(board_id: str, app_col: str | None) -> dict[str, str]:
    """Application id -> item id for every item on the board (one paged read)."""
    fields = "id name" + (f' column_values(ids: ["{app_col}"]) {{ text }}' if app_col else "")
    page = gql("query ($b: [ID!]) { boards(ids: $b) { items_page(limit: 500) { cursor items { "
               + fields + " } } } }", {"b": [board_id]})["boards"][0]["items_page"]
    found = {}
    while True:
        for item in page["items"]:
            text = (item.get("column_values") or [{}])[0].get("text") if app_col else None
            match = APP_ID.search(item["name"])
            key = text or (match.group(0) if match else None)
            if key:
                found.setdefault(key, item["id"])
        if not page.get("cursor"):
            return found
        page = gql("query ($c: String!) { next_items_page(limit: 500, cursor: $c) { cursor items { "
                   + fields + " } } }", {"c": page["cursor"]})["next_items_page"]


def push_results(results, dry_run: bool = False):
    global _DRY_RUN
    _DRY_RUN = dry_run
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    elif dry_run:
        print("No monday_board.json; dry run will show setup calls too")
        cfg = setup()
    else:
        sys.exit("No monday_board.json: run `python monday_client.py link <board id>` "
                 "or `python monday_client.py setup` first")
    board, cols = cfg["board_id"], cfg["columns"]
    types, labels = cfg.get("types"), cfg.get("labels")
    app_col = cols.get("app_id")
    known = None if dry_run else existing_items(board, app_col)
    for r in results:
        values = column_values(r, cols, types, labels)
        group = cfg.get("groups", {}).get(r.final_risk_tier)
        if known is not None:
            item_id = known.get(r.application_id)
        else:
            item_id = find_item(board, app_col, r.application_id) if app_col else None
        if item_id:
            values.pop(cols.get("review"), None)  # never overwrite a reviewer's decision
            gql("mutation ($b: ID!, $i: ID!, $v: JSON!) { change_multiple_column_values("
                "board_id: $b, item_id: $i, column_values: $v, create_labels_if_missing: true) { id } }",
                {"b": board, "i": item_id, "v": json.dumps(values, ensure_ascii=False)})
            if group:
                gql("mutation ($i: ID!, $g: String!) { move_item_to_group(item_id: $i, group_id: $g) { id } }",
                    {"i": item_id, "g": group})
            action = "updated"
        else:
            q = ("mutation ($b: ID!, $n: String!, $v: JSON!" + (", $g: String!" if group else "") +
                 ") { create_item(board_id: $b, item_name: $n, column_values: $v, "
                 + ("group_id: $g, " if group else "") +
                 "create_labels_if_missing: true) { id } }")
            variables = {"b": board, "n": f"{r.application_id} \u00b7 {r.client_name}",
                         "v": json.dumps(values, ensure_ascii=False)}
            if group:
                variables["g"] = group
            item_id = gql(q, variables)["create_item"]["id"]
            action = "created"
        gql("mutation ($i: ID!, $body: String!) { create_update(item_id: $i, body: $body) { id } }",
            {"i": item_id, "body": update_body(r)})
        print(f"  monday.com item {item_id} {action}: {r.application_id} {r.final_risk_tier}")
    return cfg.get("url")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "setup":
        setup(*sys.argv[2:3])
    elif len(sys.argv) >= 3 and sys.argv[1] == "link":
        link(sys.argv[2], create="--create" in sys.argv)
    else:
        print(__doc__)
