import json
import os
from typing import List

from db import fetch_all_audit_records, insert_audit_record
from schemas import AuditRecord, RiskAssessment, RoutingDecision

_POLICY_BANDS = [
    (2, "Very Low", "Straight-through processing; auto-approve within policy limits", False),
    (4, "Low", "Automated approval with light system checks", False),
    (6, "Moderate", "Manual review by a credit analyst; income/document verification", True),
    (8, "High", "Senior underwriter review; consider collateral/guarantor, reduced amount, or repricing", True),
    (10, "Very High", "Decline, or exception-only approval with committee sign-off", True),
]


def route_application(assessment: RiskAssessment) -> RoutingDecision:
    for max_score, tier, action, needs_review in _POLICY_BANDS:
        if assessment.risk_score <= max_score:
            return RoutingDecision(risk_tier=tier, scrutiny_action=action, requires_human_review=needs_review)
    raise ValueError(f"risk_score {assessment.risk_score} out of policy range 1-10")


def log_audit_record(record: AuditRecord) -> None:
    """Persists the record to the SQLite governance database (see db.py)."""
    insert_audit_record(record)


def load_audit_log() -> List[AuditRecord]:
    """Loads every audit record from the SQLite governance database."""
    return fetch_all_audit_records()
