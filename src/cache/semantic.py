"""Day 17 — Redis semantic cache (vector KNN + per-user TAG filter).

Exact-string cache misses on paraphrase ("scale SSE" vs "SSE fanout Redis").
Semantic cache embeds the prompt, FT.SEARCH KNN nearest neighbor, returns
cached answer if distance <= threshold AND user_id TAG matches.

Requires Redis Stack (RediSearch), not plain redis:alpine — see docker-compose.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

import numpy as np
import redis
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from src.rag.db import EMBED_DIM, embed_texts

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
INDEX = os.getenv("SEMANTIC_CACHE_INDEX", "rag_semcache")
PREFIX = "semcache:"
# Cosine distance in Redis VECTOR: lower = closer. Tune per embed model.
DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.15"))


def _to_bytes(vec: list[float]) -> bytes:
    arr = np.asarray(vec, dtype=np.float32)
    return arr.tobytes()


@dataclass
class CacheHit:
    answer: str
    distance: float
    prompt: str
    user_id: str


class SemanticCache:
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        index: str = INDEX,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.r = redis.from_url(redis_url, decode_responses=False)
        self.index = index
        self.threshold = threshold
        self.ensure_index()

    def ensure_index(self) -> None:
        try:
            self.r.ft(self.index).info()
            return
        except Exception:
            pass
        schema = (
            TextField("prompt"),
            TextField("answer"),
            TagField("user_id"),
            VectorField(
                "embedding",
                "HNSW",
                {
                    "TYPE": "FLOAT32",
                    "DIM": EMBED_DIM,
                    "DISTANCE_METRIC": "COSINE",
                },
            ),
        )
        definition = IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH)
        self.r.ft(self.index).create_index(schema, definition=definition)

    def _key(self, user_id: str, prompt: str) -> str:
        h = hashlib.sha256(f"{user_id}|{prompt}".encode()).hexdigest()[:24]
        return f"{PREFIX}{user_id}:{h}"

    def set(self, prompt: str, answer: str, *, user_id: str) -> str:
        [vec] = embed_texts([prompt], task_type="RETRIEVAL_QUERY")
        key = self._key(user_id, prompt)
        self.r.hset(
            key,
            mapping={
                "prompt": prompt.encode(),
                "answer": answer.encode(),
                "user_id": user_id.encode(),
                "embedding": _to_bytes(vec),
            },
        )
        return key

    def get(self, prompt: str, *, user_id: str, k: int = 3) -> CacheHit | None:
        [qvec] = embed_texts([prompt], task_type="RETRIEVAL_QUERY")
        # TAG filter scopes tenants; KNN finds nearest prompt embedding.
        q = (
            Query(f"(@user_id:{{{user_id}}})=>[KNN {k} @embedding $vec AS score]")
            .return_fields("prompt", "answer", "user_id", "score")
            .sort_by("score")
            .dialect(2)
        )
        res = self.r.ft(self.index).search(
            q, query_params={"vec": _to_bytes(qvec)}
        )
        if not res.docs:
            return None
        doc = res.docs[0]
        score = float(doc.score)  # cosine distance from RediSearch
        if score > self.threshold:
            return None
        return CacheHit(
            answer=doc.answer if isinstance(doc.answer, str) else doc.answer.decode(),
            distance=score,
            prompt=doc.prompt if isinstance(doc.prompt, str) else doc.prompt.decode(),
            user_id=doc.user_id if isinstance(doc.user_id, str) else doc.user_id.decode(),
        )


def main() -> None:
    cache = SemanticCache()
    user = "devesh"
    other = "alice"

    cache.set(
        "How did SSE scale with Redis at EdusmarkAI?",
        "Redis pub/sub fanout; uvicorn subscribe user:{id}; DB poll fallback.",
        user_id=user,
    )
    # Paraphrase — should HIT for same user
    hit = cache.get("Explain scaling server-sent events using Redis pub/sub", user_id=user)
    print("same-user paraphrase:", hit)

    # Same paraphrase, different user — must MISS (TAG isolation)
    miss = cache.get(
        "Explain scaling server-sent events using Redis pub/sub", user_id=other
    )
    print("other-user paraphrase:", miss)

    assert hit is not None, "expected semantic hit for same user"
    assert miss is None, "expected TAG isolation miss for other user"
    print("OK — semantic hit + per-user TAG isolation")


if __name__ == "__main__":
    main()
