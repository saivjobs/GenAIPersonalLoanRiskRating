"""
Streamlit frontend for the Gen AI-Powered Customer Risk Rating Engine.

Run locally:
    pip install -r requirements.txt
    export GEMINI_API_KEY="your-gemini-api-key-here"
    streamlit run app.py

Deploy for free on Streamlit Community Cloud:
    1. Push this repo to GitHub.
    2. Go to share.streamlit.io, sign in with GitHub, "New app", pick this
       repo and app.py as the entry point.
    3. In the app's Settings -> Secrets, add:
           GEMINI_API_KEY = "your-gemini-api-key-here"
       (Never commit the key itself to the repo.)
"""

import os

import streamlit as st

# On Streamlit Community Cloud, secrets are provided via st.secrets rather
# than a shell environment variable. Bridge the two so the rest of the
# codebase (gemini_client.py etc.) doesn't need to know the difference.
if "GEMINI_API_KEY" in st.secrets:
    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]

from main import print_report, process_application  # noqa: E402
from schemas import StructuredMetrics  # noqa: E402
from workflow import load_audit_log  # noqa: E402
from fairness_check import four_fifths_rule_check  # noqa: E402
from db import record_human_override  # noqa: E402

st.set_page_config(page_title="Personal Loan Risk Rating Engine", layout="wide")

TIER_COLORS = {
    "Very Low": "#1a7f37",
    "Low": "#57ab5a",
    "Moderate": "#d4a72c",
    "High": "#e0622a",
    "Very High": "#cf222e",
}

tab_score, tab_audit, tab_fairness = st.tabs(["Score an Applicant", "Audit Log", "Fairness Check"])

# ---------------------------------------------------------------------------
# Tab 1: Score a new applicant
# ---------------------------------------------------------------------------
with tab_score:
    st.title("Personal Loan Risk Rating Engine")
    st.caption(
        "Gen AI + trained ML risk model + policy-grounded RAG reasoning. "
        "Prototype -- not a production lending decision system. See README."
    )

    if not os.environ.get("GEMINI_API_KEY"):
        st.warning(
            "GEMINI_API_KEY is not set. Set it as an environment variable locally, "
            "or add it under Settings -> Secrets if deployed on Streamlit Community Cloud."
        )

    with st.form("applicant_form"):
        st.subheader("Applicant Details")
        col1, col2, col3 = st.columns(3)
        with col1:
            applicant_id = st.text_input("Applicant ID", value="APP-2026-0001")
            bureau_score = st.number_input("Bureau score", min_value=300, max_value=900, value=680)
            stated_monthly_income = st.number_input("Stated monthly income ($)", min_value=0.0, value=7000.0, step=100.0)
        with col2:
            debt_to_income = st.slider("Debt-to-income ratio", 0.0, 1.5, 0.35, step=0.01)
            nsf_events_3m = st.number_input("NSF events (last 3 months)", min_value=0, value=0, step=1)
            employment_tenure_months = st.number_input("Employment tenure (months)", min_value=0, value=24, step=1)
        with col3:
            loan_amount_requested = st.number_input("Loan amount requested ($)", min_value=0.0, value=12000.0, step=500.0)
            open_trade_lines = st.number_input("Open trade lines", min_value=0, value=5, step=1)
            credit_utilization = st.slider("Credit utilization", 0.0, 1.0, 0.35, step=0.01)

        applicant_group = st.selectbox(
            "Applicant group (fairness-testing attribute only -- never sent to the model)",
            options=["(not set)", "A", "B"],
        )

        document_text = st.text_area(
            "Bank statement / document text (paste extracted or raw text)",
            height=160,
            value=(
                "Bank Statement (last 3 months): Recurring payroll deposits averaging "
                "$6,900/month. No NSF events. Existing auto loan paid on time. "
                "No BNPL or short-term financing activity detected."
            ),
        )

        submitted = st.form_submit_button("Run Risk Assessment", type="primary")

    if submitted:
        metrics = StructuredMetrics(
            bureau_score=int(bureau_score),
            debt_to_income=float(debt_to_income),
            nsf_events_3m=int(nsf_events_3m),
            stated_monthly_income=float(stated_monthly_income),
            employment_tenure_months=int(employment_tenure_months),
            loan_amount_requested=float(loan_amount_requested),
            open_trade_lines=int(open_trade_lines),
            credit_utilization=float(credit_utilization),
            applicant_group=None if applicant_group == "(not set)" else applicant_group,
        )

        with st.spinner("Extracting documents, scoring, and retrieving policy context..."):
            try:
                result = process_application(applicant_id, metrics, document_text)
            except Exception as e:
                st.error(f"Pipeline failed: {e}")
                st.stop()

        a, d = result.risk_assessment, result.routing_decision
        tier_color = TIER_COLORS.get(d.risk_tier, "#888888")

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Risk Score", f"{a.risk_score}/10")
        c2.markdown(
            f"<div style='padding:0.5em 1em;background:{tier_color};color:white;"
            f"border-radius:6px;text-align:center;font-weight:600;'>{d.risk_tier}</div>",
            unsafe_allow_html=True,
        )
        c3.metric("PD (trained model)", f"{result.computed_pd:.2%}", f"decile {result.pd_decile}/10")

        st.markdown(f"**Routed Action:** {d.scrutiny_action}")
        st.markdown(f"**Human Review Required:** {'Yes' if d.requires_human_review else 'No'}")

        st.subheader("Top Contributing Factors")
        for factor in a.top_contributing_factors:
            st.markdown(f"- {factor}")

        st.subheader("Financial Story")
        st.write(a.financial_story_summary)

        st.subheader("Customer-Facing Explanation")
        st.write(a.customer_facing_explanation)

        if a.confidence_notes:
            st.subheader("Confidence Notes")
            st.write(a.confidence_notes)

        if a.policy_sources_cited:
            st.subheader("Grounded in Policy Documents (RAG)")
            for source in a.policy_sources_cited:
                st.markdown(f"- `{source}`")

        with st.expander("Raw document extraction findings"):
            st.json(result.extracted_data.model_dump())

