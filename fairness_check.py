"""
Fairness / disparate-impact check, per design doc section 4.3 ("Fairness
evaluation sets: held-out samples with protected attributes to test for
disparate impact before go-live") and section 3's guardrail ("the model
must be tested for bias against protected groups... ECOA/Reg B").

This is a STARTING POINT, not a substitute for a real fair-lending review.
It implements the "four-fifths rule" (80% rule) commonly used as an initial
screen for disparate impact in US lending and employment contexts -- but
the four-fifths rule is a rule of thumb, not a legal safe harbor, and does
not replace statistical significance testing or legal review. Consult your
compliance/legal team on the correct methodology for your jurisdiction.

IMPORTANT: applicant_group is retained in the audit log ONLY for this kind
of testing. It is never shown to the LLM (see risk_scoring.py) and is never
a feature in the PD model (see data/generate_synthetic_data.py).
"""

from collections import defaultdict
from typing import List

from schemas import AuditRecord

APPROVAL_TIERS = {"Very Low", "Low"}  # tiers that flow to approval without decline risk


def four_fifths_rule_check(records: List[AuditRecord]) -> dict:
    """
    Compares the "favorable outcome" rate (routed to Low/Very Low tiers)
    across applicant_group values. Flags any group whose favorable rate is
    below 80% of the group with the highest favorable rate.
    """
    group_totals = defaultdict(int)
    group_favorable = defaultdict(int)

    for r in records:
        if r.applicant_group is None:
            continue
        group_totals[r.applicant_group] += 1
        if r.routing_decision.risk_tier in APPROVAL_TIERS:
            group_favorable[r.applicant_group] += 1

    if not group_totals:
        return {"status": "no_data", "detail": "No records with applicant_group found."}

    rates = {g: group_favorable[g] / group_totals[g] for g in group_totals}
    max_rate = max(rates.values()) if rates else 0
    flagged = {
        g: rate for g, rate in rates.items()
        if max_rate > 0 and (rate / max_rate) < 0.8
    }

    return {
        "status": "flagged" if flagged else "pass",
        "favorable_rates_by_group": rates,
        "sample_sizes_by_group": dict(group_totals),
        "groups_below_four_fifths_threshold": flagged,
        "note": (
            "This is a preliminary statistical screen only. A 'pass' here does NOT "
            "mean the model is fair-lending compliant -- consult legal/compliance "
            "for the full review required before production use."
        ),
    }


if __name__ == "__main__":
    import json
    from workflow import load_audit_log

    records = load_audit_log()
    result = four_fifths_rule_check(records)
    print(json.dumps(result, indent=2))
