from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentAnomaly(BaseModel):
    document_type: str = Field(description="e.g. Bank Statement, Payslip, Employment Letter")
    finding: str = Field(description="The mismatch, anomaly, or notable data point found")
    severity: str = Field(description="LOW, MEDIUM, or HIGH")


class ExtractedDocumentData(BaseModel):
    observed_monthly_income: Optional[float] = Field(default=None)
    income_discrepancy_notes: Optional[str] = Field(default=None)
    nsf_events_detected: int = Field(default=0)
    anomalies: List[DocumentAnomaly] = Field(default_factory=list)
    extraction_summary: str


class StructuredMetrics(BaseModel):
    bureau_score: int = Field(ge=300, le=900)
    debt_to_income: float = Field(ge=0, le=3)
    nsf_events_3m: int = Field(default=0, ge=0)
    stated_monthly_income: float
    employment_tenure_months: int = Field(default=0, ge=0)
    # Additional fields the trained PD model needs (see data/generate_synthetic_data.py)
    loan_amount_requested: float
    open_trade_lines: int = Field(default=0, ge=0)
    credit_utilization: float = Field(ge=0, le=1)
    # Retained ONLY for fairness testing -- never passed to the PD model or the LLM prompt.
    applicant_group: Optional[str] = Field(default=None, description="Protected attribute, fairness testing only")


class RiskAssessment(BaseModel):
    risk_score: int = Field(ge=1, le=10)
    top_contributing_factors: List[str]
    financial_story_summary: str
    customer_facing_explanation: str
    confidence_notes: Optional[str] = Field(default=None)
    policy_sources_cited: List[str] = Field(
        default_factory=list,
        description="Filenames of the retrieved policy documents actually relied on for this score",
    )


class RoutingDecision(BaseModel):
    risk_tier: str
    scrutiny_action: str
    requires_human_review: bool


class AuditRecord(BaseModel):
    applicant_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    computed_pd: float
    pd_decile: int
    extracted_data: ExtractedDocumentData
    risk_assessment: RiskAssessment
    routing_decision: RoutingDecision
    applicant_group: Optional[str] = None  # carried through ONLY for fairness audits
    human_override: Optional[str] = None
