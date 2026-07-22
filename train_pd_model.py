"""
Trains and saves the Predictive Risk Model (ML) layer -- section 2.1 of the
design doc. This replaces the hand-written PD formula from the prototype
with an actual model trained on historical loan outcomes.

Usage:
    python train_pd_model.py

Swapping in real data: edit DATA_PATH below to point at your Lending Club /
Home Credit / internal CSV. As long as it has the columns listed in
data/generate_synthetic_data.py's FEATURE_COLUMNS and TARGET_COLUMN (rename
columns if needed), no other code changes are required.
"""

import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report
from sklearn.model_selection import train_test_split

sys.path.insert(0, "data")
from generate_synthetic_data import (  # noqa: E402
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    generate_synthetic_loan_data,
)

# If you've run data/prepare_lending_club_data.py, this auto-detects the
# prepared real-data CSV and uses it. Otherwise falls back to synthetic
# data with a printed warning. Override explicitly with:
#     DATA_PATH="data/your_own_data.csv" python train_pd_model.py
_PREPARED_LENDING_CLUB_PATH = "data/lending_club_prepared.csv"
DATA_PATH = os.environ.get(
    "DATA_PATH",
    _PREPARED_LENDING_CLUB_PATH if os.path.exists(_PREPARED_LENDING_CLUB_PATH) else None,
)
MODEL_OUTPUT_PATH = "model_artifacts/pd_model.joblib"
DECILE_MAP_OUTPUT_PATH = "model_artifacts/pd_decile_to_score.joblib"


def load_training_data() -> pd.DataFrame:
    if DATA_PATH:
        df = pd.read_csv(DATA_PATH)
        missing = set(FEATURE_COLUMNS + [TARGET_COLUMN]) - set(df.columns)
        if missing:
            raise ValueError(f"Real data is missing required columns: {missing}")
        return df
    print("DATA_PATH not set -- using synthetic data for demonstration. "
          "Replace with real loan performance data before production use.")
    return generate_synthetic_loan_data()


def train_model():
    df = load_training_data()
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Gradient boosting, as recommended in the design doc section 2.1.
    # Protected attributes are intentionally excluded from FEATURE_COLUMNS
    # (see data/generate_synthetic_data.py) -- they are retained separately
    # for fairness testing only, per design doc section 4.1.
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        random_state=42,
    )
    model.fit(X_train, y_train)

    test_probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, test_probs)
    brier = brier_score_loss(y_test, test_probs)

    print(f"\nHeld-out AUC: {auc:.4f}  (0.5 = random, 1.0 = perfect separation)")
    print(f"Held-out Brier score: {brier:.4f}  (lower = better calibrated)")
    print("\nClassification report at 0.5 threshold (for reference only --")
    print("production routing should use PD deciles, not a hard threshold):")
    print(classification_report(y_test, (test_probs >= 0.5).astype(int)))

    # Map PD deciles to the 1-10 risk score scale, per design doc section 5:
    # "map PD deciles to the 1-10 score." Decile boundaries are fit on the
    # full dataset's predicted PD distribution.
    all_probs = model.predict_proba(X)[:, 1]
    decile_edges = np.quantile(all_probs, np.linspace(0, 1, 11))  # 10 deciles -> 11 edges
    decile_edges[0] = 0.0
    decile_edges[-1] = 1.0

    joblib.dump(model, MODEL_OUTPUT_PATH)
    joblib.dump(decile_edges, DECILE_MAP_OUTPUT_PATH)
    print(f"\nSaved model to {MODEL_OUTPUT_PATH}")
    print(f"Saved PD-decile boundaries to {DECILE_MAP_OUTPUT_PATH}")
    print(f"Decile edges (PD values): {np.round(decile_edges, 4).tolist()}")

    return model, decile_edges


if __name__ == "__main__":
    train_model()
