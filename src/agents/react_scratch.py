"""Day 9 — ReAct from scratch (no LangGraph / Pydantic AI).

Paper loop: Thought → Action → Observation → (repeat) → final answer.

Difference from Day 2 raw tool calling:
  Day 2: model emits native function_call parts (API-level tool calling).
  Day 9: model emits an explicit Thought + Action in text; we parse and drive
  a state machine. Same underlying idea; ReAct makes reasoning visible in the
  transcript (interview + debugging signal).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_STEPS = 6


class State(str, Enum):
    THINK = "THINK"  # call LLM, expect Thought + Action
    ACT = "ACT"  # execute tool
    OBSERVE = "OBSERVE"  # append Observation to transcript
    FINISH = "FINISH"
    ERROR = "ERROR"


@dataclass
class Step:
    thought: str
    action: str
    action_input: str
    observation: str | None = None


@dataclass
class ReActResult:
    answer: str
    steps: list[Step] = field(default_factory=list)
    terminal_state: State = State.FINISH


FAKE_NOTES = {
    "sse": (
        "SSE fanout: Redis pub/sub bus, uvicorn workers subscribe on connect, "
        "DB-poll fallback. Load-tested 2k concurrent."
    ),
    "celery": (
        "Celery: acks_late=True, prefetch=1, HP + BG queues, idempotent side effects."
    ),
    "pgvector": (
        "pgvector: cosine <=> , HNSW with m / ef_construction / ef_search. "
        "ef_search is the query-time recall dial."
    ),
}


def search_notes(query: str) -> str:
    """Keyword fallback if Postgres is down; tries pgvector search first."""
    try:
        from src.rag.search import search

        hits = search(query, k=2)
        if hits:
            return "\n---\n".join(f"{t}: {c[:300]}" for t, c, _ in hits)
    except Exception:
        pass
    q = query.lower()
    hits = [note for key, note in FAKE_NOTES.items() if key in q]
    return "\n".join(hits) if hits else "no matches"


def finish(answer: str) -> str:
    return answer


TOOLS: dict[str, Callable[..., str]] = {
    "search_notes": search_notes,
    "finish": finish,
}

SYSTEM = """You are a ReAct agent. You solve questions by alternating Thought and Action.

Available tools:
- search_notes[query] — search engineering notes
- finish[final_answer] — end the loop and return the answer to the user

Strict output format every turn (no markdown fences, no extra prose):
Thought: <your reasoning>
Action: <tool_name>
Action Input: <tool argument as plain text>

Rules:
- One Action per turn.
- After you see an Observation, continue with a new Thought/Action.
- When you have enough information, Action must be finish.
"""

ACTION_RE = re.compile(
    r"Thought:\s*(?P<thought>.*?)\s*"
    r"Action:\s*(?P<action>\w+)\s*"
    r"Action Input:\s*(?P<action_input>.*)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def parse_react(text: str) -> tuple[str, str, str]:
    m = ACTION_RE.search(text.strip())
    if not m:
        raise ValueError(f"unparseable ReAct turn:\n{text}")
    return (
        m.group("thought").strip(),
        m.group("action").strip().lower(),
        m.group("action_input").strip(),
    )


def run_react(question: str, *, verbose: bool = True) -> ReActResult:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY in .env")
    client = genai.Client(api_key=api_key)

    transcript = f"Question: {question}\n"
    steps: list[Step] = []
    state = State.THINK

    for step_i in range(1, MAX_STEPS + 1):
        if verbose:
            print(f"\n=== step {step_i} state={state.value} ===")

        if state == State.THINK:
            prompt = (
                SYSTEM
                + "\n\n"
                + transcript
                + "\nRespond with Thought / Action / Action Input only.\n"
            )
            resp = client.models.generate_content(model=MODEL, contents=prompt)
            raw = (resp.text or "").strip()
            if verbose:
                print(raw)
            try:
                thought, action, action_input = parse_react(raw)
            except ValueError as e:
                if verbose:
                    print(f"[parse error] {e}")
                return ReActResult(
                    answer=f"failed to parse model output: {e}",
                    steps=steps,
                    terminal_state=State.ERROR,
                )
            step = Step(thought=thought, action=action, action_input=action_input)
            steps.append(step)
            state = State.ACT

        if state == State.ACT:
            step = steps[-1]
            if step.action not in TOOLS:
                step.observation = f"unknown tool: {step.action}"
            else:
                try:
                    step.observation = TOOLS[step.action](step.action_input)
                except Exception as e:
                    step.observation = f"{type(e).__name__}: {e}"
            if verbose:
                print(f"Observation: {step.observation}")

            if step.action == "finish":
                return ReActResult(
                    answer=step.action_input,
                    steps=steps,
                    terminal_state=State.FINISH,
                )
            state = State.OBSERVE

        if state == State.OBSERVE:
            step = steps[-1]
            transcript += (
                f"\nThought: {step.thought}\n"
                f"Action: {step.action}\n"
                f"Action Input: {step.action_input}\n"
                f"Observation: {step.observation}\n"
            )
            state = State.THINK

    return ReActResult(
        answer=f"exceeded {MAX_STEPS} steps without finish",
        steps=steps,
        terminal_state=State.ERROR,
    )


def main() -> None:
    q = (
        "What did I write about scaling SSE, and what HNSW query knob "
        "controls recall vs latency? Be concise."
    )
    print(f"USER: {q}")
    result = run_react(q)
    print("\n=== FINAL ===")
    print(f"terminal_state: {result.terminal_state.value}")
    print(f"answer: {result.answer}")
    print(f"steps: {len(result.steps)}")


if __name__ == "__main__":
    main()
