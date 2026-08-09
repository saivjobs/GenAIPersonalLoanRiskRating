import sys
from pathlib import Path

# Ensure project root is on sys.path so imports work from this scripts/ folder
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from main import process_application
from schemas import StructuredMetrics

applicant_id = "SMOKE-0001"
metrics = StructuredMetrics(
    bureau_score=700,
    debt_to_income=0.30,
    nsf_events_3m=0,
    stated_monthly_income=7500.0,
    employment_tenure_months=36,
    loan_amount_requested=10000.0,
    open_trade_lines=6,
    credit_utilization=0.25,
    applicant_group=None,
)
document_text = (
    "Bank Statement: recurring payroll deposits averaging $7,500/month. No NSF events. "
    "Stable employment, timely payments noted."
)

print("Running smoke interaction for", applicant_id)
result = process_application(applicant_id, metrics, document_text)
print("--- Result ---")
print("Risk Score:", result.risk_assessment.risk_score)
print("PD:", f"{result.computed_pd:.4f}", f"(decile {result.pd_decile}/10)")
print("Risk Tier:", result.routing_decision.risk_tier)
print("Human Review Required:", result.routing_decision.requires_human_review)
print("Policy sources cited:", result.risk_assessment.policy_sources_cited)
print("Top factors:", result.risk_assessment.top_contributing_factors)
