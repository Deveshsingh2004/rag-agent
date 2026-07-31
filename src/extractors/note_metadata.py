"""Day 1 — Structured Outputs.

Two ways to extract structured metadata from a raw note:
  1. extract_naive       — prompt for JSON, json.loads, hope
  2. extract_structured  — Gemini response_schema + Pydantic, guaranteed shape
"""

from __future__ import annotations

import json
import os
from enum import Enum
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

# MODEL = "gemini-3.1-pro-preview"  #For Complex Agentic AI Learning
# MODEL = "gemini-3.5-flash"  #For Moderate Agentic Learning
MODEL = "gemini-3.5-flash-lite"  #For Data Extraction & High-Volume Tasks



class Category(str, Enum):
    backend = "backend"
    infra = "infra"
    frontend = "frontend"
    ai = "ai"
    other = "other"


class NoteMetadata(BaseModel):
    title: str = Field(description="Short human title, max 8 words")
    tags: list[str] = Field(description="3 to 6 lowercase kebab-case tags")
    category: Category
    summary: str = Field(description="One-sentence summary, <= 200 chars")
    has_code: bool = Field(description="True if the note contains code blocks or shell commands")


PROMPT = """Extract metadata from the following engineering note.

NOTE:
---
{note}
---
"""


def extract_naive(note: str) -> dict:
    """Approach 1: ask for JSON in the prompt. Parse manually. No schema enforcement."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = PROMPT.format(note=note) + (
        "\nReturn ONLY JSON with keys: title, tags, category, summary, has_code. "
        "No markdown, no code fences."
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.strip("`").lstrip("json").strip()
    return json.loads(text)


def extract_structured(note: str) -> NoteMetadata:
    """Approach 2: pass Pydantic class as response_schema. Gemini constrains output."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(note=note),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=NoteMetadata,
        ),
    )
    return response.parsed


def extract_structured_with_retry(note: str, max_retries: int = 2) -> NoteMetadata:
    """Production pattern: structured output can still fail validation on edge cases.
    Retry with the validation error fed back as feedback."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = PROMPT.format(note=note)
    last_error: str | None = None
    for attempt in range(max_retries + 1):
        contents = prompt if last_error is None else (
            prompt + f"\nPrevious attempt failed validation: {last_error}. Fix and retry."
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NoteMetadata,
            ),
        )
        try:
            if response.parsed is not None:
                return response.parsed
            return NoteMetadata.model_validate_json(response.text)
        except ValidationError as e:
            last_error = str(e)
    raise RuntimeError(f"extract_structured failed after {max_retries + 1} attempts: {last_error}")


SAMPLE_NOTE = """
# SSE fanout at 50k concurrent

Problem: single-worker Django + SSE doesn't scale past ~500 sockets.
Fix: Redis pub/sub as the fanout bus, uvicorn workers subscribe on connect,
push events from Celery workers via redis.publish(channel, json.dumps(payload)).

Fallback path: if the client is behind a proxy that buffers SSE, fall back to
DB polling every 3s with an ETag on the last_event_id column.

```python
async def event_stream(request):
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe(f"user:{request.user.id}")
        async for msg in pubsub.listen():
            yield f"data: {msg['data']}\\n\\n"
```

Load tested to 2k concurrent on a t3.medium. Architected for 50k with
horizontal uvicorn + Redis Cluster.
"""


def _print_result(label: str, result: dict | NoteMetadata) -> None:
    print(f"\n=== {label} ===")
    if isinstance(result, BaseModel):
        print(f"type       : {type(result).__name__}")
        print(f"title      : {result.title}")
        print(f"tags       : {result.tags}")
        print(f"category   : {result.category.value}")
        print(f"has_code   : {result.has_code}")
        print(f"summary    : {result.summary}")
    else:
        print(f"type       : {type(result).__name__}")
        print(f"raw dict   : {result}")


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in .env")

    print(">>> Naive extraction (prompt for JSON, parse by hand)")
    try:
        naive = extract_naive(SAMPLE_NOTE)
        _print_result("naive", naive)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"naive failed: {type(e).__name__}: {e}")

    print("\n>>> Structured extraction (response_schema=NoteMetadata)")
    structured = extract_structured(SAMPLE_NOTE)
    _print_result("structured", structured)

    print("\n>>> Structured with retry (production pattern)")
    safe = extract_structured_with_retry(SAMPLE_NOTE)
    _print_result("structured+retry", safe)


if __name__ == "__main__":
    main()


