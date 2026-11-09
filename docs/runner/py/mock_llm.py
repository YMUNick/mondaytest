"""Offline stand-in for the model, used with LLM_PROVIDER=mock.

It only exists to test the pipeline's plumbing (parsing, validation, routing,
output, monday.com writes) without an API key. Its "judgment" is just the rule
hits, so never present mock output as AI results.
"""
import json

from schemas import Application, RuleHit


def mock_risk(app: Application, hits: list[RuleHit], floor: str) -> str:
    category_map = {"integrity": "behaviour"}
    return json.dumps({
        "high_risk_checks": {"severe_flags": [], "source_of_funds_unevidenced": False,
                             "pressure_or_resistance": False},
        "risk_tier": floor,
        "red_flags": [{"flag": h.rule, "category": category_map.get(h.category, h.category),
                       "evidence": h.matched_text} for h in hits],
        "complexity": "high" if app.estimated_aum >= 1e9 else "medium",
        "complexity_drivers": ["mock: based on AUM only"],
        "missing_information": [],
        "other_compliance_considerations": [],
        "recommended_action": "mock: route according to the rule floor",
        "confidence": 0.9,
        "reasoning": "Mock output generated from deterministic rules only.",
    })


def mock_summary(app: Application, tier: str, queue: str) -> str:
    return json.dumps({
        "headline": f"{app.client_name}: {app.requested_services}",
        "client_profile": f"{app.client_type} client.",
        "services_needed": [app.requested_services],
        "complexity_note": "mock",
        "risk_note": f"Pre-screen tier: {tier}.",
        "next_steps": [f"[Compliance] Route to {queue}."],
    })
