"""Deterministic red-flag rules that run BEFORE and INDEPENDENTLY of the model.

Why: compliance needs a floor that does not depend on a model's judgment.
The rules can only raise the tier. The model can raise it further, but it can
never push a case below what the rules found ("AI can escalate, never clears").

These patterns are a starting point for the POC. In production they would be
defined with Crestview's compliance team and sit alongside ComplianceOne
sanctions/PEP screening, which this POC does not call.
"""
import re

from schemas import TIER_ORDER, RuleHit

# (rule name, category, minimum tier, regex)
RULES = [
    ("Offshore jurisdiction or structure", "jurisdiction", "enhanced",
     r"offshore"),
    ("Nominee directors", "ownership", "high",
     r"nominee director"),
    ("Beneficial ownership unclear", "ownership", "high",
     r"beneficial ownership is (difficult|unclear|not)"),
    ("Layered ownership structure", "ownership", "enhanced",
     r"layers of (intermediate )?holding compan"),
    ("Politically exposed person", "pep", "enhanced",
     r"politically exposed|\bPEP\b|former senior government official"),
    ("Source of funds not evidenced", "source_of_funds", "enhanced",
     r"(no supporting (detail|documentation))|(supporting documentation is minimal)"),
    ("Resists due diligence", "behaviour", "enhanced",
     r"pushed back|frustration with documentation|declined a standard introductory call"
     r"|no documentation has been submitted"),
    ("Pressure on timeline", "behaviour", "enhanced",
     r"expedited processing|insists on a compressed"),
    ("Unknown introducer or intermediary", "behaviour", "enhanced",
     r"unaffiliated third-party introducer|routed through their advisor"),
    ("Limited operating history", "ownership", "enhanced",
     r"recently incorporated|limited operating history"),
    ("Incomplete KYC on material parties", "documentation", "enhanced",
     r"kyc documentation is partially complete"),
    # Text that tries to steer the reviewer (or the model) is itself a warning sign.
    ("Instruction aimed at the reviewer", "integrity", "enhanced",
     r"ignore (all |any )?(previous|prior|above) instructions|pre-?approved"
     r"|(classify|mark|rate) (this|the) (client|application|case) as"
     r"|no (further )?(review|due diligence) (is )?(needed|required)"),
]

# Three or more distinct red-flag categories together = high, a common AML heuristic.
MULTI_CATEGORY_HIGH = 3


def policy_tier(risk) -> tuple[str, list[str]]:
    """Crestview's escalation policy, applied in code to the facts the model extracted.

    Prompt v2 told the model this policy in words and it still under-applied it
    (Eastbridge: three red-flag categories plus pressure, rated "enhanced").
    So from v3 the model only extracts facts and this function, which compliance
    can read and own, decides. Returns the tier and the reasons that triggered it.
    """
    reasons = []
    checks = risk.high_risk_checks
    categories = {f.category for f in risk.red_flags if f.category != "other"}
    if checks and checks.severe_flags:
        reasons.append("severe flag: " + ", ".join(checks.severe_flags))
    if len(categories) >= MULTI_CATEGORY_HIGH:
        reasons.append(f"red flags in {len(categories)} categories: {', '.join(sorted(categories))}")
    if checks and checks.source_of_funds_unevidenced and checks.pressure_or_resistance:
        reasons.append("unevidenced source of funds combined with pressure or resistance")
    if reasons:
        return "high", reasons
    if categories:
        return "enhanced", [f"red flags in: {', '.join(sorted(categories))}"]
    return "standard", []


def run_rules(description: str) -> tuple[list[RuleHit], str]:
    """Return the rule hits and the minimum tier they imply."""
    hits = []
    for name, category, min_tier, pattern in RULES:
        match = re.search(pattern, description, flags=re.IGNORECASE)
        if match:
            hits.append(RuleHit(rule=name, category=category, min_tier=min_tier,
                                matched_text=match.group(0)))

    floor = "standard"
    for hit in hits:
        if TIER_ORDER[hit.min_tier] > TIER_ORDER[floor]:
            floor = hit.min_tier
    if len({h.category for h in hits}) >= MULTI_CATEGORY_HIGH:
        floor = "high"
    return hits, floor
