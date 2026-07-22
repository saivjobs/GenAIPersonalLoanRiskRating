# Debt-to-Income and Income Verification Policy

## DTI Thresholds
Debt-to-income (DTI) is calculated as total monthly debt obligations divided
by verified monthly income, using observed bank-statement deposits rather
than the stated application figure whenever the two differ by more than 5%.

- DTI below 25%: treated as a strength; does not independently elevate risk.
- DTI between 25% and 35%: acceptable range for most borrower profiles;
  monitor in combination with other factors but do not treat as a standalone
  concern.
- DTI between 35% and 45%: elevated. Should be explicitly named as a
  contributing risk factor. Combined with any liquidity stress signal (NSF
  events, declining balances), this typically pushes an applicant toward the
  Moderate-to-High band.
- DTI above 45%: high leverage. On its own this generally does not justify a
  score above 8 unless paired with delinquency, fraud signals, or severe
  income instability, but it should always be cited as a top contributing
  factor when present.

## Income Discrepancy Handling
When stated income (from the application) and observed income (from bank
statement deposits) differ:
- Discrepancy under 5%: immaterial; do not flag.
- Discrepancy of 5-15%: note as a minor discrepancy in the rationale, and
  recompute DTI using the lower (observed) figure.
- Discrepancy over 15%: treat as a material finding. Recompute DTI using
  observed income, and explicitly state the dollar and percentage gap in the
  customer-facing explanation, since this is a common driver of adverse
  action under fair-lending explainability requirements.

## Variable and Gig Income
Applicants with a mix of stable payroll deposits and irregular
supplemental deposits (freelance, gig, cash) should not be penalized purely
for income variability. Weight the stable, recurring portion of income more
heavily in the DTI calculation, and note supplemental income as a
confidence caveat rather than a risk factor, unless the supplemental portion
represents more than 40% of total observed deposits, in which case treat the
overall income as variable and reduce confidence accordingly.