# ---------------------------------------------------------------------------
# Tab 2: Audit log
# ---------------------------------------------------------------------------
with tab_audit:
    st.title("Audit Log")
    st.caption("Every scored applicant is logged here for governance and monitoring. "
               "Backed by a SQLite database (db.py) -- see README.")

    records = load_audit_log()
    if not records:
        st.info("No applicants scored yet. Run one from the 'Score an Applicant' tab.")
    else:
        rows = [
            {
                "Applicant ID": r.applicant_id,
                "Timestamp": r.timestamp,
                "PD": f"{r.computed_pd:.2%}",
                "PD Decile": r.pd_decile,
                "Risk Score": r.risk_assessment.risk_score,
                "Tier": r.routing_decision.risk_tier,
                "Human Review": r.routing_decision.requires_human_review,
                "Group (fairness only)": r.applicant_group or "-",
                "Human Override": r.human_override or "-",
            }
            for r in records
        ]
        st.dataframe(rows, use_container_width=True)

        st.subheader("Log a Human Override")
        st.caption(
            "Per the design doc: human underwriters remain the final decision-makers "
            "for scores of 5 and above. Use this to record their final call."
        )
        with st.form("override_form"):
            override_applicant_id = st.selectbox(
                "Applicant ID", options=[r.applicant_id for r in records]
            )
            override_note = st.text_area(
                "Override decision / notes",
                placeholder="e.g. Approved with reduced loan amount of $10,000 and guarantor required.",
            )
            override_submitted = st.form_submit_button("Save Override")
        if override_submitted and override_note.strip():
            record_human_override(override_applicant_id, override_note.strip())
            st.success(f"Override recorded for {override_applicant_id}.")
            st.rerun()

# ---------------------------------------------------------------------------
# Tab 3: Fairness check
# ---------------------------------------------------------------------------
with tab_fairness:
    st.title("Fairness Check (Four-Fifths Rule Screen)")
    st.caption(
        "A preliminary statistical screen only -- not a substitute for a full "
        "fair-lending / legal review. See fairness_check.py docstring."
    )

    records = load_audit_log()
    result = four_fifths_rule_check(records)

    if result["status"] == "no_data":
        st.info(result["detail"])
    else:
        st.metric("Status", result["status"].upper())
        st.subheader("Favorable Outcome Rate by Group")
        st.json(result["favorable_rates_by_group"])
        st.subheader("Sample Sizes by Group")
        st.json(result["sample_sizes_by_group"])
        if result["groups_below_four_fifths_threshold"]:
            st.error(f"Groups flagged below the four-fifths threshold: "
                      f"{result['groups_below_four_fifths_threshold']}")
        else:
            st.success("No groups flagged below the four-fifths threshold.")
        st.caption(result["note"])
