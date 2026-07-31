"""Day 3 — Same tools as Day 2, but as a Pydantic AI agent.

What the framework buys you over raw_tool_loop.py:
  - deps_type     : typed dependency injection (no globals / FAKE_NOTES module constant)
  - @agent.tool   : schema from type hints + docstring (no hand-written FunctionDeclaration)
  - output_type   : structured final answer (Day 1 constrained decoding, applied to the agent)
  - TestModel     : offline unit tests with zero API cost (see tests/test_agent.py)
"""

from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

load_dotenv()

# MODEL = "gemini-3.1-pro-preview"  #For Complex Agentic AI Learning
MODEL = "google:gemini-3.6-flash"

@dataclass
class NotesDeps:
    """Runtime deps injected per run. Swap the corpus in tests without touching tools."""

    notes: dict[str, str] = field(
        default_factory=lambda: {
            "sse": (
                "SSE fanout at 50k concurrent: Redis pub/sub as bus, uvicorn workers "
                "subscribe on connect, DB-poll fallback for buffered proxies."
            ),
            "celery": (
                "5 Celery queues at EdusmarkAI, acks_late=True, prefetch=1, "
                "HP + BG queues for assessment pipeline."
            ),
            "pgvector": (
                "pgvector HNSW: cosine <=> distance, ef_construction=200 build-time, "
                "ef_search=40 for recall/latency tradeoff."
            ),
        }
    )


class NotesAnswer(BaseModel):
    summary: str = Field(description="One-paragraph answer grounded in the notes")
    date: str = Field(description="ISO date YYYY-MM-DD from get_current_date")
    sources_used: list[str] = Field(description="Keywords that matched in search_notes")


agent = Agent(
    MODEL,
    deps_type=NotesDeps,
    output_type=NotesAnswer,
    instructions=(
        "You answer questions about the user's engineering notes. "
        "Always call search_notes for factual content. "
        "Always call get_current_date when the user asks for today's date. "
        "Return a NotesAnswer."
    ),
)


@agent.tool
def search_notes(ctx: RunContext[NotesDeps], query: str) -> str:
    """Search the engineering notes corpus by keyword. Returns matching note contents."""
    q = query.lower()
    hits = [note for key, note in ctx.deps.notes.items() if key in q]
    return "\n".join(hits) if hits else "no matches"


@agent.tool_plain
def get_current_date() -> str:
    """Get today's date in ISO format (YYYY-MM-DD). No arguments."""
    return dt.date.today().isoformat()


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")

    # Pydantic AI Google provider reads GOOGLE_API_KEY by default.
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    prompt = (
        "Look up what I wrote about SSE and about pgvector, and tell me what today's date is. "
        "Give me a one-paragraph summary of both notes plus the date."
    )
    result = agent.run_sync(prompt, deps=NotesDeps())
    print(result.output.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
