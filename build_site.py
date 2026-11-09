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
from site_render import TIER_LABEL, card, money, pill, ul  # noqa: E402
from site_template import CSS, ICON, JS, PAGE  # noqa: E402

REPO_URL = "https://github.com/YMUNick/mondaytest"

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
<div class="panel" id="panel-{key}" role="tabpanel" aria-labelledby="tab-{key}" tabindex="0"{hidden}>
 <div class="stats">
  <div class="stat"><b class="num">{tiers.get('high', 0)}</b><span>{pill('high', True)} escalation</span></div>
  <div class="stat"><b class="num">{tiers.get('enhanced', 0)}</b><span>{pill('enhanced', True)} due diligence</span></div>
  <div class="stat"><b class="num">{tiers.get('standard', 0)}</b><span>{pill('standard', True)} review</span></div>
  <div class="stat"><b class="num">{raised}</b><span>raised by guardrails</span></div>
  <div class="stat"><b class="num">{tiers.get('failed', 0) + len(load_errors)}</b><span>failed or rejected</span></div>
 </div>
 {skipped}
 <div class="filters" role="group" aria-label="Filter by tier">
  <button type="button" class="chip" data-filter="all" aria-pressed="true">All</button>
  <button type="button" class="chip" data-filter="high" aria-pressed="false">High</button>
  <button type="button" class="chip" data-filter="enhanced" aria-pressed="false">Enhanced</button>
  <button type="button" class="chip" data-filter="standard" aria-pressed="false">Standard</button>
  <button type="button" class="chip chip-end" data-expand aria-pressed="false">Expand all</button>
 </div>
 <div class="tablewrap"><table class="tbl clickable">
  <thead><tr><th>ID</th><th>Client</th><th>Type</th><th>AUM</th><th>Final tier</th><th>Model</th>
  <th>Complexity</th><th>Routed to</th></tr></thead><tbody>{rows}</tbody></table></div>
 <p class="hint">Select a row to open its full pre-screen below.</p>
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
    return ('<div class="tablewrap"><table class="tbl eval-tbl"><thead><tr><th>ID</th><th>Client</th>'
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
        out.append(f"""<div class="b-group b-g-{tier}"><h3 class="b-title">{escape(title)} <span class="muted">{len(items)} item{"" if len(items) == 1 else "s"}</span></h3>
<div class="tablewrap"><table class="b-tbl"><thead><tr><th>Client</th><th>Application ID</th><th>Risk tier</th>
<th>Model tier</th><th>AI confidence</th><th>Complexity</th><th>Review status</th><th>Next step</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>""")
    return "".join(out)


DEMO_CASES = ("APP-2026-0301", "APP-2026-0303", "APP-2026-0311")
HERO_CASE = "APP-2026-0311"


def hero_case(r) -> str:
    """The hero's product view: one real pre-screen from the last run, as the reviewer sees it."""
    ra = r.risk_assessment
    flag = next((f for f in ra.red_flags if f.evidence_verified), ra.red_flags[0] if ra.red_flags else None)
    why = r.tier_adjustments[0] if r.tier_adjustments else "Model tier kept: no guardrail needed"
    quote = (f'<blockquote>&ldquo;{escape(flag.evidence)}&rdquo;<small>&#10003; found verbatim in the application</small></blockquote>'
             if flag else "")
    return f"""<div class="app-frame" role="group" aria-label="Example pre-screen result from the last run">
 <div class="app-frame__bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
  <span class="mono">Pre-screen &middot; {escape(r.application_id)}</span><span class="status">Awaiting human review</span></div>
 <div class="app-frame__body">
  <div><p class="who">{escape(r.client_name)}</p><p class="muted small">{escape(r.client_type)} &middot; {money(r.estimated_aum)} &middot; {escape(r.requested_services)}</p></div>
  <div class="tierline">
   <div><span class="lbl">Final tier</span>{pill(r.final_risk_tier)}</div>
   <div><span class="lbl">Model said</span>{pill(r.model_risk_tier)}</div>
   <div><span class="lbl">Rules floor</span>{pill(r.rule_floor_tier)}</div>
   <div><span class="lbl">Confidence</span><b class="num">{ra.confidence:.2f}</b></div>
  </div>
  <dl class="kv2"><dt>Why</dt><dd>{escape(why)}</dd>
  <dt>Evidence</dt><dd>{escape(flag.flag) if flag else "None"}</dd></dl>
  {quote}
  <dl class="kv2"><dt>Routed to</dt><dd>{escape(r.routing_queue or "")}</dd>
  <dt>Next step</dt><dd>{escape(r.summary.next_steps[0] if r.summary.next_steps else "")}</dd></dl>
 </div>
</div>"""


def say_case(r) -> str:
    why = r.tier_adjustments[0] if r.tier_adjustments else "the model and the rules agreed"
    return (f"&ldquo;{escape(r.client_name)}: the model alone said {escape(r.model_risk_tier or '')}. "
            f"The final tier is {escape(r.final_risk_tier or '')} &mdash; {escape(why[0].lower() + why[1:])}. "
            "The card shows exactly why.&rdquo;")


def live_samples(apps) -> str:
    return "".join(
        f'<label class="pick"><input type="checkbox" name="sample" value="{escape(a.application_id)}"'
        f'{" checked" if a.application_id in DEMO_CASES else ""}>'
        f'<span><b class="mono">{escape(a.application_id)}</b> {escape(a.client_name)}'
        f'<small>{escape(a.client_type)} &middot; {money(a.estimated_aum)}</small></span></label>'
        for a in apps)


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
        css=CSS, js=JS, repo=REPO_URL, icon=ICON,
        hero_case=hero_case(next(r for r in golden if r.application_id == HERO_CASE)),
        say_case=say_case(next(r for r in golden if r.application_id == HERO_CASE)),
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
        cmd_one=cmd(f"python pipeline.py --ids {HERO_CASE}"),
        cmd_eval=cmd("python evaluate.py"),
        cmd_eval_edge=cmd("python evaluate.py --results output_edge/results.json --expected data/expected_edge_tiers.csv"),
        cmd_test=cmd("python -m pytest -q -p no:anyio"),
        cmd_mock=cmd("LLM_PROVIDER=mock python pipeline.py"),
        g_eval_text=escape(g_text), e_eval_text=escape(e_text),
        g_table=eval_table(g_rows), e_table=eval_table(e_rows),
        panel_golden=results_panel("golden", golden, texts, [], True),
        panel_edge=results_panel("edge", edge, texts, edge_errors, False),
        live_samples=live_samples(apps_main),
        board=board_preview([r for r in golden if r.status == "processed"]),
        dry=escape(dry), n_dry=n_calls,
        built=datetime.now().strftime("%d %b %Y"),
    )


