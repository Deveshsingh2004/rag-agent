# Deploy (Railway / Render)

Local demo is `docker compose up --build`. Public URL is optional for the GitHub pin.

## What you must have

- `GEMINI_API_KEY`
- Postgres **with pgvector** (`CREATE EXTENSION vector`)
- Redis Stack if you use semantic cache (`FT.SEARCH` KNN) — plain Redis will not work
- `DATABASE_URL`, `REDIS_URL`

## Railway (recommended over Render for this stack)

1. New project → deploy from `https://github.com/Deveshsingh2004/rag-agent`
2. Add **PostgreSQL**. In a query console: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Add **Redis**. If it’s not Redis Stack, skip semantic cache or use a Stack image.
4. Service env: `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `GOOGLE_API_KEY` (same as Gemini key)
5. Dockerfile is at repo root. Health: `GET /health`
6. After first deploy, run ingest once (Railway one-off):

```bash
python -m src.rag.ingest
```

Paste the public URL into the README **Live** line.

## Render

Same idea: Web Service from Dockerfile + Postgres. Enable pgvector on the DB. Free web services spin down — first request will be slow. Fine for a demo link, bad for interviews if it cold-starts 60s.

## Honest constraint

Do not claim a live URL you do not have. Compose-up + `/health` + `/chat` SSE is a valid Day 21 demo if Railway is still provisioning.
