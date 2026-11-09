"""HTML pieces shared by the static demo site and the in-browser runner.

Kept free of heavy imports so it also runs inside Pyodide (Python in the browser).
"""
from html import escape

from schemas import ProcessedApplication

TIER_LABEL = {"standard": "Standard", "enhanced": "Enhanced", "high": "High"}


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
   <h3 class="k">Why this tier</h3>
   <p>{escape(ra.reasoning)}</p>
   <h3 class="k">Red flags, with evidence</h3>{flags}
   <h3 class="k">Deterministic rule hits</h3>{rules}
   <h3 class="k">Guardrail actions</h3>{ul(r.tier_adjustments + r.policy_checks, "None needed")}
  </div>
  <div>
   <h3 class="k">Onboarding brief</h3>
   <p><b>Risk:</b> {escape(s.risk_note)}</p>
   <p><b>Complexity:</b> {escape(s.complexity_note)}</p>
   <h3 class="k">Next steps</h3><ol>{steps}</ol>
   <h3 class="k">Missing information</h3>{ul(ra.missing_information)}
   <h3 class="k">Other compliance considerations</h3>{ul(ra.other_compliance_considerations)}
  </div>
 </div>
 <details class="source"><summary>Original application text{' (verified quotes highlighted)' if quotes else ''}</summary>
  <p>{highlight(app_text, quotes)}</p></details>
 <p class="fine">{escape(r.model or '')} &middot; {escape(', '.join(r.prompt_versions.values()))} &middot;
 AI pre-screen, awaiting human review. Not a compliance decision.</p>
</div></details>"""
