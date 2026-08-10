"""Day 7 — Three chunkers for RAG.

1. NaiveChunker        — fixed character windows (brittle, still a baseline)
2. ParagraphChunker    — split on structure, pack to a size budget
3. ContextualChunker   — Anthropic Contextual Retrieval: LLM writes a short
                         situating prefix per chunk, then you embed prefix+chunk

Late chunking (embed full doc, then derive chunk vectors) is vocabulary-only
here — different technique, not implemented in this file.
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai

load_dotenv()

CONTEXT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


@dataclass(frozen=True)
class Chunk:
    text: str
    index: int
    strategy: str


class Chunker(ABC):
    name: str

    @abstractmethod
    def split(self, document: str) -> list[Chunk]:
        ...


class NaiveChunker(Chunker):
    """Fixed-size windows. Will bisect sentences and code blocks mid-line."""

    name = "naive"

    def __init__(self, size: int = 500, overlap: int = 50) -> None:
        if overlap >= size:
            raise ValueError("overlap must be < size")
        self.size = size
        self.overlap = overlap

    def split(self, document: str) -> list[Chunk]:
        text = document.strip()
        if not text:
            return []
        chunks: list[Chunk] = []
        start = 0
        i = 0
        while start < len(text):
            end = min(start + self.size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(Chunk(text=piece, index=i, strategy=self.name))
                i += 1
            if end == len(text):
                break
            start = end - self.overlap
        return chunks


class ParagraphChunker(Chunker):
    """Split on blank lines, then pack paragraphs into ~max_chars windows."""

    name = "paragraph"

    def __init__(self, max_chars: int = 800) -> None:
        self.max_chars = max_chars

    def split(self, document: str) -> list[Chunk]:
        paras = [p.strip() for p in re.split(r"\n\s*\n", document.strip()) if p.strip()]
        if not paras:
            return []

        packed: list[str] = []
        buf = ""
        for p in paras:
            # Oversized single paragraph: fall back to naive slices of that para.
            if len(p) > self.max_chars:
                if buf:
                    packed.append(buf)
                    buf = ""
                for c in NaiveChunker(size=self.max_chars, overlap=80).split(p):
                    packed.append(c.text)
                continue
            candidate = f"{buf}\n\n{p}".strip() if buf else p
            if len(candidate) <= self.max_chars:
                buf = candidate
            else:
                packed.append(buf)
                buf = p
        if buf:
            packed.append(buf)

        return [
            Chunk(text=t, index=i, strategy=self.name) for i, t in enumerate(packed)
        ]


class ContextualChunker(Chunker):
    """Paragraph chunks + LLM-generated situating context prepended to each.

    Embed `context + chunk`, not the raw chunk alone. Costs 1 LLM call per chunk
    at ingest. Retrieval quality usually rises; bill and latency rise too.
    """

    name = "contextual"

    def __init__(self, max_chars: int = 800, model: str = CONTEXT_MODEL) -> None:
        self.base = ParagraphChunker(max_chars=max_chars)
        self.model = model

    def split(self, document: str) -> list[Chunk]:
        base_chunks = self.base.split(document)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("Set GEMINI_API_KEY in .env")
        client = genai.Client(api_key=api_key)
        use_stub = os.getenv("CONTEXTUAL_STUB", "").lower() in {"1", "true", "yes"}

        out: list[Chunk] = []
        for c in base_chunks:
            if use_stub:
                context = (
                    f"[STUB CONTEXT] Chunk {c.index} from the engineering document "
                    f"(section inferred from nearby headings)."
                )
            else:
                prompt = (
                    "Here is a full engineering document, and one chunk from it.\n"
                    "Write 1-2 sentences of context that situate the chunk within the document "
                    "(what topic/section it belongs to). Do NOT repeat the chunk. "
                    "No preamble.\n\n"
                    f"DOCUMENT:\n{document}\n\nCHUNK:\n{c.text}\n"
                )
                try:
                    resp = client.models.generate_content(
                        model=self.model, contents=prompt
                    )
                    context = (resp.text or "").strip()
                except Exception as e:
                    # Free-tier 429 is common; don't block the day — show the shape.
                    print(
                        f"[warn] contextual LLM failed ({type(e).__name__}: {e}); "
                        f"using stub prefix. Set GEMINI_MODEL to a model with quota, "
                        f"or CONTEXTUAL_STUB=1 to skip the API."
                    )
                    context = (
                        f"[STUB CONTEXT] Chunk {c.index} from the engineering document "
                        f"(section inferred from nearby headings)."
                    )
            enriched = f"{context}\n\n{c.text}" if context else c.text
            out.append(Chunk(text=enriched, index=c.index, strategy=self.name))
        return out


SAMPLE_DOC = """
# Realtime assessment fanout at EdusmarkAI

## Problem
Teachers trigger bulk assessment generation. Students need live progress.
A single Django worker holding SSE sockets died past a few hundred connections.

## Design
We put Redis pub/sub in front of uvicorn workers. On connect, each worker
subscribes to `user:{id}`. Celery tasks publish progress events. If a corporate
proxy buffers SSE, clients fall back to DB polling every 3s keyed by last_event_id.

## Celery topology
Five queues. High-priority for interactive paths, background for bulk PDF/OCR.
acks_late=True, prefetch=1 so a killed worker redelivers safely.

## Failure modes
- Redis blip: clients reconnect; events are idempotent by event_id.
- DB poll fallback is slower but correct.
- Never put S3 downloads inside the DB transaction.
""".strip()


def demo() -> None:
    doc = SAMPLE_DOC
    chunkers: list[Chunker] = [
        NaiveChunker(size=500, overlap=50),
        ParagraphChunker(max_chars=800),
        ContextualChunker(max_chars=800),
    ]
    for chunker in chunkers:
        chunks = chunker.split(doc)
        print(f"\n=== {chunker.name}: {len(chunks)} chunks ===")
        for c in chunks:
            preview = c.text.replace("\n", " ")[:160]
            print(f"[{c.index}] ({len(c.text)} chars) {preview}...")


if __name__ == "__main__":
    demo()
