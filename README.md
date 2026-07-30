# RAG Agent over Engineering Notes

Pydantic AI agent + pgvector + MCP server + FastAPI SSE + Redis semantic cache + Langfuse traces + LLM-as-judge evals.

Built over 21 days as one project. See `CURRICULUM.md` for the day-by-day log.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# edit .env: put your Gemini API key
```

## Run Day 1

```powershell
python -m src.extractors.note_metadata
```

## Architecture

_(fills in as the project grows)_