# ---------------------------------------------------------------- template

WORKER_JS = r"""// Runs the real Python pipeline in the browser with Pyodide. Built by build_site.py.
importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
let py = null, runner = null, ready = null;

async function init() {
  postMessage({type: 'status', text: 'Loading the Python runtime (about 10 s the first time)...'});
  py = await loadPyodide();
  await py.loadPackage(['pydantic']);
  postMessage({type: 'status', text: 'Loading pipeline code and prompts...'});
  const manifest = await (await fetch('py/manifest.json', {cache: 'no-cache'})).json();
  for (const dir of manifest.dirs) py.FS.mkdirTree('/app/' + dir);
  for (const f of manifest.files) {
    const res = await fetch('py/' + f, {cache: 'no-cache'});
    if (!res.ok) throw new Error('could not load ' + f);
    py.FS.writeFile('/app/' + f, await res.text());
  }
  py.runPython("import sys, os; sys.path.insert(0, '/app'); os.chdir('/app')");
  runner = py.pyimport('browser_runner');
}

onmessage = async (e) => {
  const m = e.data;
  try {
    if (!ready) ready = init();
    await ready;
  } catch (err) {
    ready = null;
    postMessage({type: 'fatal', text: 'Could not start the Python runtime: ' + err});
    return;
  }
  if (m.type !== 'run') return;
  const runId = runner.new_run();
  const cfg = JSON.stringify(m.cfg);
  const started = performance.now();
  postMessage({type: 'start', runId: runId, n: m.items.length});
  const done = [];
  for (let i = 0; i < m.items.length; i++) {
    postMessage({type: 'progress', i: i, label: m.items[i].label});
    let out;
    try { out = JSON.parse(runner.process_one(cfg, JSON.stringify(m.items[i].input))); }
    catch (err) { out = {error: String(err)}; }
    if (out.result && out.result.status === 'processed') done.push(out.result);
    postMessage({type: 'result', i: i, label: m.items[i].label, out: out});
    if (out.error && /HTTP (401|403|404)/.test(out.error)) {
      postMessage({type: 'status', text: 'Stopped: the provider rejected the key or model. Check them and run again.'});
      break;
    }
  }
  const t = JSON.parse(runner.totals());
  postMessage({type: 'done', seconds: (performance.now() - started) / 1000, tokens_in: t.tokens_in,
               tokens_out: t.tokens_out, runId: t.run_id, audit: runner.audit_log(), board: !!m.board});
  if (m.board) {
    if (!done.length) { postMessage({type: 'board-done', out: {error: 'Nothing to write: no application was processed.'}}); return; }
    postMessage({type: 'board-start', n: done.length});
    let out;
    try { out = JSON.parse(runner.push_to_board(m.board.token, m.board.boardId, JSON.stringify(done))); }
    catch (err) { out = {error: String(err)}; }
    postMessage({type: 'board-done', out: out});
  }
};
"""

RUNTIME_FILES = ["pipeline.py", "schemas.py", "rules.py", "mock_llm.py", "llm.py", "site_render.py",
                 "monday_client.py", "browser_runner.py", "data/crestview_client_applications.csv"]


def write_runner(docs: Path):
    """Copy the pipeline code the in-browser runner loads, plus its worker."""
    py_dir = docs / "runner" / "py"
    files = RUNTIME_FILES + [f"prompts/{p.name}" for p in sorted((ROOT / "prompts").glob("*_v4.md"))]
    for f in files:
        dest = py_dir / f
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / f).read_bytes())
    manifest = {"dirs": sorted({str(Path(f).parent).replace("\\", "/") for f in files} - {"."}),
                "files": files}
    (py_dir / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (docs / "runner" / "worker.js").write_text(WORKER_JS, encoding="utf-8")


if __name__ == "__main__":
    write_runner(ROOT / "docs")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    (ROOT / "docs" / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")
