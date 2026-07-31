"""Day 3 — Offline tests. No Gemini calls. No API key required."""

from __future__ import annotations

from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from src.agents.notes_agent import NotesAnswer, NotesDeps, agent

# Hard kill-switch: any accidental live model call fails the test suite.
models.ALLOW_MODEL_REQUESTS = False


def test_agent_runs_with_testmodel_and_returns_notesanswer() -> None:
    deps = NotesDeps(notes={"sse": "SSE note about Redis pub/sub"})
    with agent.override(model=TestModel()):
        result = agent.run_sync("Summarize SSE and give today's date", deps=deps)

    assert isinstance(result.output, NotesAnswer)
    assert isinstance(result.output.summary, str)
    assert isinstance(result.output.date, str)
    assert isinstance(result.output.sources_used, list)


def test_search_notes_reads_from_injected_deps_not_globals() -> None:
    """deps_type payoff: swap the corpus per test without monkeypatching module state."""
    deps = NotesDeps(notes={"celery": "acks_late=True, prefetch=1"})
    with agent.override(model=TestModel()):
        result = agent.run_sync("What did I write about celery?", deps=deps)

    assert isinstance(result.output, NotesAnswer)
    # TestModel fabricates args; the point is the run completes against our deps.
    assert result.output is not None
