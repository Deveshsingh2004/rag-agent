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
| 10 | LangGraph port of ReAct | done — pass (Q2 soft: checkpointer ≠ long-term user prefs alone) | [b5cb4a1](https://github.com/Deveshsingh2004/rag-agent/commit/b5cb4a1) |
| 11 | Supervisor / routing pattern | done — pass | [960403b](https://github.com/Deveshsingh2004/rag-agent/commit/960403b) |
| 12 | MOCK #3 | done — PASS (Q2 soft on when to prefer native tools) | [df6db62](https://github.com/Deveshsingh2004/rag-agent/commit/df6db62) |
| 13 | FastAPI SSE streaming | done — pass | [db0a901](https://github.com/Deveshsingh2004/rag-agent/commit/db0a901) |
| 14 | Context window management | done — pass (Q3 incomplete: only covered LastN test) | [6359dae](https://github.com/Deveshsingh2004/rag-agent/commit/6359daeaea83e7afd2002bf7042f7fbbfff0ef39) |
| 15 | Build MCP server | done — pass | [1d33a3b](https://github.com/Deveshsingh2004/rag-agent/commit/1d33a3b) |
| 16 | Consume MCP from Pydantic AI | done — pass (Q3 taught: amortize discovery) | [a7a22ba](https://github.com/Deveshsingh2004/rag-agent/commit/a7a22ba) |
| 17 | MOCK #4 + Redis semantic cache | done — PASS | _pending push_ |
| 18 | Cross-encoder reranking | done — borderline drill; run proved Celery demoted | [f3cfd4a](https://github.com/Deveshsingh2004/rag-agent/commit/f3cfd4a) |
| 19 | LLM-as-Judge evals | done — pass (same-model 1.00 scores = collusion demo) | [41adb95](https://github.com/Deveshsingh2004/rag-agent/commit/41adb95) |
| 20 | Observability (Langfuse) | done — PASS drill; UI skipped (no keys yet) | _pending push_ |
| 21 | Deploy + FINAL MOCK | pending | — |
