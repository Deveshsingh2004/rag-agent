-- Day 5 schema. No index yet — sequential scan for ORDER BY embedding <=> query.
CREATE EXTENSION IF NOT EXISTS vector;

DROP TABLE IF EXISTS notes;
CREATE TABLE notes (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    embedding   vector(768) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
