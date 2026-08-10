-- Day 6 — HNSW index for cosine distance.
-- Op class MUST match the operator you query with (<=> → vector_cosine_ops).
--
-- m               : max edges per node in the graph (build quality / memory)
-- ef_construction : candidate list size while building (higher → better recall, slower build)
-- ef_search       : set at QUERY time via `SET hnsw.ef_search = N` (higher → better recall, slower query)

CREATE INDEX IF NOT EXISTS notes_embedding_hnsw
    ON notes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);
