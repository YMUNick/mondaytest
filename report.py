"""Render pipeline results as one self-contained HTML page for reviewers.

Called by pipeline.py after every run (output/report.html). Can also be run on
its own:  python report.py output/results.json
"""
import json
import sys
from collections import Counter
from html import escape
from pathlib import Path

from schemas import ProcessedApplication

CSS = """
:root{--bg:#f7f7f9;--card:#fff;--ink:#1d1f27;--muted:#5d6273;--line:#e3e5ec;
--std:#1f7a4d;--std-bg:#e3f4ea;--enh:#8a5a00;--enh-bg:#fff1d6;--high:#b42318;--high-bg:#fde7e5;
--accent:#5034ff}
@media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1d1f27;--ink:#eceef4;--muted:#a3a8b8;
--line:#2e313c;--std:#6fd59d;--std-bg:#173325;--enh:#f3c260;--enh-bg:#3a2d10;--high:#ff8a80;
--high-bg:#3d1714;--accent:#9d8cff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
.muted{color:var(--muted)}.kpis{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:120px}
.kpi b{display:block;font-size:22px}
.tbl{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.tbl th,.tbl td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.tbl th{font-size:12px;color:var(--muted);font-weight:600}
.tbl td:first-child,.tbl td:nth-child(4){white-space:nowrap}
.wrap{overflow-x:auto}
.chip{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;font-weight:600;white-space:nowrap}
.standard{color:var(--std);background:var(--std-bg)}.enhanced{color:var(--enh);background:var(--enh-bg)}
.high{color:var(--high);background:var(--high-bg)}.failed{color:var(--muted);background:var(--line)}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:10px 0;padding:0 14px}
summary{cursor:pointer;padding:12px 0;font-weight:600;list-style-position:outside}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding-bottom:14px}
@media (max-width:760px){.grid{grid-template-columns:1fr}}
ul{margin:4px 0;padding-left:18px}li{margin:2px 0}
.ok{color:var(--std)}.warn{color:var(--high)}.note{border-left:3px solid var(--accent);padding-left:10px}
code{font-size:12px}
"""


def chip(tier):
    tier = tier or "failed"
    return f'<span class="chip {tier}">{escape(tier)}</span>'


def card(r: ProcessedApplication) -> str:
    if r.status == "failed":
        return (f"<details><summary>{escape(r.application_id)} · {escape(r.client_name)} "
                f"{chip(None)}</summary><p class='warn'>{escape(r.error or '')}</p></details>")
    ra, s = r.risk_assessment, r.summary
    flags = "".join(
        f"<li><b>{escape(f.flag)}</b> <span class='muted'>({escape(f.category)})</span><br>"
        f"“{escape(f.evidence)}” "
        f"{'<span class=ok>✓ found in application</span>' if f.evidence_verified else '<span class=warn>✗ not found verbatim</span>'}</li>"
        for f in ra.red_flags) or "<li class='muted'>None identified</li>"
    rules = "".join(f"<li>{escape(h.rule)} → min {chip(h.min_tier)} <code>{escape(h.matched_text)}</code></li>"
                    for h in r.rule_hits) or "<li class='muted'>No rule matched</li>"
    lst = lambda items: "".join(f"<li>{escape(i)}</li>" for i in items) or "<li class='muted'>None</li>"
    guards = lst(r.tier_adjustments + r.policy_checks)
    return f"""
<details><summary>{escape(r.application_id)} · {escape(r.client_name)} &nbsp;{chip(r.final_risk_tier)}
<span class="muted"> · {escape(r.routing_queue or '')}</span></summary>
<p class="note"><b>{escape(s.headline)}</b><br>{escape(s.client_profile)}</p>
<div class="grid">
 <div>
  <h3>Risk pre-screen</h3>
  <p>Final {chip(r.final_risk_tier)} &nbsp; model {chip(r.model_risk_tier)} &nbsp;
     rules floor {chip(r.rule_floor_tier)} &nbsp; confidence {ra.confidence:.2f}</p>
  <p>{escape(ra.reasoning)}</p>
  <b>Red flags (model, with evidence)</b><ul>{flags}</ul>
  <b>Deterministic rule hits</b><ul>{rules}</ul>
  <b>Guardrail actions</b><ul>{guards}</ul>
 </div>
 <div>
  <h3>Onboarding brief</h3>
  <p><b>Complexity:</b> {escape(ra.complexity)} — {escape(s.complexity_note)}</p>
  <p><b>Risk:</b> {escape(s.risk_note)}</p>
  <b>Next steps</b><ol>{''.join(f'<li>{escape(x)}</li>' for x in s.next_steps)}</ol>
  <b>Missing information</b><ul>{lst(ra.missing_information)}</ul>
  <b>Other compliance considerations</b><ul>{lst(ra.other_compliance_considerations)}</ul>
  <p class="muted">Model {escape(r.model or '')} · prompts {escape(', '.join(r.prompt_versions.values()))}<br>
  AI pre-screen. Needs human review. Not a compliance decision.</p>
 </div>
</div></details>"""


def write_report(results, path: Path, run_id: str = "", load_errors=None):
    results = [r if isinstance(r, ProcessedApplication) else ProcessedApplication(**r)
               for r in results]
    tiers = Counter(r.final_risk_tier or "failed" for r in results)
    raised = sum(1 for r in results if r.status == "processed"
                 and r.final_risk_tier != r.model_risk_tier)
    rows = "".join(
        f"<tr><td>{escape(r.application_id)}</td><td>{escape(r.client_name)}</td>"
        f"<td>{escape(r.client_type)}</td><td>${r.estimated_aum/1e6:,.1f}M</td>"
        f"<td>{chip(r.final_risk_tier)}</td><td>{chip(r.model_risk_tier) if r.model_risk_tier else ''}</td>"
        f"<td>{escape(r.risk_assessment.complexity) if r.risk_assessment else ''}</td>"
        f"<td>{escape(r.routing_queue or r.error or '')}</td></tr>"
        for r in results)
    skipped = "".join(f"<li>{escape(e)}</li>" for e in (load_errors or []))
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crestview Intake Pre-screen</title><style>{CSS}</style></head><body><main>
<h1>Crestview client intake: AI pre-screen</h1>
<p class="muted">Run {escape(run_id)} · {len(results)} applications · every record needs human review</p>
<div class="kpis">
 <div class="kpi"><b>{tiers.get('high', 0)}</b>high (escalation)</div>
 <div class="kpi"><b>{tiers.get('enhanced', 0)}</b>enhanced due diligence</div>
 <div class="kpi"><b>{tiers.get('standard', 0)}</b>standard review</div>
 <div class="kpi"><b>{raised}</b>raised by guardrails</div>
 <div class="kpi"><b>{tiers.get('failed', 0)}</b>failed</div>
</div>
{f'<h2>Rows skipped at load</h2><ul>{skipped}</ul>' if skipped else ''}
<h2>Pipeline</h2>
<div class="wrap"><table class="tbl"><thead><tr><th>ID</th><th>Client</th><th>Type</th><th>AUM</th>
<th>Final tier</th><th>Model tier</th><th>Complexity</th><th>Queue</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Details</h2>
{''.join(card(r) for r in results)}
</main></body></html>"""
    path.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "output/results.json")
    data = json.loads(src.read_text(encoding="utf-8"))
    write_report(data, src.with_name("report.html"))
    print(f"Wrote {src.with_name('report.html')}")
