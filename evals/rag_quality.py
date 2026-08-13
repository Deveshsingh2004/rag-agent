"""Day 19 — RAG evals: deterministic hit@k + LLM-as-judge.

Three judges (faithfulness, relevance, completeness).
Judge model SHOULD differ from the generator in prod — here both may be Gemini;
we still separate *roles* and call out collusion risk.

Deterministic check (no LLM): is the expected note title in top-k retrieve?
That's your cheap regression gate. LLM judges catch quality, not just ranking.
"""

from __future__ import annotations

import os
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from src.rag.search import search

load_dotenv()

if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

GEN_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Prod: use a *different* family than the generator. Same-family is a known bias.
JUDGE_MODEL = os.getenv("JUDGE_MODEL", GEN_MODEL)
K = 3


class JudgeScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="One sentence")


@dataclass(frozen=True)
class Case:
    name: str
    query: str
    expected_title: str  # substring match against retrieved titles
    must_cover: str  # facts the answer should include (for completeness judge)


CASES: list[Case] = [
    Case(
        "sse_scale",
        "How did EdusmarkAI scale live student progress over SSE?",
        "SSE fanout",
        "Redis pub/sub, uvicorn workers, DB poll fallback",
    ),
    Case(
        "sse_load",
        "What was the SSE load-test vs design target vs real peak?",
        "SSE fanout",
        "50k design, 2k load-tested, 2-5k real peak",
    ),
    Case(
        "celery_acks",
        "How are Celery tasks made reliable if a worker dies?",
        "Celery queues",
        "acks_late, prefetch=1, idempotent side effects",
    ),
    Case(
        "hnsw_query_knob",
        "Which HNSW knob tunes recall vs latency at query time?",
        "pgvector retrieval",
        "ef_search, not m or ef_construction",
    ),
    Case(
        "hnsw_op_class",
        "What goes wrong if HNSW op class does not match cosine search?",
        "pgvector retrieval",
        "wrong neighbors / silent recall drop, vector_cosine_ops with <=>",
    ),
    Case(
        "rbac_cookies",
        "Why JWT in HttpOnly cookies instead of localStorage?",
        "RBAC",
        "HttpOnly reduces XSS token theft",
    ),
    Case(
        "ocr_hitl",
        "What happens when medical OCR extraction is wrong?",
        "OCR",
        "HITL review, not silent DB write",
    ),
    Case(
        "chunking_when",
        "When is Contextual Retrieval worth the ingest cost?",
        "pgvector retrieval",
        "long multi-section notes; skip short single-topic notes",
    ),
]


def _client() -> genai.Client:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in .env")
    return genai.Client(api_key=key)


def retrieve_and_answer(query: str) -> dict:
    hits = search(query, k=K)
    context = "\n---\n".join(f"{t}\n{c}" for t, c, _ in hits) if hits else ""
    titles = [t for t, _, _ in hits]
    client = _client()
    prompt = (
        "Answer the question using ONLY the context. If missing, say you lack notes.\n"
        f"QUESTION:\n{query}\n\nCONTEXT:\n{context}\n"
    )
    resp = client.models.generate_content(model=GEN_MODEL, contents=prompt)
    answer = (resp.text or "").strip()
    return {"answer": answer, "context": context, "titles": titles}


def hit_at_k(titles: list[str], expected: str) -> bool:
    needle = expected.lower()
    return any(needle in t.lower() for t in titles)


def llm_judge(rubric: str, *, query: str, context: str, answer: str, extra: str = "") -> JudgeScore:
    client = _client()
    prompt = (
        f"You are an evaluator. Rubric: {rubric}\n"
        "Score 0.0 to 1.0. Be harsh: unsupported claims → low faithfulness.\n"
        f"QUERY:\n{query}\n\nCONTEXT:\n{context[:2500]}\n\nANSWER:\n{answer}\n"
        f"{extra}"
    )
    resp = client.models.generate_content(
        model=JUDGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JudgeScore,
        ),
    )
    if resp.parsed is not None:
        return resp.parsed
    return JudgeScore.model_validate_json(resp.text)


def main() -> None:
    print(f"gen={GEN_MODEL}  judge={JUDGE_MODEL}  k={K}  n={len(CASES)}\n")
    rows: list[dict] = []
    for case in CASES:
        print(f"--- {case.name} ---")
        try:
            out = retrieve_and_answer(case.query)
        except Exception as e:
            print(f"  FAIL generate: {type(e).__name__}: {e}")
            continue
        hit = hit_at_k(out["titles"], case.expected_title)
        try:
            faith = llm_judge(
                "Faithfulness: every claim in the answer is supported by CONTEXT. "
                "Hallucinated facts score near 0 even if they sound right.",
                query=case.query,
                context=out["context"],
                answer=out["answer"],
            )
            rel = llm_judge(
                "Relevance: the answer addresses the QUERY (not just related backend trivia).",
                query=case.query,
                context=out["context"],
                answer=out["answer"],
            )
            comp = llm_judge(
                "Completeness: the answer covers the required facts listed below.",
                query=case.query,
                context=out["context"],
                answer=out["answer"],
                extra=f"REQUIRED FACTS:\n{case.must_cover}\n",
            )
        except Exception as e:
            print(f"  FAIL judge: {type(e).__name__}: {e}")
            continue

        row = {
            "name": case.name,
            "hit@k": hit,
            "faith": faith.score,
            "rel": rel.score,
            "comp": comp.score,
        }
        rows.append(row)
        print(f"  titles: {out['titles']}")
        print(f"  hit@k={hit}  faith={faith.score:.2f}  rel={rel.score:.2f}  comp={comp.score:.2f}")
        print(f"  faith: {faith.reason}")
        print(f"  rel  : {rel.reason}")
        print(f"  comp : {comp.reason}")

    if not rows:
        raise SystemExit("no cases completed")

    print("\n=== SUMMARY ===")
    print(f"{'case':22} {'hit':>5} {'faith':>6} {'rel':>6} {'comp':>6}")
    for r in rows:
        print(
            f"{r['name']:22} {str(r['hit@k']):>5} {r['faith']:6.2f} {r['rel']:6.2f} {r['comp']:6.2f}"
        )
    hit_rate = sum(1 for r in rows if r["hit@k"]) / len(rows)
    print(
        f"\nhit@{K}={hit_rate:.2f}  "
        f"faith_mean={statistics.mean(r['faith'] for r in rows):.2f}  "
        f"rel_mean={statistics.mean(r['rel'] for r in rows):.2f}  "
        f"comp_mean={statistics.mean(r['comp'] for r in rows):.2f}"
    )
    print(
        "\nGates: hit@k is the cheap CI check. LLM judges are noisy — "
        "don't use the same model as generator without a second opinion. "
        "Human eval still required for medical/OCR-class answers."
    )


if __name__ == "__main__":
    main()
