-- Day 8 schema: one row per chunk (RAG retrieval unit).
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS notes;
CREATE TABLE notes (
    id           BIGSERIAL PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,
    title        TEXT NOT NULL,
    content      TEXT NOT NULL,
    source_path  TEXT,
    chunk_index  INT NOT NULL DEFAULT 0,
    strategy     TEXT NOT NULL DEFAULT 'whole',
    embedding    vector(768) NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS notes_embedding_hnsw
    ON notes
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);
