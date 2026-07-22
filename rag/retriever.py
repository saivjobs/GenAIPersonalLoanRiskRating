"""
Retrieval half of the RAG pipeline. Embeds a query (built from the
applicant's profile) and retrieves the top-k most relevant policy chunks
from the persistent Chroma vector database built by build_index.py.
"""

import os

import chromadb
from google import genai
from google.genai import types

EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "gemini-embedding-001")
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "rag_index", "chroma_db")
COLLECTION_NAME = "policy_docs"

_collection = None
_genai_client = None


def _get_collection():
    global _collection
    if _collection is None:
        if not os.path.exists(CHROMA_DB_PATH):
            raise RuntimeError(
                f"Chroma index not found at {CHROMA_DB_PATH}. Run `python rag/build_index.py` first."
            )
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = chroma_client.get_collection(COLLECTION_NAME)
    return _collection


def _get_genai_client():
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client()
    return _genai_client


def retrieve_relevant_policy(query: str, top_k: int = 4) -> list[dict]:
    """Returns the top_k most relevant policy chunks as {source, text, score} dicts."""
    collection = _get_collection()
    client = _get_genai_client()

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    query_vec = response.embeddings[0].values

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]  # cosine distance, since the collection uses hnsw:space=cosine

    return [
        {
            "source": meta["source"],
            "text": doc,
            "score": 1 - dist,  # convert cosine distance back to a similarity score
        }
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]


def build_applicant_query(metrics, extracted, pd_decile: int) -> str:
    """Builds a natural-language retrieval query from the applicant's profile."""
    parts = [
        f"bureau score {metrics.bureau_score}",
        f"debt-to-income ratio {metrics.debt_to_income:.0%}",
        f"{metrics.nsf_events_3m} NSF events in the last 3 months",
        f"employment tenure {metrics.employment_tenure_months} months",
        f"PD decile {pd_decile} out of 10",
    ]
    if extracted.income_discrepancy_notes:
        parts.append(f"income discrepancy: {extracted.income_discrepancy_notes}")
    if extracted.anomalies:
        parts.append("document anomalies: " + "; ".join(a.finding for a in extracted.anomalies))
    return ". ".join(parts)
