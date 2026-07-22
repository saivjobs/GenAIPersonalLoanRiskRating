# Fair Lending and Explainability Guardrails

## Prohibited Basis for Scoring
The risk score must never be influenced, directly or indirectly, by an
applicant's race, color, religion, national origin, sex, marital status,
age (provided the applicant can legally contract), receipt of public
assistance income, or the exercise of any right under the Consumer Credit
Protection Act. These attributes must never appear in the reasoning model's
input, and must never be referenced in the rationale, even implicitly
through proxies such as zip code narratives.

## Adverse Action Explainability
Every score of 5 or above must be accompanied by a customer-facing
explanation that names the specific, verifiable factors that drove the
score -- not generic language. Acceptable factor descriptions cite concrete
figures (e.g., "debt-to-income ratio of 46%," "one returned payment in the
last 90 days"). Vague statements such as "overall financial profile" or
"general risk assessment" do not satisfy explainability requirements and
should not be used as a rationale on their own.

## Consistency Requirement
Two applicants with materially identical structured metrics and document
findings should receive the same score and the same tier placement. If a
narrative distinguishes two similar-looking applicants, the distinguishing
factor must be explicitly named (e.g., one NSF event was isolated, the
other was part of a recurring pattern).
