"""
Builds the RAG index: chunks every markdown file in policy_docs/, embeds
each chunk with Gemini's embedding model, and upserts the result into a
persistent Chroma collection (a real vector database, not an in-memory
numpy array).

Run this once, and again any time you edit/add a policy document:
    python rag/build_index.py
"""

import glob
import os

import chromadb
from google import genai
from google.genai import types

EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "gemini-embedding-001")
POLICY_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "policy_docs")
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "rag_index", "chroma_db")
COLLECTION_NAME = "policy_docs"


def chunk_markdown(text: str, source: str) -> list[dict]:
    """
    Splits a markdown file into chunks along '## ' headers. Each chunk keeps
    its header as context, which produces better retrieval than raw
    paragraph splitting for structured policy documents like these.
    """
    chunks = []
    sections = text.split("\n## ")
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        content = section if i == 0 else "## " + section
        if len(content) < 20:
            continue
        chunks.append({"source": source, "text": content})
    return chunks


def build_index():
    genai_client = genai.Client()
    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Rebuild from scratch each run so stale chunks from edited/removed
    # documents don't linger in the index.
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection didn't exist yet -- fine
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity, matches the query-time scoring
    )

    doc_paths = sorted(glob.glob(os.path.join(POLICY_DOCS_DIR, "*.md")))
    if not doc_paths:
        raise RuntimeError(f"No policy documents found in {POLICY_DOCS_DIR}")

    all_chunks = []
    for path in doc_paths:
        with open(path, "r") as f:
            text = f.read()
        source_name = os.path.basename(path)
        all_chunks.extend(chunk_markdown(text, source_name))

    print(f"Chunked {len(doc_paths)} documents into {len(all_chunks)} chunks. Embedding...")

    texts = [c["text"] for c in all_chunks]
    response = genai_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    embeddings = [e.values for e in response.embeddings]

    collection.upsert(
        ids=[f"{c['source']}::chunk{i}" for i, c in enumerate(all_chunks)],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": c["source"]} for c in all_chunks],
    )

    print(f"Upserted {len(all_chunks)} chunks into Chroma collection "
          f"'{COLLECTION_NAME}' at {CHROMA_DB_PATH}")


if __name__ == "__main__":
    build_index()
