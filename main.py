"""
End-to-end orchestration using the trained PD model (not a formula).

Setup:
    pip install -r requirements.txt
    export GEMINI_API_KEY="your-gemini-api-key-here"
    python train_pd_model.py     # trains and saves the PD model (run once, or whenever data changes)
    python main.py                # runs a sample applicant through the full pipeline
"""

from document_intelligence import extract_financial_data
from pd_model import calculate_pd, pd_to_decile
from risk_scoring import run_risk_rating_engine
from schemas import AuditRecord, StructuredMetrics
from workflow import log_audit_record, route_application


def process_application(applicant_id: str, metrics: StructuredMetrics, raw_document_text: str) -> AuditRecord:
    extracted = extract_financial_data(raw_document_text, metrics.stated_monthly_income)

    computed_pd = calculate_pd(
        metrics,
        loan_amount_requested=metrics.loan_amount_requested,
        open_trade_lines=metrics.open_trade_lines,
        credit_utilization=metrics.credit_utilization,
    )
    pd_decile = pd_to_decile(computed_pd)

    assessment = run_risk_rating_engine(applicant_id, metrics, extracted, computed_pd, pd_decile)
    decision = route_application(assessment)

    record = AuditRecord(
        applicant_id=applicant_id,
        computed_pd=computed_pd,
        pd_decile=pd_decile,
        extracted_data=extracted,
        risk_assessment=assessment,
        routing_decision=decision,
        applicant_group=metrics.applicant_group,
    )
    log_audit_record(record)
    return record


def print_report(record: AuditRecord) -> None:
    a, d = record.risk_assessment, record.routing_decision
    print(f"\n--- Applicant {record.applicant_id} ---")
    print(f"Computed PD (trained model): {record.computed_pd}  (decile {record.pd_decile}/10)")
    print(f"Risk Score            : {a.risk_score}/10  ({d.risk_tier})")
    print(f"Routed Action         : {d.scrutiny_action}")
    print(f"Human Review Required : {d.requires_human_review}")
    print("Top Contributing Factors:")
    for factor in a.top_contributing_factors:
        print(f"  - {factor}")
    print(f"\nFinancial Story:\n  {a.financial_story_summary}")
    print(f"\nCustomer-Facing Explanation:\n  {a.customer_facing_explanation}")
    if a.confidence_notes:
        print(f"\nConfidence Notes:\n  {a.confidence_notes}")
    if a.policy_sources_cited:
        print(f"\nGrounded in Policy Documents (RAG):")
        for source in a.policy_sources_cited:
            print(f"  - {source}")


if __name__ == "__main__":
    sample_metrics = StructuredMetrics(
        bureau_score=645,
        debt_to_income=0.46,
        nsf_events_3m=2,
        stated_monthly_income=8500,
        employment_tenure_months=14,
        loan_amount_requested=15000,
        open_trade_lines=7,
        credit_utilization=0.72,
        applicant_group="A",  # retained for fairness testing only; never sent to the LLM or PD model
    )

    sample_document_text = """
    Bank Statement (last 3 months): Recurring payroll deposits averaging $7,200/month.
    Two returned-payment (NSF) events recorded, both in the most recent statement cycle.
    Two new Buy-Now-Pay-Later installment debits appeared 4 months ago and recur biweekly.
    Salary deposits are consistent in timing; a smaller variable cash deposit appears most
    weekends, inconsistent in amount, suggesting supplemental gig income not on the application.
    """

    result = process_application("APP-2026-8891", sample_metrics, sample_document_text)
    print_report(result)
