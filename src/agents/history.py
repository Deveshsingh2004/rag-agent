"""Day 14 — Context window management for multi-turn agents.

Three strategies behind one Trimmer protocol:
  1. LastNTrimmer      — keep last N messages (cheap, loses old facts)
  2. SummarizingTrimmer — compress older turns into a summary message (LLM cost)
  3. FilterTrimmer      — drop low-signal turns (tool noise / short acks)

Wire into an agent via message_history=trimmer.apply(history).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _parts_text(msg: ModelMessage) -> str:
    bits: list[str] = []
    for part in getattr(msg, "parts", []) or []:
        if isinstance(part, UserPromptPart):
            bits.append(str(part.content))
        elif isinstance(part, TextPart):
            bits.append(part.content)
        else:
            # Tool calls / returns etc. — keep a short marker for filtering demos
            kind = type(part).__name__
            bits.append(f"[{kind}]")
    return " ".join(bits).strip()


def _role(msg: ModelMessage) -> str:
    if isinstance(msg, ModelRequest):
        return "user"
    if isinstance(msg, ModelResponse):
        return "assistant"
    return type(msg).__name__


class Trimmer(ABC):
    @abstractmethod
    def apply(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        ...


@dataclass
class LastNTrimmer(Trimmer):
    """Keep the last `n` messages. O(1) logic, zero LLM cost."""

    n: int = 6

    def apply(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        if self.n <= 0:
            return []
        return messages[-self.n :]


@dataclass
class SummarizingTrimmer(Trimmer):
    """Keep last `keep_last` messages; summarize everything before that into one user note."""

    keep_last: int = 4
    model: str = MODEL

    def apply(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        if len(messages) <= self.keep_last:
            return list(messages)

        old, recent = messages[: -self.keep_last], messages[-self.keep_last :]
        transcript = "\n".join(f"{_role(m)}: {_parts_text(m)}" for m in old)
        summary = self._summarize(transcript)
        summary_msg = ModelRequest(parts=[UserPromptPart(content=f"[conversation summary]\n{summary}")])
        return [summary_msg, *recent]

    def _summarize(self, transcript: str) -> str:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise SystemExit("Set GEMINI_API_KEY in .env")
        if os.getenv("HISTORY_STUB", "").lower() in {"1", "true", "yes"}:
            return f"(stub summary of {transcript.count(chr(10)) + 1} lines)"
        client = genai.Client(api_key=api_key)
        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=(
                    "Summarize this chat for an agent continuing the conversation. "
                    "Keep facts, decisions, and open questions. Max 8 bullet points.\n\n"
                    f"{transcript}"
                ),
            )
            return (resp.text or "").strip() or "(empty summary)"
        except Exception as e:
            return f"(summary failed: {type(e).__name__}: {e}; stub) key topics from older turns retained poorly"


@dataclass
class FilterTrimmer(Trimmer):
    """Drop short ack-style turns and pure tool-marker noise; then apply Last-N."""

    n: int = 8
    min_chars: int = 20

    def apply(self, messages: list[ModelMessage]) -> list[ModelMessage]:
        kept: list[ModelMessage] = []
        for m in messages:
            text = _parts_text(m)
            # Drop tiny acknowledgements ("ok", "thanks") that burn context.
            if len(text) < self.min_chars and not text.startswith("["):
                continue
            # Drop messages that are only tool markers with no prose.
            if text.startswith("[") and "]" in text and len(text) < 40:
                continue
            kept.append(m)
        return LastNTrimmer(n=self.n).apply(kept)


def demo_history() -> list[ModelMessage]:
    """Synthetic multi-turn history (longer than a tiny window)."""
    turns = [
        ("user", "What is SSE fanout at EdusmarkAI?"),
        ("assistant", "Redis pub/sub bus; uvicorn workers subscribe per user channel."),
        ("user", "ok"),
        ("assistant", "Want details on Celery publish path?"),
        ("user", "Also how does HNSW ef_search work?"),
        (
            "assistant",
            "ef_search is the query-time candidate list size: higher recall, higher latency.",
        ),
        ("user", "thanks"),
        ("assistant", "Anytime."),
        ("user", "Compare that to ef_construction."),
        (
            "assistant",
            "ef_construction is build-time; ef_search is query-time. m is graph degree.",
        ),
        ("user", "Remind me the SSE part and the HNSW query knob only."),
    ]
    out: list[ModelMessage] = []
    for role, text in turns:
        if role == "user":
            out.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        else:
            out.append(ModelResponse(parts=[TextPart(content=text)]))
    return out


def _print_trimmed(label: str, msgs: list[ModelMessage]) -> None:
    print(f"\n=== {label} ({len(msgs)} messages) ===")
    for m in msgs:
        text = _parts_text(m).replace("\n", " ")
        print(f"  {_role(m):9} {text[:120]}")


def main() -> None:
    history = demo_history()
    print(f"full history: {len(history)} messages")

    strategies: list[tuple[str, Trimmer]] = [
        ("last_n(4)", LastNTrimmer(n=4)),
        ("filter+last_n(6)", FilterTrimmer(n=6, min_chars=20)),
        ("summarize(keep_last=4)", SummarizingTrimmer(keep_last=4)),
    ]
    for name, trimmer in strategies:
        trimmed = trimmer.apply(history)
        _print_trimmed(name, trimmed)

    print(
        "\nWire-up (conceptual): agent.run(user_prompt, message_history=trimmer.apply(prior))"
    )


if __name__ == "__main__":
    main()
