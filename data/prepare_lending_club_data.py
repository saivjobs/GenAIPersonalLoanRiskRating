"""
Converts the raw Kaggle Lending Club dataset into the schema
train_pd_model.py expects (see data/generate_synthetic_data.py's
FEATURE_COLUMNS and TARGET_COLUMN).

Download the data first (from your terminal, not in this script):
    pip install kaggle
    # Get a free API token: kaggle.com -> Account -> "Create New API Token"
    # This downloads kaggle.json -- place it at ~/.kaggle/kaggle.json (Linux/Mac)
    # or C:\\Users\\<you>\\.kaggle\\kaggle.json (Windows)
    kaggle datasets download -d wordsforthewise/lending-club
    unzip lending-club.zip -d data/lending_club_raw

Then run this script:
    python data/prepare_lending_club_data.py

It writes data/lending_club_prepared.csv, ready to point train_pd_model.py's
DATA_PATH at.

IMPORTANT LIMITATION, stated explicitly rather than hidden: Lending Club's
public data has no bank-statement-level NSF (returned payment) field --
that's not something a credit bureau or loan platform publishes. This
script approximates nsf_events_3m using capped 2-year delinquency count as
a rough stand-in. This is a real gap versus what your production system
would have (real internal banking transaction data), not a perfect
substitute -- document this when you present the model's results.
"""

import glob
import os
import gzip

import pandas as pd

RAW_CSV_PATH = os.environ.get(
    "LENDING_CLUB_RAW_PATH",
    None,  # set this, or set the LENDING_CLUB_RAW_PATH env var, to the raw CSV/CSV.GZ path
)
OUTPUT_PATH = "data/lending_club_prepared.csv"

# Only closed loans have a known final outcome -- "Current", "Late", "In
# Grace Period", "Issued" loans haven't resolved yet and would mislabel the
# target if included.
GOOD_STATUSES = {"Fully Paid"}
BAD_STATUSES = {"Charged Off", "Default"}

# Only read the columns we actually need -- the full file has 150+ columns
# and can be several GB; this keeps memory usage manageable.
USECOLS = [
    "loan_amnt", "annual_inc", "dti", "delinq_2yrs", "fico_range_low",
    "fico_range_high", "emp_length", "open_acc", "revol_util", "loan_status",
]


def _find_raw_file() -> str:
    if RAW_CSV_PATH:
        return RAW_CSV_PATH
    candidates = glob.glob("data/lending_club_raw/*.csv") + glob.glob("data/lending_club_raw/*.csv.gz")
    if not candidates:
        raise RuntimeError(
            "Could not find the raw Lending Club CSV. Set LENDING_CLUB_RAW_PATH "
            "or place the file under data/lending_club_raw/."
        )
    return candidates[0]


def _read_raw_dataframe(raw_path: str) -> pd.DataFrame:
    if raw_path.endswith(".gz"):
        with gzip.open(raw_path, "rt", encoding="utf-8", errors="replace") as handle:
            return pd.read_csv(handle, usecols=USECOLS, low_memory=False)
    return pd.read_csv(raw_path, usecols=USECOLS, low_memory=False)


def _emp_length_to_months(value) -> float:
    if pd.isna(value) or value == "n/a":
        return 0.0
    value = str(value).strip()
    if value.startswith("< 1"):
        return 6.0
    if value.startswith("10+"):
        return 120.0
    digits = "".join(ch for ch in value if ch.isdigit())
    return float(digits) * 12 if digits else 0.0


def prepare_lending_club_data():
    raw_path = _find_raw_file()
    print(f"Reading {raw_path} (this may take a while for the full multi-GB file)...")

    df = _read_raw_dataframe(raw_path)
    print(f"Loaded {len(df):,} raw rows.")

    df = df[df["loan_status"].isin(GOOD_STATUSES | BAD_STATUSES)].copy()
    print(f"{len(df):,} rows remain after keeping only closed loans (Fully Paid / Charged Off / Default).")

    df = df.dropna(subset=["annual_inc", "dti", "fico_range_low", "fico_range_high"])

    prepared = pd.DataFrame()
    prepared["bureau_score"] = (df["fico_range_low"] + df["fico_range_high"]) / 2
    prepared["debt_to_income"] = (df["dti"] / 100).clip(lower=0, upper=3)
    # Approximation -- see module docstring. Capped at 4 to avoid a few
    # extreme outliers dominating the "NSF" signal.
    prepared["nsf_events_3m"] = df["delinq_2yrs"].fillna(0).clip(upper=4).astype(int)
    prepared["employment_tenure_months"] = df["emp_length"].apply(_emp_length_to_months)
    prepared["stated_monthly_income"] = df["annual_inc"] / 12
    prepared["loan_amount_requested"] = df["loan_amnt"]
    prepared["open_trade_lines"] = df["open_acc"].fillna(0)
    prepared["credit_utilization"] = (df["revol_util"].fillna(0) / 100).clip(lower=0, upper=1)
    prepared["defaulted"] = df["loan_status"].isin(BAD_STATUSES).astype(int)

    prepared = prepared.dropna()

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    prepared.to_csv(OUTPUT_PATH, index=False)

    print(f"\nWrote {len(prepared):,} prepared rows to {OUTPUT_PATH}")
    print(f"Default rate: {prepared['defaulted'].mean():.2%}")
    print("\nNext step: set DATA_PATH = \"data/lending_club_prepared.csv\" "
          "in train_pd_model.py, then rerun `python train_pd_model.py`.")


if __name__ == "__main__":
    prepare_lending_club_data()
