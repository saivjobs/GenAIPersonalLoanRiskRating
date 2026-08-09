# Gen AI-Powered Customer Risk Rating Engine (v2 — real trained PD model)

This is the step up from the Colab prototype: the hand-written PD formula is
replaced with an **actual trained gradient boosting model**, plus a fairness
testing scaffold that was entirely missing before.

## Files

| File | Purpose |
|---|---|
| `data/generate_synthetic_data.py` | Synthetic loan dataset (stand-in for real data — see below) |
| `train_pd_model.py` | Trains the PD model, saves it, prints AUC/Brier score, computes PD deciles |
| `pd_model.py` | Loads the trained model and scores new applicants |
| `schemas.py` | Data contracts (now includes `loan_amount_requested`, `open_trade_lines`, `credit_utilization` — the trained model's full feature set — plus `applicant_group` for fairness testing only) |
| `document_intelligence.py` | Document extraction layer (Gemini) |
| `risk_scoring.py` | Gen AI reasoning/scoring layer (Gemini), now anchored to the PD decile |
| `workflow.py` | Deterministic score→tier→action routing + audit logging |
| `fairness_check.py` | Four-fifths rule disparate-impact screen on the audit log |
| `policy_docs/*.md` | Underwriting policy knowledge base (RAG source documents) |
| `rag/build_index.py` | Chunks and embeds the policy docs into a persistent Chroma vector database |
| `rag/retriever.py` | Embeds an applicant query and retrieves the most relevant policy chunks via Chroma |
| `app.py` | Streamlit frontend -- form input, results display, audit log viewer, fairness check viewer |
| `main.py` | End-to-end orchestration (also used by app.py) |

## Setup

```bash
pip install -r requirements.txt
export GEMINI_API_KEY="your-gemini-api-key-here"   # free at aistudio.google.com/apikey

# 1. Train the PD model (creates model_artifacts/pd_model.joblib)
python train_pd_model.py

# 2. Build the RAG policy index (embeds policy_docs/*.md -- run once, and
#    again whenever you edit/add a policy document)
python rag/build_index.py

# 3. Run a sample applicant through the full pipeline
python main.py

# 4. Run the fairness screen on whatever's in the audit log
python fairness_check.py
```

## RAG layer (retrieval-augmented generation)

`policy_docs/` holds the bank's underwriting policy as markdown documents
(DTI thresholds, NSF handling rules, bureau score bands, fair-lending
guardrails, the master risk-score-band table). `rag/build_index.py` chunks
each document by header, embeds every chunk with Gemini's embedding model
(`gemini-embedding-001`), and upserts them into a **persistent Chroma
vector database** (`rag_index/chroma_db/`) -- a real vector store with
approximate-nearest-neighbor search, not an in-memory array.

At scoring time, `risk_scoring.py` builds a short natural-language query
from the applicant's profile (bureau score, DTI, NSF count, PD decile,
document anomalies), embeds it, and Chroma returns the top-4 most relevant
policy chunks by cosine similarity (`rag/retriever.py`) -- not the whole
policy library, just what's relevant to *this* applicant. Those excerpts
are injected into the reasoning prompt, and the system instruction requires
the LLM to ground its scoring decision in them and cite the source
filenames it actually relied on (`policy_sources_cited` in the output).

This is genuine RAG, not a static prompt: the retrieved context changes per
applicant, and the model is instructed not to invent policy rules beyond
what was retrieved. Editing `policy_docs/` and rerunning
`python rag/build_index.py` rebuilds the Chroma collection from scratch, so
stale chunks from removed/edited documents never linger.

**Note:** Gemini generates the embeddings (so document and query vectors
stay from the same model); Chroma is used purely as the vector index/store
on top of them, not for its own built-in embedding function.

## Replacing synthetic data with real data

`train_pd_model.py` has a `DATA_PATH` variable near the top, currently `None`
(which triggers synthetic data generation). Set it to a CSV path:

```python
DATA_PATH = "data/lending_club.csv"
```

The CSV needs these columns (rename yours to match, or edit
`FEATURE_COLUMNS`/`TARGET_COLUMN` in `data/generate_synthetic_data.py`):
`bureau_score, debt_to_income, nsf_events_3m, employment_tenure_months,
stated_monthly_income, loan_amount_requested, open_trade_lines,
credit_utilization, defaulted`. Optionally include `applicant_group` (or
your real protected-attribute column) — it's used only by `fairness_check.py`
and is never fed into the model or the LLM.

Good starting sources per the design doc section 4.2: Lending Club Loan Data
and Home Credit Default Risk on Kaggle, or German Credit Data on UCI/OpenML
for a smaller benchmark. **For actual production use, this must ultimately be
your institution's own loan performance data** (design doc section 4.3).

