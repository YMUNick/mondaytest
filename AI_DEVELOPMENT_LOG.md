# AI-assisted development log

How AI tools were used to build this POC, what the prompt iterations were, how output quality was judged, and where human judgment had to step in.

## Tools used

| Stage | Tool | What for |
| --- | --- | --- |
| Scenario synthesis | Claude (chat) | Turned the account brief, transcript and metrics into a stakeholder → concern → design-requirement map |
| Architecture | Claude (chat), then Claude Code | First skeleton (rules floor, two-stage pipeline, schemas, audit log); then hardening in the repo |
| Code | Claude Code (agentic, in the repo) | Wrote and refactored modules, ran the pipeline against the real model, read the outputs, wrote tests |
| Prompts | Claude Code + gpt-4.1-mini as the system under test | Iterated v1 → v4 driven by `evaluate.py` and by reading full outputs |
| Evaluation | Hand-labelled golden set + scripts | `expected_tiers.csv` labelled before any model run; edge cases written to attack known weaknesses |
| Slides | Claude | Proposal deck drafted from the stakeholder map and the real POC numbers |

## Prompt iterations

### Risk assessment

| Version | Change | Why (what went wrong before) | Effect |
| --- | --- | --- | --- |
| v1 | Tiers, verbatim evidence, risk vs complexity separated, "don't trust 'straightforward'" | Initial | 15/15 final, but model alone rated Eastbridge (0311) "enhanced"; only the rules floor caught it. 10b5-1/trading-window issue for Mercer-Hastings never surfaced. 0314 summary asked for "missing ownership / source-of-funds documents" the application never said were missing. Confidence 0.90–0.95 on every case. |
| v2 | Application wrapped in `<application>` tags, treated as untrusted data; explicit "high" combinations; `missing_information` only for things the text says are missing; new `other_compliance_considerations` field; confidence rubric; "why not one tier higher" | v1 findings above, plus a prompt-injection test I wanted to pass | 10b5-1 now surfaced; hallucinated missing documents gone. **But** model still rated Eastbridge "enhanced" while writing "fewer than three categories" next to three listed categories. Edge set: injection case stayed "enhanced": **1 missed high-risk**. |
| v3 | Model fills a fact checklist (`severe_flags`, `source_of_funds_unevidenced`, `pressure_or_resistance`) **before** the tier; escalation policy moved into code (`rules.policy_tier`) | v2 showed the model extracts the facts correctly but applies a multi-condition policy unreliably, even when the policy is written out. Rewording would not fix that, so the policy moved into code. | Edge set 3/3. **But** Brightpath (0306) over-escalated: "begin onboarding in parallel… Q2 funding deadline" was read as pressure. |
| v4 | Narrowed "pressure" (a business deadline or phased timeline from a client providing documents is not pressure); pending board resolution named as `missing_information`, not a red flag | v3 checklist definition was too broad | 15/15 golden and 3/3 edge on the first runs; final tier matched in 18/18 across 3 consistency runs. A later full run: 14/15 (James Okafor over-escalated, see below). 0 missed high-risk in every run. |

### Onboarding summary

| Version | Change | Why | Effect |
| --- | --- | --- | --- |
| v1 | Final tier is authoritative, never "approved", name missing documents, model picks `owner` | Initial | High-risk cases routed to "Compliance - enhanced due diligence" instead of escalation; standard cases routed to "Operations" (skipping KYC). Generic steps ("Proceed with standard due diligence"). |
| v2 | Queue decided in code and injected; first step must hand to that queue; owner tags `[Compliance]/[RM]/[Operations]`; what may run in parallel per tier | Routing is a policy decision, not a writing task | Routing correct by construction; steps concrete (e.g. ESG exclusion coding for Brightpath). Some noise: "prepare account structure only after clearance" for high-risk cases; operations "collecting" documents from clients. |
| v3/v4 | No deferred set-up steps for enhanced/high; anything requested from the client goes through `[RM]` | Noise above | Cleaner briefs; post-generation policy checks (`check_summary`) needed 0 corrections on v4 output |

