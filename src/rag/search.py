"""Day 5 — Raw vector search with cosine distance. Sequential scan (no HNSW yet)."""

from __future__ import annotations

import sys

from src.rag.db import embed_texts, get_conn


def search(query: str, k: int = 3) -> list[tuple[str, str, float]]:
    """Return top-k (title, content, distance) by cosine distance <=> ."""
    [qvec] = embed_texts([query], task_type="RETRIEVAL_QUERY")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT title, content, embedding <=> %s::vector AS distance
            FROM notes
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, k),
        )
        return [(row[0], row[1], float(row[2])) for row in cur.fetchall()]


def main() -> None:
    query = " ".join(sys.argv[1:]) or "how do I scale server-sent events with redis?"
    print(f"QUERY: {query}\n")
    hits = search(query, k=3)
    for i, (title, content, dist) in enumerate(hits, 1):
        print(f"--- hit {i}  distance={dist:.4f} ---")
        print(f"title  : {title}")
        print(f"content: {content}\n")


if __name__ == "__main__":
    main()
