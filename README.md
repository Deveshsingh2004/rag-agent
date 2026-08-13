# RAG Agent over Engineering Notes

Pydantic AI + pgvector (HNSW) + MCP + FastAPI SSE + Redis semantic cache + Langfuse + LLM-as-judge evals.

21-day build. Log: [`CURRICULUM.md`](CURRICULUM.md). Mocks: [`interviews/`](interviews/).

**Live:** _add Railway/Render URL here after deploy_ — local: `http://127.0.0.1:8000`

## One-command local

```powershell
copy .env.example .env
# set GEMINI_API_KEY in .env
docker compose up --build -d
docker compose exec api python -m src.rag.ingest
```

```powershell
curl.exe -N -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" --data-raw "{\"message\":\"How did SSE scale with Redis?\"}"
```

`GET /health` → `{"status":"ok"}`.

Public deploy: [`docs/deploy.md`](docs/deploy.md).

## Architecture

```
Browser / curl
    │  POST /chat  (SSE token stream)
    ▼
FastAPI (uvicorn)
    │  optional Redis semantic cache (KNN + user TAG)
    ▼
Agent (Pydantic AI / LangGraph / MCP tools)
    │  search_notes / ingest_note
    ▼
Postgres + pgvector HNSW  (cosine <=>)
    ▲
Ingest: markdown → paragraph chunk → embed → index
```

**Query path (prod shape):** cache → bi-encoder retrieve → cross-encoder rerank → agent → SSE.  
**Ingest:** batch/Celery, not inside the request.  
**Multi-worker SSE:** Redis pub/sub per `user:{id}` (EdusmarkAI pattern).

## Day-by-day entrypoints

| Area | Command |
|---|---|
| Structured outputs | `python -m src.extractors.note_metadata` |
| Raw tool loop | `python -m src.agents.raw_tool_loop` |
| Pydantic AI + TestModel | `python -m src.agents.notes_agent` / `pytest tests/test_agent.py -v` |
| Ingest + search | `python -m src.rag.ingest` / `python -m src.rag.search "..."` |
| HNSW bench | `python scripts/bench_hnsw.py` |
| Chunkers | `python -m src.rag.chunkers` |
| ReAct / LangGraph / supervisor | `python -m src.agents.react_scratch` / `react_langgraph` / `supervisor` |
| SSE API | `python -m src.api.main` |
| Context trim | `python -m src.agents.history` |
| MCP server + agent | `python -m src.mcp.server --http` / `python -m src.agents.mcp_agent` |
| Semantic cache | `python -m src.cache.semantic` |
| Rerank | `python -m src.rag.rerank` |
| Evals | `python evals/rag_quality.py` |
| Langfuse demo | `python scripts/trace_demo.py` |

## Stack

Python, Gemini, Pydantic AI, LangGraph, pgvector, Redis Stack, FastAPI, MCP, Docker Compose.
