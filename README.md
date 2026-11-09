# Crestview intelligent client intake (POC)

Raw client applications in → explained risk pre-screen → operations brief → structured output and a monday.com board.

**Result on the 15 sample applications (prompt v4, gpt-4.1-mini):** **0 missed high-risk cases in every run**. 14–15/15 within the hand-labelled acceptable tiers: the latest run (20261109T080107Z) scored 15/15, and one earlier run over-escalated James Okafor (APP-2026-0305), the safe direction of error (see [Evaluation](#evaluation)). 20–30 s for the batch with 4 workers, ~3k tokens per application.

**Demo site:** https://ymunick.github.io/mondaytest/ (built from this repo by `python build_site.py`). Its **Try it live** section runs this same `pipeline.process()` in the browser with Pyodide (`browser_runner.py`): paste an OpenAI or Anthropic key, pick sample applications or write your own, and the browser calls the provider directly. No server, and the key is never stored.

## Run it

```bash
pip install -r requirements.txt

# pick ONE provider (or leave LLM_PROVIDER unset: the first key found is used)
export OPENAI_API_KEY=...           # LLM_PROVIDER=openai   (used for the results above)
# export ANTHROPIC_API_KEY=...      # LLM_PROVIDER=anthropic
# export GEMINI_API_KEY=...         # LLM_PROVIDER=gemini   (free tier)
# export AZURE_OPENAI_API_KEY=... AZURE_OPENAI_ENDPOINT=... LLM_MODEL=<deployment>   # LLM_PROVIDER=azure (Crestview production)

python pipeline.py                                   # all 15 applications -> output/
python pipeline.py --ids APP-2026-0303               # one case, for the live demo
python pipeline.py --prompt-version v1               # the original prompts, for before/after
python pipeline.py --input data/edge_cases.csv --out output_edge   # messy / adversarial rows

python evaluate.py                                   # golden set; exit 1 if a high-risk case is missed
python evaluate.py --results output_edge/results.json --expected data/expected_edge_tiers.csv
python consistency.py --runs 3                       # run-to-run stability of the risk stage
python -m pytest -q                                  # 27 offline tests, no API key needed
python build_site.py                                 # docs/index.html: one-page demo site (GitHub Pages), no model calls

# monday.com
python pipeline.py --monday --dry-run                # prints every GraphQL call, sends nothing
export MONDAY_API_TOKEN=...
python monday_client.py link 5032370472             # once: use an existing board (maps its columns by title)
python monday_client.py setup                        # or once: a new board, 3 tier groups, 13 columns
python pipeline.py --monday                          # idempotent upsert by Application ID, then opens the board
```

`LLM_PROVIDER=mock` runs everything offline to test the plumbing. Mock output comes from the rules only; it is not AI output.

Outputs in `output/`: `results.json` (full records), `results.csv` (flat, one row per client), `report.html` (reviewer view), `audit_log.jsonl` (every model call).

## Architecture

```
CSV row ─► Load & validate ─► Rules (regex) ──────────────┐ floor
                │                                          ▼
                └──────────► LLM #1 risk pre-screen ─► Guardrails ─► final tier ─► routing queue (code)
                             (facts checklist, flags        │  max(rules, policy(facts), model)
                              with verbatim evidence)       │  low confidence → +1 tier
                                                            │  evidence quotes verified vs source
                                                            ▼
                             LLM #2 onboarding brief ◄── final tier + queue + flags
                                                            │
                                         Policy checks on the brief (code) ─► JSON / CSV / HTML / monday.com
```

| Stage | File | What it does |
| --- | --- | --- |
| Load | `pipeline.py`, `schemas.py` | Validates each row; normalises `$1,200,000` / `35M` / ISO dates; skips and reports bad rows and duplicates |
| Rules | `rules.py` | Deterministic red-flag patterns set a **minimum** tier, independent of the model |
| Risk | `prompts/risk_assessment_v4.md` | Model fills a fact checklist, then returns tier, red flags with verbatim evidence, complexity, missing info, non-AML compliance items, confidence |
| Policy | `rules.py: policy_tier` | Crestview's escalation policy applied **in code** to the model's facts (severe flag, ≥3 categories, unevidenced funds + pressure → high) |
| Guardrails | `pipeline.py` | Final tier = max(rules, policy, model); confidence < 0.7 goes up a tier; each evidence quote is checked against the source |
| Routing | `schemas.py: ROUTING` | Queue chosen by code from the final tier, never by the model |
| Summary | `prompts/onboarding_summary_v4.md` | Model writes the ops brief **from the final risk result and queue**; owner-tagged next steps |
| Checks | `pipeline.py: check_summary` | First step must route to compliance, tier must be stated, "approved/cleared" language is flagged |
| Output | `pipeline.py`, `report.py` | JSON, CSV, HTML report, JSONL audit log (model, prompt file hash, tokens, latency, raw output) |
| Board | `monday_client.py` | Group per tier, item per client, upsert by Application ID, reasoning as an item update |
| Eval | `evaluate.py`, `consistency.py`, `tests/` | Golden set, edge-case set, stability across runs, 27 unit tests |

### Design rules (and which stakeholder they answer)

- **AI can escalate, never clear** (Priya). Rules and the code-owned policy set floors the model cannot go below. Every record is `needs_human_review = true`; the pipeline writes "Awaiting human review" and only a person can change it.
- **Explainable** (Priya). Every red flag carries a verbatim quote that is machine-checked against the application; every tier change records why (`tier_adjustments`).
- **LLM extracts facts, code applies policy** (Priya, Marcus). The escalation policy is 20 lines of Python that compliance can read and change, not a paragraph inside a prompt.
- **Risk and complexity are separate.** A sovereign fund can be complex and low risk; a shell company can be simple and high risk.
- **Handles messy input** (David). Bad rows are reported, not fatal; one failed model call never stops the batch; invalid JSON gets one retry with the validation error.
- **Untrusted text is data** (Marcus). The application sits inside `<application>` tags; instructions inside it are flagged as a red flag (rule + model), not obeyed.
- **Portable** (Marcus). One provider switch; production target is Azure OpenAI inside Crestview's M365 tenant.

## Evaluation

| Prompt | Golden set (15) | Model alone | Edge set (3) | Notes |
| --- | --- | --- | --- | --- |
| v1 | 15/15 | 14/15 | not run | Eastbridge saved only by rules floor; high-risk cases routed to the wrong queue; 10b5-1 issue not surfaced |
| v2 | 15/15 | 14/15 | 2/3, **1 missed high** | Prompt-injection case stayed "enhanced" |
| v3 | 14/15 (1 over) | 13/15 | 3/3 | Policy moved to code; checklist definition of "pressure" too broad (Brightpath) |
| v4 | **14–15/15** | 14–15/15 | **3/3** | 0 missed high in every run. Final tier matched in 18/18 cases across 3 consistency runs, but a later full run over-escalated APP-2026-0305 (below) |

**Known variance (v4).** On run 20261109T065112Z the model tagged James Okafor's red flags in three categories (ownership, jurisdiction, source of funds) instead of two, so the code policy (≥3 categories → high) raised a case labelled `standard|enhanced` to high. The guardrails make the final tier far more stable than the model's own tier, but not perfectly stable, because the policy still depends on which facts the model extracts. Next tuning step, for compliance to decide: whether flags that describe complexity (international residency, layered but documented ownership) should count toward the 3-category rule. That needs a larger labelled set before changing it.

Edge cases (`data/edge_cases.csv`): a prompt-injection attempt, a Spanish-language PEP case the regex rules cannot read, an unparseable AUM, an empty description, and a clean case with messy formatting.

## Production hardening at Crestview (not in this POC)

- **Data boundary:** Azure OpenAI in Crestview's tenant (no training on data, regional residency, private endpoint); PII minimisation before the call where possible.
- **Documents:** Azure AI Document Intelligence / OCR for PDFs and scans feeding the same extraction schema; the POC starts from the application text.
- **Real screening:** ComplianceOne API for sanctions/PEP/adverse media; the rules here only read the narrative.
- **Larger golden set:** 200+ historical cases labelled by Priya's team; evaluation as a CI gate on every prompt change; confidence calibrated against outcomes.
- **Operations:** secrets in Key Vault, queue-based processing (Service Bus / Azure Functions), dead-letter queue, monitoring of tier distribution drift, prompt versions in source control with approval by compliance.
- **monday.com:** webhook/automation triggers on new items instead of a batch CSV; SharePoint links on each item; Salesforce sync of status.
