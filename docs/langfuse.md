# Day 20 — Langfuse observability

## Setup

1. Free project: [cloud.langfuse.com](https://cloud.langfuse.com)
2. Project settings → API keys → `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`
3. `.env`:

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

US region: `https://us.cloud.langfuse.com`

4. Run:

```powershell
python scripts/trace_demo.py
```

5. UI → **Traces**. Screenshot → `docs/langfuse-trace.png` (optional commit).

## What to look at in a trace

| Signal | Why |
|---|---|
| Span tree (agent → LLM → tool) | Debug “why did it search twice?” |
| Latency per span | p95 alerts; rerank vs retrieve vs LLM |
| Token usage / cost | Budget; catch runaway ReAct loops |
| Tool I/O | Hallucination vs bad retrieval |

## Prod alerts (interview)

Alert on: error rate, p95 latency, cost/token spike, tool-failure rate.  
**Sampling:** do not export 100% of traces at 10k QPS — sample ~1–10%, plus 100% of errors and slow traces.

## Primary source

[Langfuse × Pydantic AI](https://langfuse.com/integrations/frameworks/pydantic-ai)
