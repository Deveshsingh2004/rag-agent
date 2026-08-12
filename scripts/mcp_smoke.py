"""Day 15 smoke test — list + call MCP tools over streamable HTTP.

Requires: docker postgres up, notes ingested, and:
  python -m src.mcp.server --http
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = "http://127.0.0.1:8100/mcp"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [t.name for t in tools.tools])
            result = await session.call_tool(
                "search_notes", {"query": "SSE Redis pub/sub"}
            )
            print("search_notes result:")
            for block in result.content:
                text = getattr(block, "text", None) or str(block)
                print(text[:800])


if __name__ == "__main__":
    asyncio.run(main())
