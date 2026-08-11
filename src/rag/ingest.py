"""Day 8 — Ingest markdown notes from disk, paragraph-chunk, embed, HNSW index.

Usage:
  python -m src.rag.ingest
  python -m src.rag.ingest path/to/notes   # your Obsidian export / private notes
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from src.rag.chunkers import ParagraphChunker
from src.rag.db import embed_texts, get_conn

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
DEFAULT_NOTES_DIR = ROOT / "notes" / "sample"


def reset_schema(conn) -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.execute(sql)
    conn.commit()


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_markdown_notes(notes_dir: Path) -> list[dict[str, str]]:
    if not notes_dir.is_dir():
        raise SystemExit(f"notes dir not found: {notes_dir}")
    files = sorted(notes_dir.glob("**/*.md"))
    if not files:
        raise SystemExit(f"no .md files under {notes_dir}")
    notes: list[dict[str, str]] = []
    for path in files:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        stem = path.stem
        slug_base = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
        notes.append(
            {
                "slug_base": slug_base,
                "title": _title_from_markdown(text, stem),
                "content": text,
                "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return notes


def ingest_dir(notes_dir: Path, *, max_chars: int = 800) -> int:
    docs = load_markdown_notes(notes_dir)
    chunker = ParagraphChunker(max_chars=max_chars)
    rows: list[dict] = []
    for doc in docs:
        chunks = chunker.split(doc["content"])
        if not chunks:
            continue
        for c in chunks:
            rows.append(
                {
                    "slug": f"{doc['slug_base']}-{c.index}",
                    "title": doc["title"],
                    "content": c.text,
                    "source_path": doc["source_path"],
                    "chunk_index": c.index,
                    "strategy": c.strategy,
                }
            )

    texts = [r["content"] for r in rows]
    # Batch embed in groups of 20 to stay under API payload limits.
    vectors: list[list[float]] = []
    batch = 20
    for i in range(0, len(texts), batch):
        vectors.extend(
            embed_texts(texts[i : i + batch], task_type="RETRIEVAL_DOCUMENT")
        )

    with get_conn() as conn:
        reset_schema(conn)
        with conn.cursor() as cur:
            for row, vec in zip(rows, vectors, strict=True):
                assert len(vec) == 768, f"expected 768-dim, got {len(vec)}"
                cur.execute(
                    """
                    INSERT INTO notes
                        (slug, title, content, source_path, chunk_index, strategy, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        row["slug"],
                        row["title"],
                        row["content"],
                        row["source_path"],
                        row["chunk_index"],
                        row["strategy"],
                        vec,
                    ),
                )
        conn.commit()
    return len(rows)


def main() -> None:
    notes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NOTES_DIR
    n = ingest_dir(notes_dir)
    print(f"ingested {n} chunks from {notes_dir} (paragraph strategy + HNSW)")


if __name__ == "__main__":
    main()
