"""Day 20 — One traced agent run (Pydantic AI → Langfuse).

Usage:
  1. Create free project at https://cloud.langfuse.com
  2. Put pk/sk in .env (see .env.example)
  3. python -m scripts.trace_demo   (or: python scripts/trace_demo.py)

Then open Langfuse → Traces. Screenshot → docs/langfuse-trace.png (optional commit).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext

from src.observability import flush, instrument_agent

load_dotenv()

if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "google:gemini-3.5-flash-lite")
if ":" not in MODEL:
    MODEL = f"google:{MODEL}"


class RagDeps:
    pass


agent = Agent(
    MODEL,
    deps_type=RagDeps,
    instructions=(
        "Answer from engineering notes. Call search_notes for facts. Be concise."
    ),
)


@agent.tool
def search_notes(ctx: RunContext[RagDeps], query: str) -> str:
    """Search pgvector notes."""
    try:
        from src.rag.search import search

        hits = search(query, k=2)
        if hits:
            return "\n---\n".join(f"{t}: {c[:400]}" for t, c, _ in hits)
    except Exception as e:
        return f"search error: {type(e).__name__}: {e}"
    return "no matches"


def main() -> None:
    enabled = instrument_agent()
    prompt = (
        "How did EdusmarkAI scale SSE, and which HNSW knob is query-time "
        "for recall vs latency?"
    )
    print(f"USER: {prompt}\n")
    result = agent.run_sync(prompt, deps=RagDeps())
    print("=== ANSWER ===")
    print(result.output)
    flush()
    if enabled:
        print(
            "\nOpen https://cloud.langfuse.com → Traces. "
            "You should see this run: LLM spans, search_notes tool, latency, tokens. "
            "Save a screenshot as docs/langfuse-trace.png"
        )
    else:
        print("\nRe-run after adding Langfuse keys to see the trace tree.")


if __name__ == "__main__":
    main()
