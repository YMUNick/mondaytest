"""Data contracts for every stage of the pipeline.

The LLM's JSON is validated against these models. If it does not match, the
pipeline retries once with the validation error, then marks the record as failed
instead of passing bad data downstream.
"""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

RiskTier = Literal["standard", "enhanced", "high"]
TIER_ORDER = {"standard": 0, "enhanced": 1, "high": 2}
TIERS = ["standard", "enhanced", "high"]

# Who acts next is decided by code from the final tier, never by the model.
ROUTING = {
    "standard": "Compliance - standard review",
    "enhanced": "Compliance - enhanced due diligence",
    "high": "Compliance - escalation",
}


class Application(BaseModel):
    """One raw row from the intake CSV. Tolerates common formatting mess."""
    application_id: str = Field(min_length=3)
    client_name: str = Field(min_length=1)
    client_type: str
    requested_services: str
    estimated_aum: float = Field(gt=0)
    submission_date: str
    status: str
    description: str = Field(min_length=20)

    @field_validator("application_id", "client_name", "client_type",
                     "requested_services", "status", "description", mode="before")
    @classmethod
    def strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("estimated_aum", mode="before")
    @classmethod
    def parse_aum(cls, v):
        """Accept 750000000, "$750,000,000", "750M", "1.2B"."""
        if isinstance(v, (int, float)):
            return v
        text = str(v).strip().upper().replace("$", "").replace(",", "").replace("USD", "").strip()
        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMB]?)", text)
        if not match:
            raise ValueError(f"estimated_aum is not a number: {v!r}")
        mult = {"": 1, "K": 1e3, "M": 1e6, "B": 1e9}[match.group(2)]
        return float(match.group(1)) * mult

    @field_validator("submission_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        """Normalise MM/DD/YYYY or YYYY-MM-DD to ISO YYYY-MM-DD."""
        text = str(v).strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                pass
        raise ValueError(f"submission_date not MM/DD/YYYY or YYYY-MM-DD: {v!r}")


class RedFlag(BaseModel):
    flag: str
    category: Literal["ownership", "source_of_funds", "pep", "jurisdiction",
                      "behaviour", "documentation", "other"]
    evidence: str
    evidence_verified: bool | None = None  # set by the pipeline, not the model


SevereFlag = Literal["nominee_directors", "beneficial_owner_unknown", "refuses_documents",
                     "blocks_direct_contact", "steering_attempt"]


class HighRiskChecks(BaseModel):
    """v3: facts the model extracts; the escalation policy is applied in code (rules.py)."""
    severe_flags: list[SevereFlag] = []
    source_of_funds_unevidenced: bool = False
    pressure_or_resistance: bool = False


class RiskAssessment(BaseModel):
    high_risk_checks: HighRiskChecks | None = None  # v3+; absent in v1/v2 output
    risk_tier: RiskTier
    red_flags: list[RedFlag]
    complexity: Literal["low", "medium", "high"]
    complexity_drivers: list[str]
    missing_information: list[str]
    # v2: regulatory items that are not AML risk but compliance must see
    # (insider-trading windows, ESG mandates, reciprocal due diligence...).
    other_compliance_considerations: list[str] = []
    recommended_action: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class OnboardingSummary(BaseModel):
    headline: str
    client_profile: str
    services_needed: list[str]
    complexity_note: str
    risk_note: str
    next_steps: list[str] = Field(min_length=1)
    # v1 asked the model for an owner; v2 sets it in code. Kept for comparison.
    owner: str | None = None


class RuleHit(BaseModel):
    rule: str
    category: str
    min_tier: RiskTier
    matched_text: str


class ProcessedApplication(BaseModel):
    """One row of pipeline output: what goes to the board and the JSON file."""
    application_id: str
    client_name: str
    client_type: str
    requested_services: str = ""
    estimated_aum: float
    submission_date: str = ""
    status: Literal["processed", "failed"]
    final_risk_tier: RiskTier | None = None
    model_risk_tier: RiskTier | None = None
    rule_floor_tier: RiskTier | None = None
    routing_queue: str | None = None
    tier_adjustments: list[str] = []
    policy_checks: list[str] = []
    rule_hits: list[RuleHit] = []
    risk_assessment: RiskAssessment | None = None
    summary: OnboardingSummary | None = None
    needs_human_review: bool = True  # always true: AI recommends, people decide
    model: str | None = None
    prompt_versions: dict[str, str] = {}
    processed_at: str | None = None
    error: str | None = None
