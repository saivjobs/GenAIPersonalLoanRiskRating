"""
Predictive Risk Model (ML) serving layer.

Loads the model trained by train_pd_model.py and scores new applicants.
Replaces the hand-written formula from the prototype -- this is now a real
trained gradient boosting model.
"""

import joblib
import pandas as pd

from data.generate_synthetic_data import FEATURE_COLUMNS
from schemas import StructuredMetrics

MODEL_PATH = "model_artifacts/pd_model.joblib"
DECILE_MAP_PATH = "model_artifacts/pd_decile_to_score.joblib"

_model = None
_decile_edges = None


def _load_artifacts():
    global _model, _decile_edges
    if _model is None:
        try:
            _model = joblib.load(MODEL_PATH)
            _decile_edges = joblib.load(DECILE_MAP_PATH)
        except FileNotFoundError as e:
            raise RuntimeError(
                "PD model artifacts not found. Run `python train_pd_model.py` first."
            ) from e
    return _model, _decile_edges


def calculate_pd(metrics: StructuredMetrics, loan_amount_requested: float,
                  open_trade_lines: int, credit_utilization: float) -> float:
    """
    Returns the model's predicted probability of default for this applicant.

    Note the extra fields beyond StructuredMetrics (loan_amount_requested,
    open_trade_lines, credit_utilization) -- the trained model needs the
    full feature set it was trained on. Extend StructuredMetrics in
    schemas.py if you want these captured on the application form directly.
    """
    model, _ = _load_artifacts()

    row = pd.DataFrame([{
        "bureau_score": metrics.bureau_score,
        "debt_to_income": metrics.debt_to_income,
        "nsf_events_3m": metrics.nsf_events_3m,
        "employment_tenure_months": metrics.employment_tenure_months,
        "stated_monthly_income": metrics.stated_monthly_income,
        "loan_amount_requested": loan_amount_requested,
        "open_trade_lines": open_trade_lines,
        "credit_utilization": credit_utilization,
    }])[FEATURE_COLUMNS]

    pd_value = float(model.predict_proba(row)[:, 1][0])
    return round(pd_value, 4)


def pd_to_decile(pd_value: float) -> int:
    """Maps a PD value to its decile (1-10) using the boundaries fit at training time."""
    _, decile_edges = _load_artifacts()
    for i in range(10):
        if decile_edges[i] <= pd_value <= decile_edges[i + 1]:
            return i + 1
    return 10
