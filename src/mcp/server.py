"""Day 15 — MCP server exposing RAG tools.

MCP = Model Context Protocol: a standard way for hosts (Cursor, agents, IDEs)
to discover and call tools/resources — like OpenAPI, but designed for LLM tool use.

Transports:
  - stdio (default): host spawns this process, speaks JSON-RPC on stdin/stdout
  - streamable-http: long-lived HTTP endpoint for remote clients (Day 16 will consume)

Tools:
  - search_notes(query)
  - ingest_note(title, content, slug?)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "rag-notes",
    host="127.0.0.1",
    port=8100,
)


@mcp.tool()
def search_notes(query: str) -> str:
    """Semantic search over engineering notes in Postgres/pgvector. Returns top snippets."""
    from src.rag.search import search

    hits = search(query, k=3)
    if not hits:
        return "no matches"
    return "\n---\n".join(
        f"title={title}\ndistance={dist:.4f}\n{content[:500]}"
        for title, content, dist in hits
    )


@mcp.tool()
def ingest_note(title: str, content: str, slug: str | None = None) -> str:
    """Embed and insert one note chunk into the notes table (does not wipe existing rows)."""
    from src.rag.db import embed_texts, get_conn

    base = slug or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "note"
    slug_final = f"{base}-mcp"
    [vec] = embed_texts([content], task_type="RETRIEVAL_DOCUMENT")

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO notes (slug, title, content, source_path, chunk_index, strategy, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding
            """,
            (slug_final, title, content, "mcp:ingest_note", 0, "mcp", vec),
        )
        conn.commit()
    return f"upserted slug={slug_final} dim={len(vec)}"


def main() -> None:
    if "--http" in sys.argv:
        print("MCP streamable-http on http://127.0.0.1:8100/mcp", flush=True)
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
