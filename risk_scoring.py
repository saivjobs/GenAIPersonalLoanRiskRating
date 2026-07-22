import json

from google.genai import types

from gemini_client import MODEL, get_client
from rag.retriever import build_applicant_query, retrieve_relevant_policy
from schemas import ExtractedDocumentData, RiskAssessment, StructuredMetrics

_SYSTEM = (
    "You are a credit risk reasoning agent inside a bank's underwriting layer. "
    "You are given: (1) a probability of default (PD) and its decile rank from a "
    "validated, trained ML model, (2) structured application metrics, (3) document "
    "extraction findings, and (4) retrieved excerpts from the bank's own underwriting "
    "policy documents, selected because they are relevant to this specific applicant's "
    "profile. Ground your scoring decision and rationale in the retrieved policy "
    "excerpts wherever they apply -- if a policy excerpt gives a threshold or rule "
    "relevant to this applicant, follow it, and reference it by its source document name "
    "in your reasoning. Synthesize everything into ONE risk score from 1 (lowest risk) "
    "to 10 (highest risk), reading the applicant's financial history as a single "
    "connected story. The PD decile is a strong anchor for the score -- do not deviate "
    "from it by more than 1-2 points unless the document extraction findings or retrieved "
    "policy reveal something the PD model could not see. Do not invent facts not present "
    "in the input, and do not invent policy rules not present in the retrieved excerpts. "
    "Write the rationale so an underwriter can verify it in under a minute. NEVER "
    "reference the applicant's protected attributes (they are not provided to you, and "
    "must never factor into the score). In policy_sources_cited, list the filenames "
    "(the 'source' field) of only the retrieved policy excerpts you actually relied on."
)


def run_risk_rating_engine(
    applicant_id: str,
    metrics: StructuredMetrics,
    extracted: ExtractedDocumentData,
    computed_pd: float,
    pd_decile: int,
) -> RiskAssessment:
    client = get_client()

    # Deliberately exclude applicant_group -- the LLM should never see it.
    metrics_for_llm = metrics.model_dump(exclude={"applicant_group"})

    # RAG step: retrieve the policy passages most relevant to THIS applicant,
    # rather than dumping every policy document into every prompt.
    query = build_applicant_query(metrics, extracted, pd_decile)
    retrieved_policy = retrieve_relevant_policy(query, top_k=4)

    user_payload = {
        "applicant_id": applicant_id,
        "computed_probability_of_default": computed_pd,
        "pd_decile_1_to_10": pd_decile,
        "structured_metrics": metrics_for_llm,
        "document_extraction_findings": extracted.model_dump(),
        "retrieved_policy_excerpts": [
            {"source": p["source"], "text": p["text"]} for p in retrieved_policy
        ],
    }

    response = client.models.generate_content(
        model=MODEL,
        contents=json.dumps(user_payload, indent=2),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            response_mime_type="application/json",
            response_schema=RiskAssessment,
            temperature=0.2,
        ),
    )
    return response.parsed
