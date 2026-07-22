import json

from google.genai import types

from gemini_client import MODEL, get_client
from schemas import ExtractedDocumentData

_SYSTEM = (
    "You are a document intelligence agent inside a bank's loan underwriting pipeline. "
    "You are given raw text from an applicant's financial documents (bank statements, "
    "payslips, employment letters). Extract verifiable facts only -- do not speculate "
    "beyond what the text supports. Flag any mismatch between stated and observed income, "
    "any bounced-payment (NSF) events, and any other anomaly with a severity rating."
)


def extract_financial_data(raw_document_text: str, stated_monthly_income: float) -> ExtractedDocumentData:
    client = get_client()
    user_content = json.dumps(
        {
            "stated_monthly_income_on_application": stated_monthly_income,
            "raw_document_text": raw_document_text,
        },
        indent=2,
    )
    response = client.models.generate_content(
        model=MODEL,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM,
            response_mime_type="application/json",
            response_schema=ExtractedDocumentData,
        ),
    )
    return response.parsed
