# 21-Day Curriculum Log

Progress tracker. Each day = one commit + one row filled in.

| Day | Topic | Status | Commit |
|---|---|---|---|
| 1 | Structured Outputs (Gemini `response_schema` → Pydantic) | done — borderline | [3a5d7e5](https://github.com/Deveshsingh2004/rag-agent/commit/3a5d7e5) |
| 2 | Raw Tool Calling | done — pass (weak on Q3: agent-as-actor threat model) | [a0b7b7a](https://github.com/Deveshsingh2004/rag-agent/commit/a0b7b7a) |
| 3 | Pydantic AI (agent, tools, deps, TestModel) | done — pass (Q2 soft on what TestModel actually does) | [b4d0674](https://github.com/Deveshsingh2004/rag-agent/commit/b4d0674) |
| 4 | MOCK #1 + repo scaffolding polish | done — PASS | [8de1b0a](https://github.com/Deveshsingh2004/rag-agent/commit/8de1b0a) |
| 5 | Embeddings + pgvector basics | done — pass (Q1 soft on when to pick metric) | [0fd313f](https://github.com/Deveshsingh2004/rag-agent/commit/0fd313fcc23af43ba03bbb5223a7f04779ce3621) |
| 6 | HNSW indexing tuning | done — borderline (latency myth on Q1; m confused with ef on Q3) | [ee6a8ea](https://github.com/Deveshsingh2004/rag-agent/commit/ee6a8ea) |
| 7 | Chunking strategies | done — pass (Q2 soft on late-chunking mechanism) | [9fd88bb](https://github.com/Deveshsingh2004/rag-agent/commit/9fd88bb) |
| 8 | MOCK #2 + ingest real notes | done — BORDERLINE (Q5 fail: Celery vs sync) | [e722d6c](https://github.com/Deveshsingh2004/rag-agent/commit/e722d6c) |
| 9 | ReAct loop from scratch | done — pass (Q1 soft; Q3 taught after gap) | [735bc3f](https://github.com/Deveshsingh2004/rag-agent/commit/735bc3f) |
| 10 | LangGraph port of ReAct | done — pass (Q2 soft: checkpointer ≠ long-term user prefs alone) | _pending push_ |
| 11 | Supervisor / routing pattern | pending | — |
| 12 | MOCK #3 | pending | — |
| 13 | FastAPI SSE streaming | pending | — |
| 14 | Context window management | pending | — |
| 15 | Build MCP server | pending | — |
| 16 | Consume MCP from Pydantic AI | pending | — |
| 17 | MOCK #4 + Redis semantic cache | pending | — |
| 18 | Cross-encoder reranking | pending | — |
| 19 | LLM-as-Judge evals | pending | — |
| 20 | Observability (Langfuse) | pending | — |
| 21 | Deploy + FINAL MOCK | pending | — |
