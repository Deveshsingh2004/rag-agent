"""Day 6 — HNSW bench: recall@k vs ef_search, plus p95 latency.

Why synthetic rows: 5 real notes cannot stress ANN. We keep any existing notes
and pad to N unit vectors so exact vs HNSW divergence is measurable.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

# `python scripts/bench_hnsw.py` does not add project root to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.rag.db import EMBED_DIM, get_conn

TARGET_ROWS = 2000
K = 10
EF_SWEEP = (10, 40, 100)
N_QUERIES = 30
M = 16
EF_CONSTRUCTION = 100


def _unit_vectors(n: int, dim: int = EMBED_DIM) -> list[list[float]]:
    rng = np.random.default_rng(42)
    mat = rng.standard_normal((n, dim), dtype=np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True)
    return mat.tolist()


def ensure_corpus(conn, n: int = TARGET_ROWS) -> int:
    count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    if count >= n:
        print(f"corpus already has {count} rows")
        return count

    need = n - count
    print(f"padding corpus: {count} -> {n} (+{need} synthetic unit vectors)")
    vecs = _unit_vectors(need)
    with conn.cursor() as cur:
        for i, vec in enumerate(vecs):
            slug = f"synth-{count + i:05d}"
            cur.execute(
                """
                INSERT INTO notes (slug, title, content, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (slug) DO NOTHING
                """,
                (slug, f"Synthetic {slug}", "synthetic padding for HNSW bench", vec),
            )
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]


def rebuild_hnsw(conn) -> float:
    conn.execute("DROP INDEX IF EXISTS notes_embedding_hnsw")
    conn.commit()
    t0 = time.perf_counter()
    conn.execute(
        f"""
        CREATE INDEX notes_embedding_hnsw
            ON notes
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = {M}, ef_construction = {EF_CONSTRUCTION})
        """
    )
    conn.commit()
    return time.perf_counter() - t0


def _as_float_list(vec) -> list[float]:
    # pgvector.Vector exposes to_list(); it is not a plain Python sequence.
    if hasattr(vec, "to_list"):
        return vec.to_list()
    return np.asarray(vec, dtype=np.float32).tolist()


def sample_query_vectors(conn, n: int) -> list[list[float]]:
    rows = conn.execute(
        "SELECT embedding FROM notes ORDER BY random() LIMIT %s",
        (n,),
    ).fetchall()
    return [_as_float_list(r[0]) for r in rows]


def exact_top_k(conn, qvec: list[float], k: int) -> list[int]:
    # SET LOCAL only lasts for this transaction — forces seq scan = exact neighbors.
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SET LOCAL enable_indexscan = off")
            cur.execute("SET LOCAL enable_bitmapscan = off")
            cur.execute(
                """
                SELECT id FROM notes
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, k),
            )
            return [r[0] for r in cur.fetchall()]


def hnsw_top_k(conn, qvec: list[float], k: int, ef_search: int) -> tuple[list[int], float]:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(f"SET LOCAL hnsw.ef_search = {int(ef_search)}")
            t0 = time.perf_counter()
            cur.execute(
                """
                SELECT id FROM notes
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qvec, k),
            )
            ids = [r[0] for r in cur.fetchall()]
            elapsed_ms = (time.perf_counter() - t0) * 1000
    return ids, elapsed_ms


def recall_at_k(truth: list[int], pred: list[int]) -> float:
    if not truth:
        return 0.0
    return len(set(truth) & set(pred)) / len(truth)


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    return float(np.percentile(xs, p))


def main() -> None:
    with get_conn() as conn:
        # Table must exist from Day 5 ingest.
        exists = conn.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notes')"
        ).fetchone()[0]
        if not exists:
            raise SystemExit("notes table missing — run: python -m src.rag.ingest")

        total = ensure_corpus(conn, TARGET_ROWS)
        build_s = rebuild_hnsw(conn)
        print(
            f"HNSW built on {total} rows "
            f"(m={M}, ef_construction={EF_CONSTRUCTION}) in {build_s:.2f}s\n"
        )

        queries = sample_query_vectors(conn, N_QUERIES)
        # Precompute exact ground truth once (expensive; that's the point).
        print(f"computing exact top-{K} for {len(queries)} queries (seq scan)...")
        truths = [exact_top_k(conn, q, K) for q in queries]

        print(f"{'ef_search':>10}  {'recall@'+str(K):>10}  {'p50_ms':>8}  {'p95_ms':>8}  {'mean_ms':>8}")
        for ef in EF_SWEEP:
            recalls: list[float] = []
            latencies: list[float] = []
            for q, truth in zip(queries, truths, strict=True):
                pred, ms = hnsw_top_k(conn, q, K, ef)
                recalls.append(recall_at_k(truth, pred))
                latencies.append(ms)
            print(
                f"{ef:>10}  {statistics.mean(recalls):>10.3f}  "
                f"{percentile(latencies, 50):>8.2f}  "
                f"{percentile(latencies, 95):>8.2f}  "
                f"{statistics.mean(latencies):>8.2f}"
            )

        print(
            "\nRead: higher ef_search → recall@k rises toward 1.0, latency rises. "
            "HNSW never promises exact neighbors — only a tunable approximation."
        )


if __name__ == "__main__":
    main()
