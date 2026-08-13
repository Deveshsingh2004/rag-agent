"""Langfuse / OTel wiring for Pydantic AI.

Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (cloud.langfuse.com free tier).
If keys are missing, instrument_agent() is a no-op so local runs still work.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def instrument_agent() -> bool:
    """Export Pydantic AI spans to Langfuse. Call once at process start."""
    if not langfuse_enabled():
        print("Langfuse skipped (set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY)")
        return False

    os.environ.setdefault("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

    from langfuse import get_client
    from pydantic_ai import Agent

    client = get_client()
    if not client.auth_check():
        print("Langfuse auth failed — check keys / LANGFUSE_BASE_URL")
        return False

    if hasattr(Agent, "instrument_all"):
        Agent.instrument_all()
    else:
        print("Pydantic AI has no Agent.instrument_all — traces may be incomplete")
    print(f"Langfuse OK → {os.environ['LANGFUSE_BASE_URL']}")
    return True


def flush() -> None:
    if not langfuse_enabled():
        return
    from langfuse import get_client

    get_client().flush()