## What changed from the prototype, and why it matters

1. **Real trained model instead of a formula.** `calculate_baseline_pd()` is
   gone. The model is a `GradientBoostingClassifier` trained on labeled
   outcomes, with held-out AUC/Brier score printed at training time so you
   can see how good it actually is — not just assume it.
2. **PD deciles, not raw scores.** Per design doc section 5 ("map PD deciles
   to the 1-10 score"), `pd_model.py` computes the applicant's decile rank
   against the training distribution, and the LLM is told to anchor to that
   decile rather than free-reasoning the whole score from scratch.
3. **A fairness testing scaffold exists now.** It didn't before. `applicant_group`
   flows through the pipeline in the audit log only — never as a model
   feature, never in the LLM prompt (see the `exclude={"applicant_group"}`
   in `risk_scoring.py`) — and `fairness_check.py` runs a four-fifths rule
   screen against it.

## What is still NOT done — read this before treating this as production-ready

This remains a **prototype with real components**, not a production system.
Specifically, per the design doc's own section 5 and section 3 guardrail:

- **The model is trained on synthetic data.** AUC 0.77 on synthetic data
  tells you the *pipeline* works, not that the *model* is any good on real
  applicants. Retrain on real data before this touches a real decision.
- **The four-fifths check is a screen, not a compliance sign-off.** Real
  fair-lending review (ECOA/Reg B or your local equivalent) needs your legal
  and compliance teams, statistical significance testing, and likely
  additional protected classes beyond the single synthetic one here.
- **No document-extraction accuracy has been measured against real, messy
  documents** — only clean synthetic text.
- **No credit risk committee has reviewed or approved the score bands** —
  they're still the design doc's illustrative example.
- **No human-in-the-loop pilot has run.** Every score here has gone straight
  through code, with no underwriter in the loop overriding or validating it.

None of this is a reason not to keep building — it's the actual checklist
for getting there, straight from your own design doc's Suggested Next Steps.

## Frontend (Streamlit)

`app.py` is a three-tab web UI: a form to score a new applicant, an audit
log viewer, and the fairness check viewer -- all wired directly to the
pipeline you already ran from the CLI.

**Run locally:**
```bash
streamlit run app.py
```
Opens at `http://localhost:8501`.

Combined project documentation and assets: a single-file PDF containing the README, presentation guide, technical deep dive, executive summary, and architecture source is available at:

- [COMBINED_DOCUMENT.pdf](COMBINED_DOCUMENT.pdf#L1)

**Deploy for free on Streamlit Community Cloud (recommended for sharing):**
1. Push this repo to GitHub (see below).
2. Go to share.streamlit.io, sign in with GitHub.
3. Click "New app", pick this repo, set the entry point to `app.py`.
4. In the app's Settings -> Secrets, paste:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key-here"
   ```
5. Deploy. You'll get a public `*.streamlit.app` URL that runs the full
   pipeline in the browser, for free.

**Never commit your real API key.** `.streamlit/secrets.toml` is in
`.gitignore` for local runs; `.streamlit/secrets.toml.example` shows the
format to copy. For the hosted version, the key only ever lives in
Streamlit Cloud's Secrets manager, not in the repo.

## Pushing to GitHub

```bash
git init  # only if not already a repo
git add .
git commit -m "Add RAG-grounded risk rating engine with Streamlit frontend"
git branch -M main
git remote add origin https://github.com/saivjobs/GenAIPersonalLoanRiskRating.git
git push -u origin main
```

## Database (SQLite)

The governance layer is now backed by a real relational database
(`db.py`), not a flat file. `audit_records` has structured, queryable
columns (applicant_id, timestamp, PD, decile, score, tier, human-review
flag, fairness group, human override) plus JSON columns for the full
nested extraction/assessment/routing objects, so no data is lost while
still enabling SQL queries.

`workflow.py`'s `log_audit_record()` / `load_audit_log()` functions now
delegate to `db.py` under the hood -- `main.py`, `app.py`, and
`fairness_check.py` didn't need to change.

**Default file:** `risk_engine.db` in the working directory. Override with
`RISK_ENGINE_DB_PATH`. The Streamlit "Audit Log" tab also lets an
underwriter record a human override decision against any scored applicant,
directly satisfying the design doc's "human underwriters remain the final
decision-makers for scores of 5 and above" requirement.

**Caveat if deployed on Streamlit Community Cloud:** its filesystem is
ephemeral -- the SQLite file resets when the app redeploys or the
container restarts. Fine for demos; for real persistence, swap `db.py`'s
connection for a hosted database (e.g. Supabase or Neon Postgres) -- only
`db.py` needs to change, since `schemas.py` and `workflow.py` are
database-agnostic.
