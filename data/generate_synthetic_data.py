"""
Synthetic loan-outcome dataset generator.

IMPORTANT: This is a STAND-IN for real data, used only so the training
pipeline in train_pd_model.py can be demonstrated end-to-end without
internet access. It is NOT a substitute for real historical loan
performance data.

Before production use, replace this module's output with one of:
  - Your institution's own loan performance data (preferred -- see design
    doc section 4.3: "the production model must be trained and validated
    on your institution's own loan performance data")
  - Lending Club Loan Data (Kaggle: wordsforthewise/lending-club)
  - Home Credit Default Risk (Kaggle: home-credit-default-risk)
  - German Credit Data (UCI / OpenML)

Whatever the source, the real data must have the same column names used
here (see FEATURE_COLUMNS and TARGET_COLUMN below), or you must update
train_pd_model.py's column references to match.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "bureau_score",
    "debt_to_income",
    "nsf_events_3m",
    "employment_tenure_months",
    "stated_monthly_income",
    "loan_amount_requested",
    "open_trade_lines",
    "credit_utilization",
]
TARGET_COLUMN = "defaulted"  # 1 = defaulted / charged-off, 0 = fully paid

# Protected attribute, generated independently of creditworthiness so it can
# be used ONLY for fairness testing (see fairness_check.py). It is never
# passed into the model as a feature -- see train_pd_model.py.
PROTECTED_ATTRIBUTE_COLUMN = "applicant_group"  # synthetic categorical, e.g. "A" / "B"


def generate_synthetic_loan_data(n_rows: int = 20000, random_seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)

    bureau_score = rng.normal(680, 75, n_rows).clip(300, 900)
    debt_to_income = rng.beta(2, 5, n_rows) * 1.2  # skewed toward lower DTI
    nsf_events_3m = rng.poisson(0.3, n_rows)
    employment_tenure_months = rng.exponential(36, n_rows).clip(0, 480)
    stated_monthly_income = rng.lognormal(8.7, 0.4, n_rows)  # ~ centered near $6k
    loan_amount_requested = rng.lognormal(9.2, 0.5, n_rows)
    open_trade_lines = rng.poisson(6, n_rows)
    credit_utilization = rng.beta(2, 3, n_rows)

    # Protected attribute assigned independently of the risk features (by
    # construction), so a well-calibrated, unbiased model trained WITHOUT
    # this column should show no disparate impact across groups A/B.
    applicant_group = rng.choice(["A", "B"], size=n_rows, p=[0.6, 0.4])

    # True underlying default probability -- a nonlinear function of the
    # actual risk features only (protected attribute is NOT an input here).
    logit = (
        -4.5
        + (-0.012) * (bureau_score - 680)
        + 3.2 * debt_to_income
        + 0.55 * nsf_events_3m
        + (-0.004) * employment_tenure_months
        + 1.8 * credit_utilization
        + 0.15 * (loan_amount_requested / stated_monthly_income)
    )
    true_pd = 1 / (1 + np.exp(-logit))
    defaulted = rng.binomial(1, true_pd)

    df = pd.DataFrame(
        {
            "bureau_score": bureau_score.round(0),
            "debt_to_income": debt_to_income.round(4),
            "nsf_events_3m": nsf_events_3m,
            "employment_tenure_months": employment_tenure_months.round(1),
            "stated_monthly_income": stated_monthly_income.round(2),
            "loan_amount_requested": loan_amount_requested.round(2),
            "open_trade_lines": open_trade_lines,
            "credit_utilization": credit_utilization.round(4),
            PROTECTED_ATTRIBUTE_COLUMN: applicant_group,
            TARGET_COLUMN: defaulted,
        }
    )
    return df


if __name__ == "__main__":
    df = generate_synthetic_loan_data()
    out_path = "data/synthetic_loan_data.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"Default rate: {df[TARGET_COLUMN].mean():.3%}")
    print(df.groupby(PROTECTED_ATTRIBUTE_COLUMN)[TARGET_COLUMN].mean())
