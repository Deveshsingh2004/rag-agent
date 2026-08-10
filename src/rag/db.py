"""Shared DB + embedding helpers for the RAG layer."""

from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://rag:rag@localhost:5432/rag",
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
EMBED_DIM = 768


def get_conn() -> psycopg.Connection:
    """Connect, ensure vector type exists, then register the Python adapter.

    Order matters: pgvector's register_vector looks up the `vector` type in
    pg_type. That type only appears after CREATE EXTENSION vector — so a brand
    new DB fails if we register first (reset_schema runs too late).
    """
    conn = psycopg.connect(DATABASE_URL)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.commit()
    register_vector(conn)
    return conn


def embed_texts(texts: list[str], *, task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed one or more texts. task_type: RETRIEVAL_DOCUMENT for ingest, RETRIEVAL_QUERY for search."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY in .env")
    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=EMBED_DIM,
        ),
    )
    return [list(e.values) for e in result.embeddings]
