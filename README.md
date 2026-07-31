# RAG Agent over Engineering Notes

Pydantic AI agent + pgvector + MCP + FastAPI SSE + Redis semantic cache + Langfuse + LLM-as-judge evals.

One repo, 21 days. Progress: `CURRICULUM.md`. Mock transcripts: `interviews/`.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# set GEMINI_API_KEY in .env
```

Infra (Days 5+):

```powershell
docker compose up -d
```

Brings up Postgres 16 + pgvector (`localhost:5432`, user/pass/db: `rag`) and Redis 7 (`localhost:6379`).

## What's built so far

| Day | Run |
|---|---|
| 1 Structured outputs | `python -m src.extractors.note_metadata` |
| 2 Raw tool loop | `python -m src.agents.raw_tool_loop` |
| 3 Pydantic AI agent | `python -m src.agents.notes_agent` |
| 3 Offline tests | `pytest tests/test_agent.py -v` |

## Architecture

```
[notes] -> extract (Day 1) -> agent tools (Days 2-3)
                              |
                         deps_type / output_type / TestModel
                              |
                    [pgvector ingest + search]  <- Days 5-8
                    [LangGraph / MCP / SSE / cache / evals] <- later
```
