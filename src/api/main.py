"""Day 13 — FastAPI SSE endpoint streaming agent tokens.

Contrast with EdusmarkAI SSE:
  EdusmarkAI: many clients, Redis pub/sub fanout, Celery publishes events,
              uvicorn workers subscribe — multi-process / multi-user bus.
  This file:  one HTTP request owns one LLM stream in-process. No Redis.
              Fine for demos / single-worker. Multi-worker needs the bus back.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

load_dotenv()

if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "google:gemini-3.5-flash-lite")
# pydantic-ai expects provider prefix
if ":" not in MODEL and not MODEL.startswith("google"):
    MODEL = f"google:{MODEL}"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class StreamDeps:
    """Optional retrieval — keep deps injectable like Day 3."""

    def search(self, query: str) -> str:
        try:
            from src.rag.search import search

            hits = search(query, k=2)
            if hits:
                return "\n---\n".join(f"{t}: {c[:400]}" for t, c, _ in hits)
        except Exception as e:
            return f"search unavailable: {type(e).__name__}: {e}"
        return "no matches"


agent = Agent(
    MODEL,
    deps_type=StreamDeps,
    instructions=(
        "You answer questions about the user's engineering notes. "
        "Call search_notes when you need facts. Stream a clear final answer."
    ),
)


@agent.tool
def search_notes(ctx: RunContext[StreamDeps], query: str) -> str:
    """Search engineering notes by query."""
    return ctx.deps.search(query)


app = FastAPI(title="rag-agent", version="0.13.0")


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def token_events(message: str) -> AsyncIterator[str]:
    """Yield SSE frames: meta, token deltas, done / error."""
    yield _sse({"type": "meta", "model": MODEL})
    try:
        async with agent.run_stream(message, deps=StreamDeps()) as result:
            async for text in result.stream_text(delta=True):
                if text:
                    yield _sse({"type": "token", "text": text})
        yield _sse({"type": "done"})
    except Exception as e:
        yield _sse({"type": "error", "message": f"{type(e).__name__}: {e}"})
        yield _sse({"type": "done"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        token_events(body.message),
        media_type="text/event-stream",
        headers={
            # Disable proxy buffering (nginx etc.) so tokens flush live.
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main() -> None:
    import uvicorn

    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
