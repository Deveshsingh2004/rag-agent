# pgvector retrieval notes

## Distance

For text embeddings use cosine distance `<=>` with `vector_cosine_ops` on the HNSW index.
Wrong op class vs query operator silently hurts recall.

## HNSW knobs

- `m` (~16 start): graph degree — RAM and build cost
- `ef_construction` (~64–200): build quality
- `ef_search` (query-time): recall vs latency dial — never leave at 1

## Chunking

Paragraph-aware chunking before embed. Contextual Retrieval (LLM prefix per chunk)
helps long multi-section notes; skip for short single-topic notes.
