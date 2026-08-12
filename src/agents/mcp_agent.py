"""Day 16 — Pydantic AI agent that consumes Day 15 MCP tools over HTTP.

The agent has ZERO local @agent.tool definitions for notes.
Tools come from the MCP server at http://127.0.0.1:8100/mcp.

Requires Terminal A: python -m src.mcp.server --http
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from pydantic_ai import Agent

load_dotenv()

if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "google:gemini-3.5-flash-lite")
if ":" not in MODEL:
    MODEL = f"google:{MODEL}"

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8100/mcp")


def _build_toolset():
    """Prefer MCPToolset (current); fall back to MCPServerStreamableHTTP (older PAI)."""
    try:
        from pydantic_ai.mcp import MCPToolset

        return MCPToolset(MCP_URL)
    except ImportError:
        from pydantic_ai.mcp import MCPServerStreamableHTTP

        return MCPServerStreamableHTTP(MCP_URL)


async def main() -> None:
    toolset = _build_toolset()
    agent = Agent(
        MODEL,
        toolsets=[toolset],
        instructions=(
            "You answer using MCP tools only. "
            "Call search_notes for facts from engineering notes. "
            "Be concise."
        ),
    )

    prompt = (
        "Using search_notes, what did I write about scaling SSE with Redis, "
        "and which HNSW knob is query-time for recall vs latency?"
    )
    print(f"USER: {prompt}\nMCP: {MCP_URL}\n")

    # Some PAI versions need the toolset/server entered as an async context.
    enter = getattr(toolset, "__aenter__", None)
    if enter is not None:
        async with toolset:
            result = await agent.run(prompt)
    else:
        result = await agent.run(prompt)

    print("=== ANSWER ===")
    print(result.output)

    # Show which tools were used (if message history exposes them).
    try:
        from pydantic_ai.messages import ToolCallPart

        print("\n=== TOOL CALLS (from history) ===")
        found = False
        for msg in result.all_messages():
            for part in getattr(msg, "parts", []) or []:
                if isinstance(part, ToolCallPart) or type(part).__name__ == "ToolCallPart":
                    print(f"- {getattr(part, 'tool_name', part)} {getattr(part, 'args', '')}")
                    found = True
        if not found:
            print("(none listed — check server logs for tools/call)")
    except Exception as e:
        print(f"(could not print tool calls: {type(e).__name__}: {e})")


if __name__ == "__main__":
    asyncio.run(main())
