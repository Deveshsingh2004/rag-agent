"""Day 5 — Ingest notes: embed with Gemini, store in Postgres vector(768). No index yet."""

from __future__ import annotations

from pathlib import Path

from src.rag.db import embed_texts, get_conn

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"

SAMPLE_NOTES = [
    {
        "slug": "sse-fanout",
        "title": "SSE fanout at scale",
        "content": (
            "SSE fanout at 50k concurrent: Redis pub/sub as bus, uvicorn workers "
            "subscribe on connect, DB-poll fallback for buffered proxies. "
            "Load-tested to 2k concurrent, architected for 50k."
        ),
    },
    {
        "slug": "celery-queues",
        "title": "Celery queue design",
        "content": (
            "5 Celery queues at EdusmarkAI, acks_late=True, prefetch=1, "
            "HP + BG queues for assessment pipeline. Idempotent tasks for side effects."
        ),
    },
    {
        "slug": "pgvector-hnsw",
        "title": "pgvector HNSW basics",
        "content": (
            "pgvector HNSW: cosine distance operator <=> , ef_construction at build time, "
            "ef_search at query time for recall vs latency tradeoff."
        ),
    },
    {
        "slug": "django-rbac",
        "title": "Multi-tenant RBAC",
        "content": (
            "Multi-tenant auth with 9-role RBAC, JWT HttpOnly cookies, refresh rotation, "
            "blacklist, custom DRF permission classes per org."
        ),
    },
    {
        "slug": "ocr-pipeline",
        "title": "Medical form OCR",
        "content": (
            "OCR medical forms with Gemini Vision, ThreadPoolExecutor for parallel LLM calls, "
            "OpenCV preprocess, HITL review UI, ~95% on 200+ forms."
        ),
    },
]


def reset_schema(conn) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)
    conn.commit()


def ingest(notes: list[dict[str, str]] | None = None) -> int:
    notes = notes or SAMPLE_NOTES
    with get_conn() as conn:
        reset_schema(conn)
        texts = [n["content"] for n in notes]
        vectors = embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")
        with conn.cursor() as cur:
            for note, vec in zip(notes, vectors, strict=True):
                assert len(vec) == 768, f"expected 768-dim, got {len(vec)}"
                cur.execute(
                    """
                    INSERT INTO notes (slug, title, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (note["slug"], note["title"], note["content"], vec),
                )
        conn.commit()
    return len(notes)


def main() -> None:
    n = ingest()
    print(f"ingested {n} notes into notes(embedding vector(768)) — no index yet")


if __name__ == "__main__":
    main()
