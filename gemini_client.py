"""
Requires: pip install google-genai pydantic scikit-learn pandas numpy joblib
Requires: export GEMINI_API_KEY="your-gemini-api-key-here"
Get a free key at https://aistudio.google.com/apikey
"""

import os

from google import genai

MODEL = os.environ.get("RISK_ENGINE_MODEL", "gemini-flash-latest")

_client = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client