## How I evaluated output quality

- **Golden set first.** `data/expected_tiers.csv` was labelled by hand, with *acceptable ranges* (e.g. `standard|enhanced`) where reasonable compliance officers could differ, before running any model.
- **The metric that matters most is missed high-risk cases (must be 0).** Over-escalation costs reviewer time; under-escalation is a regulatory finding. `evaluate.py` exits 1 on any miss, so it can gate CI.
- **Model-alone vs final accuracy** is reported separately, to show how much the guardrails carry.
- **Adversarial edge set** written to attack specific weaknesses: prompt injection, non-English text (regex rules blind), unparseable values, empty fields, messy formatting on a clean case (over-flagging check).
- **Read the full outputs, not just the tier.** The worst v1 problems (wrong routing, missing 10b5-1, invented missing documents) did not show up in the tier metric at all.
- **Run-to-run consistency** (`consistency.py --runs 3`): at temperature 0 the model tier was still unstable. Eastbridge got "high" in one pipeline run and "enhanced" in all three consistency runs, and EDGE-001 flipped between runs. The final tier after guardrails was identical in 18/18. Do not quote a single run's model-alone score.
- **A later full run broke the "stable" claim.** Run `20261109T065112Z` rated James Okafor (APP-2026-0305, labelled `standard|enhanced`) as high: the model listed flags in three categories (ownership, jurisdiction, source of funds) where earlier runs listed two, and the ≥3-category policy fired. It is an over-escalation, the safe error, and missed high-risk stayed 0. But it shows the guardrails reduce variance rather than remove it, because the code policy runs on facts the model extracts. Open item for compliance: whether complexity-type flags (international residency, documented layered ownership) should count toward the 3-category rule. I recorded this instead of re-running until the number looked better.
- **Evidence verification:** every quoted evidence string is checked against the source; 0 unverified quotes across all v2–v4 runs.

## Where AI was most / least effective

- **Most effective:** scaffolding (schemas, retries, audit log, CLI, HTML report, tests) in minutes; reading 15 full JSON outputs and grouping failure patterns; writing adversarial test cases once told what to attack.
- **Least effective:** the model under test applying a multi-condition rule ("3+ categories OR unevidenced funds + pressure"): it wrote the condition back in its own reasoning and still got the tier wrong. Self-reported confidence was uninformative (0.85–0.95 almost everywhere), so it should not be the main safety mechanism.
- **Where I intervened:**
  - Decided that routing and the escalation policy belong in code, not in the prompt. An AI assistant's default was to keep adding prompt wording.
  - Wrote the golden labels myself and kept them fixed while iterating, so the prompts could not be tuned to whatever the model produced.
  - Recognised the v3→v4 change as tuning on a 15-case set: it is a definition compliance should own, and it needs validation on a larger labelled set before production.
  - Caught the false "model alone 15/15" from a single run, using the consistency check.

## Before/after example to show live

**Eastbridge Trading Group (APP-2026-0311):** an 8-month-old company, source of funds "trading profits" with no statements, client pushing for speed.

Before (v2, model): *"The pressure to speed up onboarding adds a behavioural red flag but does not reach the threshold for high risk. There are fewer than three categories of red flags…"*, with ownership, source_of_funds and behaviour all listed. That is three categories.

After (v4): the model's checklist says `source_of_funds_unevidenced: true, pressure_or_resistance: true`; `policy_tier` returns **high** with the reason *"unevidenced source of funds combined with pressure or resistance"*, recorded in `tier_adjustments` and shown on the monday.com item. Same result in every run.

**Demo command:** `python pipeline.py --ids APP-2026-0311 --prompt-version v2` then `python pipeline.py --ids APP-2026-0311`.
