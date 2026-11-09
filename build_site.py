"""Build the one-page demo site (docs/index.html) for GitHub Pages.

Everything on the page comes from files already in the repo: the last pipeline
run in output/ and output_edge/, the golden sets in data/, the test suite and a
monday.com dry run. No model calls are made, so rebuilding costs nothing:

  python build_site.py            # -> docs/index.html
"""
import contextlib
import csv
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import evaluate as ev  # noqa: E402
import monday_client  # noqa: E402
from pipeline import load_applications  # noqa: E402
from schemas import ProcessedApplication  # noqa: E402

REPO_URL = "https://github.com/YMUNick/mondaytest"
TIER_LABEL = {"standard": "Standard", "enhanced": "Enhanced", "high": "High"}

# ---------------------------------------------------------------- data


def load_results(path: Path) -> list[ProcessedApplication]:
    return [ProcessedApplication(**r) for r in json.loads(path.read_text(encoding="utf-8"))]


def load_expected(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        return {r["application_id"]: r["acceptable_tiers"].split("|") for r in csv.DictReader(f)}


def run_evaluate(results_path: Path, expected_path: Path) -> tuple[dict, str, list[dict]]:
    """Same logic and wording as `python evaluate.py`, captured as text."""
    results = json.loads(results_path.read_text(encoding="utf-8"))
    expected = load_expected(expected_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        s = ev.evaluate(results, expected)
        print(f"\nWithin acceptable tiers: {s['ok']}/{s['total']}   "
              f"(model alone, before guardrails: {s['model_only_ok']}/{s['total']})")
        print(f"Under-escalated: {s['under']}   Over-escalated: {s['over']}   Failed: {s['failed']}")
        print(f"MISSED HIGH-RISK: {s['missed_high']}  (must be 0)")
    rows = []
    for r in results:
        want = expected.get(r["application_id"])
        if want is None:
            continue
        got = r.get("final_risk_tier")
        if got is None:
            verdict = "failed"
        elif got in want:
            verdict = "ok"
        elif ev.ORDER[got] < min(ev.ORDER[t] for t in want):
            verdict = "under"
        else:
            verdict = "over"
        rows.append(dict(id=r["application_id"], name=r["client_name"], want=want, got=got,
                         model=r.get("model_risk_tier"), verdict=verdict))
    return s, buf.getvalue().rstrip(), rows


def run_tests() -> tuple[str, list[str], str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:anyio", "-v", "--no-header"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env)
    names = re.findall(r"::(\w+) PASSED", proc.stdout)
    tail = next((l.strip("= ").strip() for l in reversed(proc.stdout.splitlines())
                 if " passed" in l or " failed" in l), "no result")
    return tail, names, "ok" if proc.returncode == 0 else "fail"


def run_dry_run(results: list[ProcessedApplication]) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        monday_client.push_results([r for r in results if r.status == "processed"], dry_run=True)
    return buf.getvalue().rstrip()


def run_meta(audit_path: Path) -> dict:
    rows = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    run_id = max(r["run_id"] for r in rows)
    mine = [r for r in rows if r["run_id"] == run_id]
    start = datetime.strptime(run_id.split("-")[0], "%Y%m%dT%H%M%SZ")
    end = max(datetime.fromisoformat(r["ts"]).replace(tzinfo=None) for r in mine)
    return dict(run_id=run_id, calls=len(mine), model=mine[0]["model"],
                provider=mine[0]["provider"],
                prompts=sorted({r["prompt_version"] for r in mine}),
                tokens_in=sum(r["input_tokens"] for r in mine),
                tokens_out=sum(r["output_tokens"] for r in mine),
                seconds=(end - start).total_seconds(),
                retries=sum(1 for r in mine if r["attempt"] > 1),
                date=start.strftime("%d %b %Y, %H:%M UTC"))


# ---------------------------------------------------------------- html helpers


def pill(tier, small=False):
    if not tier:
        return '<span class="pill pill-failed">Failed</span>'
    cls = " pill-sm" if small else ""
    return f'<span class="pill pill-{tier}{cls}"><i></i>{TIER_LABEL[tier]}</span>'


def ul(items, empty="None"):
    if not items:
        return f'<p class="muted small">{escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{escape(i)}</li>" for i in items) + "</ul>"


def highlight(text: str, quotes: list[str]) -> str:
    out = escape(text)
    for q in quotes:
        eq = escape(q.strip())
        if eq and eq in out:
            out = out.replace(eq, f"<mark>{eq}</mark>", 1)
    return out


def money(v: float) -> str:
    return f"${v / 1e9:,.1f}B" if v >= 1e9 else f"${v / 1e6:,.1f}M"


def card(r: ProcessedApplication, app_text: str, set_key: str) -> str:
    cid = f"{set_key}-{r.application_id}"
    if r.status == "failed":
        return (f'<details class="case" id="{cid}" data-tier="failed"><summary>'
                f'<span class="case-id">{escape(r.application_id)}</span>'
                f'<span class="case-name">{escape(r.client_name)}</span>{pill(None)}</summary>'
                f'<div class="case-body"><p class="warn">{escape(r.error or "")}</p></div></details>')
    ra, s = r.risk_assessment, r.summary
    flags = "".join(
        f'<li><b>{escape(f.flag)}</b> <span class="tag">{escape(f.category)}</span>'
        f'<q>{escape(f.evidence)}</q>'
        + ('<span class="ok small">&#10003; quote found in application</span>' if f.evidence_verified
           else '<span class="warn small">&#10007; not found verbatim</span>') + "</li>"
        for f in ra.red_flags)
    flags = f'<ul class="flags">{flags}</ul>' if flags else '<p class="muted small">None identified</p>'
    rules = "".join(
        f'<li>{escape(h.rule)} &rarr; at least {pill(h.min_tier, True)} <code>{escape(h.matched_text)}</code></li>'
        for h in r.rule_hits)
    rules = f"<ul>{rules}</ul>" if rules else '<p class="muted small">No rule matched</p>'
    quotes = [f.evidence for f in ra.red_flags if f.evidence_verified]
    raised = r.final_risk_tier != r.model_risk_tier
    steps = "".join(f"<li>{escape(x)}</li>" for x in s.next_steps)
    return f"""
<details class="case" id="{cid}" data-tier="{r.final_risk_tier}">
<summary><span class="case-id">{escape(r.application_id)}</span>
<span class="case-name">{escape(r.client_name)}</span>
{pill(r.final_risk_tier)}{'<span class="raised" title="Final tier raised above the model tier by guardrails">raised</span>' if raised else ''}
<span class="case-queue">{escape(r.routing_queue or '')}</span></summary>
<div class="case-body">
 <p class="headline">{escape(s.headline)}</p>
 <p class="muted">{escape(s.client_profile)}</p>
 <div class="tierline">
  <div><span class="lbl">Final tier</span>{pill(r.final_risk_tier)}</div>
  <div><span class="lbl">Model said</span>{pill(r.model_risk_tier)}</div>
  <div><span class="lbl">Rules floor</span>{pill(r.rule_floor_tier)}</div>
  <div><span class="lbl">Confidence</span><b class="num">{ra.confidence:.2f}</b></div>
  <div><span class="lbl">Complexity</span><b>{escape(ra.complexity)}</b></div>
 </div>
 <div class="cols">
  <div>
   <h4>Why this tier</h4>
   <p>{escape(ra.reasoning)}</p>
   <h4>Red flags, with evidence</h4>{flags}
   <h4>Deterministic rule hits</h4>{rules}
   <h4>Guardrail actions</h4>{ul(r.tier_adjustments + r.policy_checks, "None needed")}
  </div>
  <div>
   <h4>Onboarding brief</h4>
   <p><b>Risk:</b> {escape(s.risk_note)}</p>
   <p><b>Complexity:</b> {escape(s.complexity_note)}</p>
   <h4>Next steps</h4><ol>{steps}</ol>
   <h4>Missing information</h4>{ul(ra.missing_information)}
   <h4>Other compliance considerations</h4>{ul(ra.other_compliance_considerations)}
  </div>
 </div>
 <details class="source"><summary>Original application text{' (verified quotes highlighted)' if quotes else ''}</summary>
  <p>{highlight(app_text, quotes)}</p></details>
 <p class="fine">{escape(r.model or '')} &middot; {escape(', '.join(r.prompt_versions.values()))} &middot;
 AI pre-screen, awaiting human review. Not a compliance decision.</p>
</div></details>"""


def results_panel(key, results, apps, load_errors, active):
    tiers = Counter(r.final_risk_tier or "failed" for r in results)
    raised = sum(1 for r in results if r.status == "processed" and r.final_risk_tier != r.model_risk_tier)
    rows = "".join(
        f'<tr data-tier="{r.final_risk_tier or "failed"}" data-target="{key}-{escape(r.application_id)}" tabindex="0">'
        f'<td class="nowrap mono">{escape(r.application_id)}</td><td>{escape(r.client_name)}</td>'
        f'<td>{escape(r.client_type)}</td><td class="nowrap num">{money(r.estimated_aum)}</td>'
        f'<td>{pill(r.final_risk_tier)}</td><td>{pill(r.model_risk_tier, True) if r.model_risk_tier else ""}</td>'
        f'<td>{escape(r.risk_assessment.complexity) if r.risk_assessment else ""}</td>'
        f'<td class="queue">{escape(r.routing_queue or r.error or "")}</td></tr>'
        for r in results)
    skipped = ""
    if load_errors:
        skipped = ('<div class="callout callout-warn"><b>Rejected at load, before any model call</b>'
                   + ul(load_errors) + "</div>")
    cards = "".join(card(r, apps.get(r.application_id, ""), key) for r in results)
    hidden = "" if active else " hidden"
    return f"""
<div class="panel" id="panel-{key}" role="tabpanel" aria-labelledby="tab-{key}"{hidden}>
 <div class="stats">
  <div class="stat"><b class="num">{tiers.get('high', 0)}</b><span>{pill('high', True)} escalation</span></div>
  <div class="stat"><b class="num">{tiers.get('enhanced', 0)}</b><span>{pill('enhanced', True)} due diligence</span></div>
  <div class="stat"><b class="num">{tiers.get('standard', 0)}</b><span>{pill('standard', True)} review</span></div>
  <div class="stat"><b class="num">{raised}</b><span>raised by guardrails</span></div>
  <div class="stat"><b class="num">{tiers.get('failed', 0) + len(load_errors)}</b><span>failed or rejected</span></div>
 </div>
 {skipped}
 <div class="filters" role="group" aria-label="Filter by tier">
  <button class="chip is-on" data-filter="all">All</button>
  <button class="chip" data-filter="high">High</button>
  <button class="chip" data-filter="enhanced">Enhanced</button>
  <button class="chip" data-filter="standard">Standard</button>
  <button class="chip chip-ghost" data-expand>Expand all</button>
 </div>
 <div class="tablewrap"><table class="tbl clickable">
  <thead><tr><th>ID</th><th>Client</th><th>Type</th><th>AUM</th><th>Final tier</th><th>Model</th>
  <th>Complexity</th><th>Routed to</th></tr></thead><tbody>{rows}</tbody></table></div>
 <p class="muted small">Click a row to open its full pre-screen below.</p>
 <div class="cases">{cards}</div>
</div>"""


def eval_table(rows):
    verdict = {"ok": '<span class="ok">&#10003; within range</span>',
               "over": '<span class="amber">&#9650; over-escalated</span>',
               "under": '<span class="warn">&#9660; MISSED</span>',
               "failed": '<span class="warn">failed</span>'}
    body = "".join(
        f'<tr><td class="nowrap mono">{escape(x["id"])}</td><td>{escape(x["name"])}</td>'
        f'<td>{" ".join(pill(t, True) for t in x["want"])}</td><td>{pill(x["got"], True)}</td>'
        f'<td>{pill(x["model"], True)}</td><td class="nowrap">{verdict[x["verdict"]]}</td></tr>'
        for x in rows)
    return ('<div class="tablewrap"><table class="tbl"><thead><tr><th>ID</th><th>Client</th>'
            '<th>Acceptable</th><th>Final</th><th>Model alone</th><th>Result</th></tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def board_preview(results):
    groups = [("high", "High risk - escalation"), ("enhanced", "Enhanced due diligence"),
              ("standard", "Standard review")]
    out = []
    for tier, title in groups:
        items = [r for r in results if r.final_risk_tier == tier]
        rows = "".join(
            f'<tr><td class="b-item">{escape(r.client_name)}</td><td class="mono nowrap">{escape(r.application_id)}</td>'
            f'<td><span class="b-status b-{tier}">{TIER_LABEL[tier]}</span></td>'
            f'<td>{escape(r.model_risk_tier or "")}</td><td class="num">{r.risk_assessment.confidence:.2f}</td>'
            f'<td>{escape(r.risk_assessment.complexity.capitalize())}</td>'
            f'<td><span class="b-status b-review">Awaiting human review</span></td>'
            f'<td class="b-next"><div class="clamp" title="{escape(r.summary.next_steps[0] if r.summary.next_steps else "")}">'
            f'{escape(r.summary.next_steps[0] if r.summary.next_steps else "")}</div></td></tr>'
            for r in items) or '<tr><td colspan="8" class="muted">No items in this group on this run</td></tr>'
        out.append(f"""<div class="b-group b-g-{tier}"><p class="b-title">{escape(title)} <span class="muted">{len(items)} items</span></p>
<div class="tablewrap"><table class="b-tbl"><thead><tr><th>Client</th><th>Application ID</th><th>Risk tier</th>
<th>Model tier</th><th>AI confidence</th><th>Complexity</th><th>Review status</th><th>Next step</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>""")
    return "".join(out)


def cmd(text):
    return (f'<div class="cmd"><code>{escape(text)}</code>'
            f'<button class="copy" data-copy="{escape(text)}" aria-label="Copy command">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/>'
            '<path d="M5 15V6a2 2 0 0 1 2-2h9"/></svg><span>Copy</span></button></div>')


# ---------------------------------------------------------------- page


def build() -> str:
    golden = load_results(ROOT / "output" / "results.json")
    edge = load_results(ROOT / "output_edge" / "results.json")
    apps_main, _ = load_applications(ROOT / "data" / "crestview_client_applications.csv")
    apps_edge, edge_errors = load_applications(ROOT / "data" / "edge_cases.csv")
    texts = {a.application_id: a.description for a in apps_main + apps_edge}

    g_stats, g_text, g_rows = run_evaluate(ROOT / "output" / "results.json",
                                           ROOT / "data" / "expected_tiers.csv")
    e_stats, e_text, e_rows = run_evaluate(ROOT / "output_edge" / "results.json",
                                           ROOT / "data" / "expected_edge_tiers.csv")
    test_tail, test_names, test_state = run_tests()
    dry = run_dry_run(golden)
    meta = run_meta(ROOT / "output" / "audit_log.jsonl")
    n_calls = dry.count("[dry-run]")

    per_app = (meta["tokens_in"] + meta["tokens_out"]) / max(1, len(golden))
    missed = g_stats["missed_high"] + e_stats["missed_high"]
    over = g_stats["over"] + e_stats["over"]
    over_note = ""
    over_rows = [x for x in g_rows + e_rows if x["verdict"] == "over"]
    if over_rows:
        by_id = {r.application_id: r for r in golden + edge}
        items = "".join(
            f'<li><b>{escape(x["name"])}</b> ({escape(x["id"])}): '
            f'{escape("; ".join(by_id[x["id"]].tier_adjustments) or "model tier above the label")}</li>'
            for x in over_rows)
        over_note = ('<div class="callout callout-warn"><b>Honest note on this run.</b> '
                     + ("One case was" if len(over_rows) == 1 else f"{len(over_rows)} cases were")
                     + f' rated higher than the label allows:<ul>{items}</ul>'
                     'That is the safe direction of error: it costs a reviewer some time and never lets a '
                     'risky client through. The red flags the model tags can vary from run to run, which is '
                     'why the escalation rule lives in code and the final call stays with a person.</div>')

    test_list = "".join(f"<li><span class='ok'>&#10003;</span> {escape(n.removeprefix('test_').replace('_', ' '))}</li>"
                        for n in test_names)

    return PAGE.format(
        css=CSS, js=JS, repo=REPO_URL,
        n_golden=len(golden), n_edge=len(edge) + len(edge_errors),
        g_ok=g_stats["ok"], g_total=g_stats["total"], g_model=g_stats["model_only_ok"],
        e_ok=e_stats["ok"], e_total=e_stats["total"], e_model=e_stats["model_only_ok"],
        missed=missed, over=over, over_note=over_note,
        n_tests=len(test_names), test_tail=escape(test_tail), test_list=test_list,
        test_state="passed" if test_state == "ok" else "FAILED",
        seconds=f"{meta['seconds']:.0f}", per_app=f"{per_app / 1000:.1f}k",
        tokens_in=f"{meta['tokens_in']:,}", tokens_out=f"{meta['tokens_out']:,}",
        calls=meta["calls"], retries=meta["retries"], model=escape(meta["model"]),
        provider=escape(meta["provider"]), run_id=escape(meta["run_id"]), run_date=escape(meta["date"]),
        prompts=escape(", ".join(meta["prompts"])),
        cmd_pipeline=cmd("python pipeline.py --monday --dry-run"),
        cmd_one=cmd("python pipeline.py --ids APP-2026-0303"),
        cmd_eval=cmd("python evaluate.py"),
        cmd_eval_edge=cmd("python evaluate.py --results output_edge/results.json --expected data/expected_edge_tiers.csv"),
        cmd_test=cmd("python -m pytest -q -p no:anyio"),
        cmd_mock=cmd("LLM_PROVIDER=mock python pipeline.py"),
        g_eval_text=escape(g_text), e_eval_text=escape(e_text),
        g_table=eval_table(g_rows), e_table=eval_table(e_rows),
        panel_golden=results_panel("golden", golden, texts, [], True),
        panel_edge=results_panel("edge", edge, texts, edge_errors, False),
        board=board_preview([r for r in golden if r.status == "processed"]),
        dry=escape(dry), n_dry=n_calls,
        built=datetime.now().strftime("%d %b %Y"),
    )


# ---------------------------------------------------------------- template

CSS = r"""
:root{
 --bg:#F7F5F0;--surface:#FFFFFF;--surface-2:#EFECE4;--ink:#14213D;--ink-2:#3F4A5C;--muted:#5B6474;
 --line:#E2DED4;--accent:#2F5BEA;--accent-ink:#FFFFFF;--warm:#C2410C;
 --std:#166534;--std-bg:#DCF2E3;--enh:#8A4B00;--enh-bg:#FCEBCB;--high:#B42318;--high-bg:#FBE1DE;
 --code-bg:#14213D;--code-ink:#E6EAF2;--code-dim:#93A0B8;--mark:#FFE69A;
 --shadow:0 1px 2px rgba(20,33,61,.06),0 4px 16px rgba(20,33,61,.05);
 --serif:"Source Serif 4",Georgia,serif;--sans:"IBM Plex Sans",system-ui,"Segoe UI",sans-serif;
 --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
:root[data-theme="dark"]{
 --bg:#0E1424;--surface:#161E33;--surface-2:#1D2740;--ink:#E8ECF4;--ink-2:#C3CBDA;--muted:#98A3B8;
 --line:#2A3550;--accent:#7FA0FF;--accent-ink:#0E1424;--warm:#FB8A55;
 --std:#7FDCA0;--std-bg:#15362A;--enh:#F5C46A;--enh-bg:#3A2C10;--high:#FF9C8F;--high-bg:#3F1A18;
 --code-bg:#0A0F1C;--code-ink:#DCE3F0;--code-dim:#7D8AA3;--mark:#6B5A12;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.25);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --bg:#0E1424;--surface:#161E33;--surface-2:#1D2740;--ink:#E8ECF4;--ink-2:#C3CBDA;--muted:#98A3B8;
 --line:#2A3550;--accent:#7FA0FF;--accent-ink:#0E1424;--warm:#FB8A55;
 --std:#7FDCA0;--std-bg:#15362A;--enh:#F5C46A;--enh-bg:#3A2C10;--high:#FF9C8F;--high-bg:#3F1A18;
 --code-bg:#0A0F1C;--code-ink:#DCE3F0;--code-dim:#7D8AA3;--mark:#6B5A12;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 4px 16px rgba(0,0,0,.25);}}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:72px}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 var(--sans);-webkit-text-size-adjust:100%}
a{color:var(--accent)}
.skip{position:absolute;left:-999px;top:8px;background:var(--accent);color:var(--accent-ink);padding:8px 12px;border-radius:8px;z-index:100}
.skip:focus{left:8px}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
@media (min-width:768px){.wrap{padding:0 32px}}
/* header */
.top{position:sticky;top:0;z-index:40;background:color-mix(in srgb,var(--bg) 88%,transparent);
 backdrop-filter:saturate(1.4) blur(10px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:16px;height:60px}
.brand{font-weight:600;white-space:nowrap;color:var(--ink);text-decoration:none;display:flex;align-items:center;gap:8px}
.brand svg{width:22px;height:22px;stroke:var(--accent);fill:none;stroke-width:2}
.nav{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;flex:1;min-width:0}
.nav::-webkit-scrollbar{display:none}
.nav a{color:var(--ink-2);text-decoration:none;font-size:14px;padding:8px 10px;border-radius:8px;white-space:nowrap}
.nav a:hover,.nav a.is-active{background:var(--surface-2);color:var(--ink)}
.iconbtn{flex:none;width:40px;height:40px;border-radius:10px;border:1px solid var(--line);background:var(--surface);
 color:var(--ink);cursor:pointer;display:grid;place-items:center}
.iconbtn svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2}
@media (max-width:640px){.brand span{display:none}}
/* hero */
.hero{padding-top:56px;padding-bottom:40px}
.eyebrow{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 12px}
h1,h2{font-family:var(--serif);font-weight:600;line-height:1.15;letter-spacing:-.01em;margin:0}
h1{font-size:clamp(32px,5vw,52px);max-width:18ch}
h2{font-size:clamp(26px,3.4vw,36px)}
h3{font-size:19px;margin:0 0 6px;line-height:1.3}
h4{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:18px 0 6px}
.lede{font-size:clamp(17px,2vw,19px);color:var(--ink-2);max-width:62ch;margin:16px 0 0}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:32px 0 0}
@media (min-width:768px){.kpis{grid-template-columns:repeat(4,1fr)}}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px;box-shadow:var(--shadow)}
.kpi b{display:block;font-family:var(--serif);font-size:34px;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi span{font-size:14px;color:var(--muted)}
.kpi.good b{color:var(--std)}
.principle{margin:20px 0 0;display:flex;gap:14px;align-items:flex-start;background:var(--ink);color:var(--bg);
 border-radius:14px;padding:18px 20px}
:root[data-theme="dark"] .principle{background:var(--surface-2);color:var(--ink)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .principle{background:var(--surface-2);color:var(--ink)}}
.principle svg{flex:none;width:28px;height:28px;stroke:var(--warm);fill:none;stroke-width:2;margin-top:2px}
.principle p{margin:0}
.principle b{font-family:var(--serif);font-size:20px;display:block}
/* sections */
section{padding:56px 0;border-top:1px solid var(--line)}
.sec-head{display:flex;flex-direction:column;gap:8px;margin-bottom:28px;max-width:70ch}
.sec-head p{margin:0;color:var(--ink-2)}
.muted{color:var(--muted)}.small{font-size:14px}.fine{font-size:13px;color:var(--muted);margin:16px 0 0}
.mono{font-family:var(--mono);font-size:14px}.num{font-variant-numeric:tabular-nums}.nowrap{white-space:nowrap}
.ok{color:var(--std)}.warn{color:var(--high)}.amber{color:var(--enh)}
/* flow */
.flow{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;counter-reset:st}
@media (min-width:768px){.flow{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (min-width:1024px){.flow{grid-template-columns:repeat(4,minmax(0,1fr))}}
.st{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;position:relative}
.st::before{counter-increment:st;content:counter(st);position:absolute;top:14px;right:16px;font-family:var(--serif);
 font-size:22px;color:var(--line)}
.st p{margin:6px 0 0;font-size:14px;color:var(--ink-2)}
.badge{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:99px;letter-spacing:.02em}
.b-ai{background:color-mix(in srgb,var(--accent) 14%,transparent);color:var(--accent)}
.b-code{background:var(--surface-2);color:var(--ink-2)}
.b-human{background:color-mix(in srgb,var(--warm) 15%,transparent);color:var(--warm)}
.rules{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;margin-top:24px}
@media (min-width:768px){.rules{grid-template-columns:repeat(2,minmax(0,1fr))}}
.rule{border-left:3px solid var(--accent);padding:4px 0 4px 14px}
.rule b{display:block}.rule span{font-size:15px;color:var(--ink-2)}
/* demo steps */
.steps{display:flex;flex-direction:column;gap:16px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:var(--shadow);
 display:grid;grid-template-columns:44px minmax(0,1fr);gap:16px}
@media (max-width:560px){.step{grid-template-columns:minmax(0,1fr);padding:16px}}
.step-n{width:44px;height:44px;border-radius:12px;background:var(--ink);color:var(--bg);display:grid;place-items:center;
 font-family:var(--serif);font-size:22px;font-weight:600}
.step-body{min-width:0}
.step-body>p{margin:6px 0 0;color:var(--ink-2)}
.say{margin:12px 0 0;padding:12px 14px;background:var(--surface-2);border-radius:10px;font-size:15px}
.say b{color:var(--warm)}
.cmd{display:flex;align-items:center;gap:8px;background:var(--code-bg);color:var(--code-ink);border-radius:10px;
 padding:6px 6px 6px 14px;margin:12px 0 0;min-width:0}
.cmd code{font-family:var(--mono);font-size:14px;flex:1;min-width:0;overflow-x:auto;white-space:nowrap;padding:6px 0;
 background:none;color:inherit;border-radius:0}
.cmd code::before{content:"$ ";color:var(--code-dim)}
.copy{flex:none;display:flex;align-items:center;gap:6px;min-height:36px;padding:0 10px;border-radius:8px;border:0;cursor:pointer;
 background:rgba(255,255,255,.08);color:var(--code-ink);font:500 13px var(--sans);transition:background .2s}
.copy:hover{background:rgba(255,255,255,.16)}
.copy svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2}
.out{margin:12px 0 0}
.out>summary,.source>summary{cursor:pointer;font-size:14px;font-weight:600;color:var(--accent);padding:6px 0;list-style:none;
 display:flex;align-items:center;gap:6px}
.out>summary::-webkit-details-marker,.source>summary::-webkit-details-marker,.case>summary::-webkit-details-marker{display:none}
.out>summary::before,.source>summary::before{content:"";width:8px;height:8px;border-right:2px solid currentColor;
 border-bottom:2px solid currentColor;transform:rotate(-45deg);transition:transform .2s}
.out[open]>summary::before,.source[open]>summary::before{transform:rotate(45deg)}
pre.term{background:var(--code-bg);color:var(--code-ink);font:13px/1.55 var(--mono);padding:14px 16px;border-radius:10px;
 overflow:auto;max-height:420px;margin:8px 0 0;white-space:pre}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-size:14px;margin:10px 0 0}
.kv dt{color:var(--muted)}.kv dd{margin:0;font-family:var(--mono);font-size:13px;word-break:break-word}
.explain{margin:12px 0 0;display:grid;grid-template-columns:minmax(0,1fr);gap:10px}
@media (min-width:768px){.explain{grid-template-columns:repeat(2,minmax(0,1fr))}}
.explain div{border:1px solid var(--line);border-radius:10px;padding:12px 14px;font-size:15px}
.explain b{display:block;margin-bottom:2px}
.testlist{columns:1;font-size:14px;margin:8px 0 0;padding:0;list-style:none}
@media (min-width:768px){.testlist{columns:2}}
.testlist li{break-inside:avoid;padding:2px 0}
/* tabs + filters */
.tabs{display:flex;gap:6px;border-bottom:1px solid var(--line);margin-bottom:20px;overflow-x:auto}
.tab{appearance:none;background:none;border:0;border-bottom:3px solid transparent;padding:10px 14px;font:600 15px var(--sans);
 color:var(--muted);cursor:pointer;white-space:nowrap;min-height:44px}
.tab[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px}
@media (min-width:768px){.stats{grid-template-columns:repeat(5,1fr)}}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-family:var(--serif);font-size:28px;line-height:1.1}
.stat span{font-size:13px;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.chip{min-height:36px;padding:0 14px;border-radius:99px;border:1px solid var(--line);background:var(--surface);color:var(--ink-2);
 font:500 14px var(--sans);cursor:pointer;transition:background .2s,color .2s}
.chip:hover{border-color:var(--accent)}
.chip.is-on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.chip-ghost{margin-left:auto}
/* tables */
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
.tbl,.b-tbl{width:100%;border-collapse:collapse;font-size:14px}
.tbl th,.tbl td,.b-tbl th,.b-tbl td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
.tbl tr:last-child td,.b-tbl tr:last-child td{border-bottom:0}
.tbl th,.b-tbl th{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;background:var(--surface-2);white-space:nowrap}
.clickable tbody tr{cursor:pointer;transition:background .15s}
.clickable tbody tr:hover,.clickable tbody tr:focus-visible{background:var(--surface-2)}
.queue{color:var(--ink-2);min-width:180px}
.clickable{min-width:900px}.clickable td:nth-child(2){min-width:170px}.clickable td:nth-child(3){min-width:120px}
.hist{min-width:0}
tr[hidden]{display:none}
/* pills */
.pill{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:99px;font-size:13px;font-weight:600;white-space:nowrap}
.pill i{width:7px;height:7px;border-radius:50%;background:currentColor}
.pill-sm{font-size:12px;padding:1px 8px}
.pill-standard{color:var(--std);background:var(--std-bg)}
.pill-enhanced{color:var(--enh);background:var(--enh-bg)}
.pill-high{color:var(--high);background:var(--high-bg)}
.pill-high i{border-radius:1px;transform:rotate(45deg)}
.pill-enhanced i{border-radius:0;width:0;height:0;background:none;border-left:4px solid transparent;border-right:4px solid transparent;border-bottom:7px solid currentColor}
.pill-failed{color:var(--muted);background:var(--surface-2)}
/* cases */
.cases{display:flex;flex-direction:column;gap:10px;margin-top:20px}
.case{background:var(--surface);border:1px solid var(--line);border-radius:14px;scroll-margin-top:76px}
.case[hidden]{display:none}
.case>summary{cursor:pointer;list-style:none;padding:14px 18px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;min-height:52px}
.case>summary:hover{background:var(--surface-2);border-radius:14px}
.case-id{font-family:var(--mono);font-size:13px;color:var(--muted)}
.case-name{font-weight:600}
.case-queue{margin-left:auto;font-size:13px;color:var(--muted)}
.raised{font-size:12px;font-weight:600;color:var(--warm);border:1px solid currentColor;border-radius:99px;padding:0 8px}
.case-body{padding:4px 18px 18px;border-top:1px solid var(--line)}
.headline{font-family:var(--serif);font-size:20px;font-weight:600;margin:14px 0 4px}
.tierline{display:flex;flex-wrap:wrap;gap:10px 24px;padding:12px 14px;margin:14px 0 0;background:var(--surface-2);border-radius:10px}
.tierline div{display:flex;flex-direction:column;gap:4px}
.lbl{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
.cols{display:grid;grid-template-columns:minmax(0,1fr);gap:8px 32px}
@media (min-width:900px){.cols{grid-template-columns:repeat(2,minmax(0,1fr))}}
.cols p{margin:0 0 8px;font-size:15px}
.cols ul,.cols ol{margin:0;padding-left:20px;font-size:15px}
.cols li{margin:4px 0}
.flags li{margin:0 0 10px}
.flags q{display:block;font-style:italic;color:var(--ink-2);margin:2px 0}
.tag{font-size:12px;color:var(--muted);background:var(--surface-2);padding:0 6px;border-radius:4px}
code{font-family:var(--mono);font-size:13px;background:var(--surface-2);padding:1px 5px;border-radius:4px}
.source{margin:16px 0 0}
.source p{font-size:15px;background:var(--surface-2);border-radius:10px;padding:12px 14px;margin:6px 0 0}
mark{background:var(--mark);color:inherit;padding:0 2px;border-radius:2px}
.callout{border:1px solid var(--line);border-left:4px solid var(--accent);background:var(--surface);border-radius:10px;
 padding:14px 16px;margin:16px 0;font-size:15px}
.callout-warn{border-left-color:var(--warm)}
.callout ul{margin:6px 0 0;padding-left:20px}
/* eval */
.grid2{display:grid;grid-template-columns:minmax(0,1fr);gap:24px}
@media (min-width:1024px){.grid2{grid-template-columns:minmax(0,3fr) minmax(0,2fr)}}
.hist td:first-child{font-weight:600}
/* board */
.b-group{margin:0 0 18px;border-left:4px solid var(--line);padding-left:12px}
.b-g-high{border-left-color:var(--high)}.b-g-enhanced{border-left-color:var(--enh)}.b-g-standard{border-left-color:var(--std)}
.b-title{font-weight:600;margin:0 0 8px}
.b-g-high .b-title{color:var(--high)}.b-g-enhanced .b-title{color:var(--enh)}.b-g-standard .b-title{color:var(--std)}
.b-item{font-weight:500;min-width:200px}
.b-status{display:inline-block;padding:3px 10px;border-radius:4px;font-size:13px;font-weight:600;white-space:nowrap;color:#fff}
.b-high{background:#D83A52}.b-enhanced{background:#C77700}.b-standard{background:#1F8A55}.b-review{background:#5B6474}
.b-next{min-width:340px;font-size:13px;color:var(--ink-2)}
.clamp{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.b-tbl td{padding:8px 12px}.b-title .muted{font-weight:400;font-size:14px}
footer{padding:40px 0 56px;border-top:1px solid var(--line);font-size:14px;color:var(--muted)}
footer p{margin:4px 0}
"""

JS = r"""
(function(){
 var root=document.documentElement,key='crestview-theme';
 function setTheme(t){if(t){root.setAttribute('data-theme',t)}else{root.removeAttribute('data-theme')}}
 try{var saved=localStorage.getItem(key);if(saved)setTheme(saved)}catch(e){}
 document.getElementById('theme').addEventListener('click',function(){
  var dark=root.getAttribute('data-theme')==='dark'||(!root.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches);
  var next=dark?'light':'dark';setTheme(next);try{localStorage.setItem(key,next)}catch(e){}
 });
 document.querySelectorAll('.copy').forEach(function(b){b.addEventListener('click',function(){
  var label=b.querySelector('span'),t=b.getAttribute('data-copy');
  function done(ok){label.textContent=ok?'Copied':'Select';setTimeout(function(){label.textContent='Copy'},1600)}
  if(navigator.clipboard){navigator.clipboard.writeText(t).then(function(){done(true)},function(){done(false)})}else{done(false)}
 })});
 var tabs=document.querySelectorAll('.tab');
 tabs.forEach(function(t){t.addEventListener('click',function(){
  tabs.forEach(function(o){o.setAttribute('aria-selected',o===t?'true':'false');
   document.getElementById(o.getAttribute('aria-controls')).hidden=o!==t});
 })});
 document.querySelectorAll('.panel').forEach(function(p){
  var chips=p.querySelectorAll('[data-filter]');
  chips.forEach(function(c){c.addEventListener('click',function(){
   var f=c.getAttribute('data-filter');
   chips.forEach(function(o){o.classList.toggle('is-on',o===c)});
   p.querySelectorAll('tbody tr, .case').forEach(function(el){el.hidden=!(f==='all'||el.getAttribute('data-tier')===f)});
  })});
  var ex=p.querySelector('[data-expand]');
  ex.addEventListener('click',function(){
   var cases=p.querySelectorAll('.case:not([hidden])'),open=ex.textContent==='Expand all';
   cases.forEach(function(c){c.open=open});ex.textContent=open?'Collapse all':'Expand all';
  });
  p.querySelectorAll('tbody tr[data-target]').forEach(function(r){
   function go(){var c=document.getElementById(r.getAttribute('data-target'));if(c){c.open=true;c.scrollIntoView({block:'start'})}}
   r.addEventListener('click',go);r.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}});
  });
 });
 var links=document.querySelectorAll('.nav a'),secs=[].map.call(links,function(a){return document.querySelector(a.getAttribute('href'))});
 if('IntersectionObserver' in window){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){
   var i=secs.indexOf(e.target);links.forEach(function(l,j){l.classList.toggle('is-active',i===j)})}})},{rootMargin:'-40% 0px -55% 0px'});
  secs.forEach(function(s){if(s)io.observe(s)});
 }
})();
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crestview AI Intake</title>
<meta name="description" content="Proof of concept: AI risk pre-screen and onboarding brief for Crestview Capital client applications, with guardrails, evaluation and a monday.com board integration.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap">
 <a class="brand" href="#overview"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l8 4v5c0 4.5-3.4 8.4-8 9-4.6-.6-8-4.5-8-9V7z"/><path d="M9 12l2 2 4-4"/></svg><span>Crestview AI Intake</span></a>
 <nav class="nav" aria-label="Sections">
  <a href="#how">How it works</a><a href="#demo">Demo</a><a href="#results">Results</a>
  <a href="#evaluation">Evaluation</a><a href="#monday">monday.com</a>
 </nav>
 <button class="iconbtn" id="theme" aria-label="Toggle light or dark theme"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg></button>
</div></header>

<main id="main">
<div class="wrap hero" id="overview">
 <p class="eyebrow">Proof of concept &middot; Crestview Capital Group &times; monday.com</p>
 <h1>From raw application to an explained risk pre-screen</h1>
 <p class="lede">Each client application is read by an AI model that pulls out the facts and quotes its evidence.
 Code then applies Crestview's escalation policy, picks the compliance queue and checks the AI's work.
 A second model call writes the onboarding brief, and every result lands on a monday.com board, waiting for a person to decide.</p>
 <div class="kpis">
  <div class="kpi good"><b>{missed}</b><span>missed high-risk cases (must be 0)</span></div>
  <div class="kpi"><b>{g_ok}/{g_total}</b><span>sample applications within the labelled tier</span></div>
  <div class="kpi"><b>{e_ok}/{e_total}</b><span>adversarial edge cases, incl. prompt injection</span></div>
  <div class="kpi"><b>~{seconds}s</b><span>for {n_golden} applications, {per_app} tokens each</span></div>
 </div>
 <div class="principle"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l8 4v5c0 4.5-3.4 8.4-8 9-4.6-.6-8-4.5-8-9V7z"/><path d="M12 8v5M12 16h.01"/></svg>
  <p><b>AI can escalate, never clear.</b> Rules and code set a minimum tier the model cannot go below.
  Every record is marked &ldquo;Awaiting human review&rdquo;, and only a person can change that.</p></div>
</div>

<section id="how"><div class="wrap">
 <div class="sec-head"><p class="eyebrow">How it works</p><h2>Two model calls, wrapped in code that owns the decisions</h2>
 <p>The model extracts and explains. Code enforces policy, routing and checks. People decide.</p></div>
 <div class="flow">
  <div class="st"><span class="badge b-code">Code</span><h3>Load &amp; validate</h3><p>Normalises &ldquo;$1,200,000&rdquo;, &ldquo;35M&rdquo; and mixed date formats. Bad rows are reported, not fatal.</p></div>
  <div class="st"><span class="badge b-code">Code</span><h3>Rules floor</h3><p>Deterministic patterns (shell companies, PEPs, nominee directors, injected instructions) set a minimum tier.</p></div>
  <div class="st"><span class="badge b-ai">AI #1</span><h3>Risk pre-screen</h3><p>Fills a fact checklist and lists red flags, each with a verbatim quote, plus complexity, missing information and confidence.</p></div>
  <div class="st"><span class="badge b-code">Code</span><h3>Policy &amp; guardrails</h3><p>Final tier = max(rules, policy, model). Confidence &lt; 0.7 raises a tier. Every quote is checked against the source.</p></div>
  <div class="st"><span class="badge b-code">Code</span><h3>Routing</h3><p>The compliance queue comes from the final tier through a fixed map, never from the model.</p></div>
  <div class="st"><span class="badge b-ai">AI #2</span><h3>Onboarding brief</h3><p>Written from the final risk result and queue: client profile, risk note, owner-tagged next steps.</p></div>
  <div class="st"><span class="badge b-code">Code</span><h3>Brief checks</h3><p>The first step must hand off to compliance and the tier must be stated. &ldquo;Approved&rdquo; or &ldquo;cleared&rdquo; wording is flagged.</p></div>
  <div class="st"><span class="badge b-human">People</span><h3>Board &amp; review</h3><p>JSON, CSV, audit log and a monday.com item per client, grouped by tier, awaiting a named reviewer.</p></div>
 </div>
 <div class="rules">
  <div class="rule"><b>Explainable</b><span>Every red flag carries a quote that is machine-checked against the application, and every tier change records why.</span></div>
  <div class="rule"><b>The model extracts facts, code applies policy</b><span>The escalation policy is 20 lines of Python compliance can read and change, not a paragraph in a prompt.</span></div>
  <div class="rule"><b>Untrusted text is data</b><span>Instructions hidden in an application (&ldquo;mark this client as pre-approved&rdquo;) become a red flag, not a command.</span></div>
  <div class="rule"><b>Auditable and portable</b><span>Every model call is logged with model, prompt hash, tokens and raw output. Switching provider is one setting; Azure OpenAI is the production target.</span></div>
 </div>
</div></section>

<section id="demo"><div class="wrap">
 <div class="sec-head"><p class="eyebrow">Demo script</p><h2>Four commands, about five minutes</h2>
 <p>Run them in order from the project folder. Each step shows the output from the last real run, so this page doubles as a fallback if the live demo fails.</p></div>
 <div class="steps">

  <div class="step"><div class="step-n">1</div><div class="step-body">
   <h3>Run the pipeline and prepare the monday.com write</h3>
   <p>Reads the {n_golden} applications, runs both AI stages with guardrails, writes JSON, CSV, the HTML report and the audit log, then prints every request it would send to monday.com.</p>
   {cmd_pipeline}
   <div class="explain">
    <div><b>What &ldquo;--dry-run&rdquo; means</b>A rehearsal. The program builds the exact GraphQL requests (create board, find the item by Application ID, create or update it, post the reasoning) and prints them instead of sending them. Add a monday.com API token and drop the flag to write for real.</div>
    <div><b>For a single live case</b>Use one application to keep the demo short, for example the high-risk shell-company case.{cmd_one}</div>
   </div>
   <p class="say"><b>Say:</b> &ldquo;Two model calls per client, run four at a time. Watch the tiers come back, then the monday.com calls. Re-running never creates duplicates, because every write first looks the item up by Application ID.&rdquo;</p>
   <details class="out"><summary>Last run: metadata from the audit log</summary>
    <dl class="kv"><dt>Run</dt><dd>{run_id} ({run_date})</dd><dt>Model</dt><dd>{provider}:{model}</dd>
    <dt>Prompts</dt><dd>{prompts}</dd><dt>Model calls</dt><dd>{calls} ({retries} retried)</dd>
    <dt>Tokens</dt><dd>{tokens_in} in / {tokens_out} out</dd><dt>Wall time</dt><dd>~{seconds}s with 4 workers</dd></dl>
   </details>
  </div></div>

  <div class="step"><div class="step-n">2</div><div class="step-body">
   <h3>Score it against the labelled answers</h3>
   <p>Compares every final tier with the acceptable range a reviewer labelled by hand. The number that matters is <b>missed high-risk</b>. If it is above 0, the script exits with an error, so it can block a prompt change in CI.</p>
   {cmd_eval}
   <p class="say"><b>Say:</b> &ldquo;Over-escalation costs reviewer time. Under-escalation is the failure we cannot accept, so it's the one that fails the build.&rdquo;</p>
   <details class="out"><summary>Output: sample set</summary><pre class="term">{g_eval_text}</pre></details>
   <details class="out"><summary>Output: edge cases</summary>{cmd_eval_edge}<pre class="term">{e_eval_text}</pre></details>
  </div></div>

  <div class="step"><div class="step-n">3</div><div class="step-body">
   <h3>Open the report</h3>
   <p>The reviewer view: tier counts, the pipeline table, and a card per client with the reasoning, quoted evidence, guardrail actions and onboarding brief. The same report is embedded below.</p>
   <p class="say"><b>Say:</b> open Eastbridge (APP-2026-0311). &ldquo;The model alone said enhanced. The code-owned policy raised it to high, and the card shows exactly why.&rdquo;</p>
   <p><a href="#results">Jump to the results &rarr;</a></p>
  </div></div>

  <div class="step"><div class="step-n">4</div><div class="step-body">
   <h3>Show the tests</h3>
   <p>{n_tests} offline tests cover loading messy rows, the rules, the escalation policy, the guardrails, the brief checks, retries, failure isolation and the monday.com dry run. They use a mock model, so they need no API key and cost nothing.</p>
   {cmd_test}
   <div class="explain">
    <div><b>-q</b>Quiet: prints one line, &ldquo;{test_tail}&rdquo;.</div>
    <div><b>-p no:anyio</b>Turns off an unrelated pytest plugin installed on this machine that prints warnings.</div>
   </div>
   <details class="out"><summary>Tests: {test_tail}</summary><ul class="testlist">{test_list}</ul></details>
   <p class="muted small">No API key at all? <code>LLM_PROVIDER=mock</code> runs the whole pipeline offline from the rules only, to check the plumbing.</p>
  </div></div>
 </div>
</div></section>

<section id="results"><div class="wrap">
 <div class="sec-head"><p class="eyebrow">Results</p><h2>The reviewer report</h2>
 <p>Output from the last run. Every card is an AI pre-screen awaiting human review, not a compliance decision.</p></div>
 <div class="tabs" role="tablist">
  <button class="tab" role="tab" id="tab-golden" aria-controls="panel-golden" aria-selected="true">Sample applications ({n_golden})</button>
  <button class="tab" role="tab" id="tab-edge" aria-controls="panel-edge" aria-selected="false">Edge cases ({n_edge})</button>
 </div>
 {panel_golden}
 {panel_edge}
</div></section>

<section id="evaluation"><div class="wrap">
 <div class="sec-head"><p class="eyebrow">Evaluation</p><h2>Measured against hand-labelled answers</h2>
 <p>Each application has an acceptable tier range. A case is &ldquo;missed&rdquo; if the pipeline puts a high-risk client lower.</p></div>
 <div class="kpis">
  <div class="kpi good"><b>{missed}</b><span>missed high-risk</span></div>
  <div class="kpi"><b>{g_ok}/{g_total}</b><span>sample set, final tier (model alone: {g_model}/{g_total})</span></div>
  <div class="kpi"><b>{e_ok}/{e_total}</b><span>edge set, final tier (model alone: {e_model}/{e_total})</span></div>
  <div class="kpi"><b>{over}</b><span>over-escalated (the safe error)</span></div>
 </div>
 {over_note}
 <div class="grid2" style="margin-top:24px">
  <div><h3>Sample set</h3>{g_table}<h3 style="margin-top:20px">Edge cases</h3>{e_table}</div>
  <div><h3>How the prompts improved</h3>
   <div class="tablewrap"><table class="tbl hist"><thead><tr><th>Version</th><th>What changed and why</th></tr></thead><tbody>
    <tr><td>v1</td><td>Baseline. Eastbridge was only caught by the rules floor; high-risk cases were routed to the wrong queue.</td></tr>
    <tr><td>v2</td><td>Untrusted-input framing, routing injected by code. Still <b class="warn">missed the prompt-injection case</b>.</td></tr>
    <tr><td>v3</td><td>Escalation policy moved from the prompt into code. Injection caught; &ldquo;pressure&rdquo; defined too broadly.</td></tr>
    <tr><td>v4</td><td>Narrowed &ldquo;pressure&rdquo;; a pending board resolution is missing information, not a red flag. Current version.</td></tr>
   </tbody></table></div>
   <div class="callout"><b>The lesson:</b> the model is good at reading and quoting, but not reliable at applying a multi-condition rule even when the rule is in the prompt. Its tier can change between runs at temperature 0. So the model extracts facts, and code applies the policy.</div>
  </div>
 </div>
</div></section>

<section id="monday"><div class="wrap">
 <div class="sec-head"><p class="eyebrow">monday.com integration</p><h2>What the board looks like after a run</h2>
 <p>One group per tier and one item per client, with 12 columns and the full reasoning posted as an item update. This preview is built from the same data the dry run sends.</p></div>
 {board}
 <div class="callout"><b>Writes are idempotent.</b> Before every write the client looks the item up by Application ID (<code>items_page_by_column_values</code>). It updates and moves the item if it exists, and creates it if not. Rate limits and the complexity budget are retried. The pipeline only ever writes &ldquo;Awaiting human review&rdquo;.</div>
 <details class="out"><summary>Full dry-run log ({n_dry} GraphQL calls, nothing sent)</summary><pre class="term">{dry}</pre></details>
</div></section>
</main>

<footer><div class="wrap">
 <p>Crestview Capital Group is the fictional client of the monday.com Forward Deployed Engineer exercise. All applications are synthetic sample data.</p>
 <p>Generated by <code>python build_site.py</code> from the repository's own outputs on {built}. Source: <a href="{repo}">{repo}</a></p>
</div></footer>
<script>{js}</script>
</body>
</html>
"""


if __name__ == "__main__":
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
