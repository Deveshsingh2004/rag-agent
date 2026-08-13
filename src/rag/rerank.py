"""Day 18 — Bi-encoder retrieve, then cross-encoder rerank.

Bi-encoder (pgvector): embed query once, embed docs at ingest, cosine KNN.
  Fast. Docs and query never see each other at score time.

Cross-encoder: score (query, chunk) as a pair. Slower (N forward passes),
  better ranking because the model attends to both texts together.

Prod pattern: retrieve top-50 cheaply, rerank to top-5.
This corpus is tiny — we retrieve 8 and rerank to 3 so the reorder is visible.

Default backend = Gemini pair-scoring (no torch download).
Set RERANK_BACKEND=local to use ms-marco-MiniLM-L-6-v2 via sentence-transformers.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.rag.search import search

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
BACKEND = os.getenv("RERANK_BACKEND", "gemini")  # gemini | local
RETRIEVE_K = 8
RERANK_K = 3


class Relevance(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="0=irrelevant, 1=exactly answers the query")
    reason: str = Field(description="One short clause")


@dataclass
class Ranked:
    title: str
    content: str
    bi_distance: float
    ce_score: float
    reason: str = ""


def retrieve(query: str, k: int = RETRIEVE_K) -> list[tuple[str, str, float]]:
    return search(query, k=k)


def _score_gemini(query: str, chunk: str) -> tuple[float, str]:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY in .env")
    client = genai.Client(api_key=api_key)
    prompt = (
        "Score how well CHUNK answers QUERY. Joint relevance, not keyword overlap.\n"
        f"QUERY:\n{query}\n\nCHUNK:\n{chunk[:1200]}\n"
    )
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Relevance,
        ),
    )
    parsed = resp.parsed
    if parsed is None:
        parsed = Relevance.model_validate_json(resp.text)
    return float(parsed.score), parsed.reason


_local_model = None


def _score_local(query: str, chunk: str) -> tuple[float, str]:
    """ms-marco MiniLM cross-encoder. First call downloads ~80MB."""
    global _local_model
    if _local_model is None:
        from sentence_transformers import CrossEncoder

        _local_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    score = float(_local_model.predict([(query, chunk[:1200])])[0])
    return score, "local MiniLM logit (higher=more relevant)"


def rerank(
    query: str,
    hits: list[tuple[str, str, float]],
    top_k: int = RERANK_K,
    backend: str = BACKEND,
) -> list[Ranked]:
    scorer = _score_local if backend == "local" else _score_gemini
    ranked: list[Ranked] = []
    for title, content, dist in hits:
        score, reason = scorer(query, content)
        ranked.append(
            Ranked(
                title=title,
                content=content,
                bi_distance=dist,
                ce_score=score,
                reason=reason,
            )
        )
    ranked.sort(key=lambda r: r.ce_score, reverse=True)
    return ranked[:top_k]


def search_reranked(query: str, retrieve_k: int = RETRIEVE_K, top_k: int = RERANK_K) -> list[Ranked]:
    hits = retrieve(query, k=retrieve_k)
    return rerank(query, hits, top_k=top_k)


def main() -> None:
    query = " ".join(sys.argv[1:]) or (
        "How did EdusmarkAI scale live student progress over SSE?"
    )
    print(f"QUERY: {query}")
    print(f"backend={BACKEND}  retrieve_k={RETRIEVE_K}  rerank_k={RERANK_K}\n")

    t0 = time.perf_counter()
    hits = retrieve(query, k=RETRIEVE_K)
    bi_ms = (time.perf_counter() - t0) * 1000

    print(f"=== bi-encoder top-{len(hits)} ({bi_ms:.0f} ms) ===")
    for i, (title, content, dist) in enumerate(hits, 1):
        preview = content.replace("\n", " ")[:90]
        print(f"{i}. dist={dist:.4f}  {title}  | {preview}")

    t1 = time.perf_counter()
    ranked = rerank(query, hits, top_k=RERANK_K)
    ce_ms = (time.perf_counter() - t1) * 1000

    print(f"\n=== cross-encoder top-{len(ranked)} ({ce_ms:.0f} ms) ===")
    for i, r in enumerate(ranked, 1):
        preview = r.content.replace("\n", " ")[:90]
        print(
            f"{i}. ce={r.ce_score:.3f}  bi_dist={r.bi_distance:.4f}  {r.title}\n"
            f"    {r.reason}\n    {preview}"
        )
    print(
        "\nRead: bi-encoder is cheap ANN. Cross-encoder reorders using the pair. "
        "Skip rerank when retrieve_k is tiny, latency SLO is tight, or top-1 is already obvious."
    )


if __name__ == "__main__":
    main()
