"""Day 2 — Raw tool calling.

No framework. Hand-rolled request -> tool_call -> tool_result -> final loop.
Point: understand the state machine that Pydantic AI and LangGraph hide.

Two tools:
  - search_notes(query)  : returns hardcoded matches (RAG placeholder)
  - get_current_date()   : trivial, forces multi-tool sequencing
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Callable

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
# MODEL = "gemini-3.1-pro-preview"  #For Complex Agentic AI Learning
MODEL = "gemini-3.5-flash-lite"
MAX_ITERATIONS = 8


FAKE_NOTES = {
    "sse": (
        "SSE fanout at 50k concurrent: Redis pub/sub as bus, uvicorn workers "
        "subscribe on connect, DB-poll fallback for buffered proxies."
    ),
    "celery": (
        "5 Celery queues at EdusmarkAI, acks_late=True, prefetch=1, "
        "HP + BG queues for assessment pipeline."
    ),
    "pgvector": (
        "pgvector HNSW: cosine <=> distance, ef_construction=200 build-time, "
        "ef_search=40 for recall/latency tradeoff."
    ),
}


def search_notes(query: str) -> str:
    q = query.lower()
    hits = [note for key, note in FAKE_NOTES.items() if key in q]
    return "\n".join(hits) if hits else "no matches"


def get_current_date() -> str:
    return dt.date.today().isoformat()


TOOLS: dict[str, Callable[..., Any]] = {
    "search_notes": search_notes,
    "get_current_date": get_current_date,
}


TOOL_DECLARATIONS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_notes",
                description="Search the engineering notes corpus by keyword. Returns matching note contents.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(
                            type=types.Type.STRING,
                            description="A keyword or short phrase to search for",
                        ),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_current_date",
                description="Get today's date in ISO format (YYYY-MM-DD). No arguments.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
        ]
    )
]


def run_agent(user_prompt: str, verbose: bool = True) -> str:
    """The tool-calling state machine, hand-rolled.

    States:
      START  -> call LLM
      LLM_RESPONSE  -> inspect part: function_call or text
        function_call -> execute tool, append result, loop back to LLM
        text          -> DONE
      DONE          -> return final text
      GUARD         -> max iterations exceeded, abort
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
    ]
    config = types.GenerateContentConfig(tools=TOOL_DECLARATIONS)

    for iteration in range(1, MAX_ITERATIONS + 1):
        if verbose:
            print(f"\n--- iteration {iteration} ---")
        response = client.models.generate_content(
            model=MODEL, contents=contents, config=config
        )
        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        function_calls = [p.function_call for p in parts if p.function_call is not None]
        text_parts = [p.text for p in parts if p.text]
        if not function_calls:
            final = "".join(text_parts)
            if verbose:
                print(f"[final text] {final}")
            return final

        contents.append(candidate.content)

        response_parts: list[types.Part] = []
        for call in function_calls:
            name = call.name
            args = dict(call.args) if call.args else {}
            if verbose:
                print(f"[tool_call] {name}({args})")
            if name not in TOOLS:
                result = {"error": f"unknown tool {name}"}
            else:
                try:
                    result = {"result": TOOLS[name](**args)}
                except Exception as e:
                    result = {"error": f"{type(e).__name__}: {e}"}
            if verbose:
                print(f"[tool_result] {name} -> {result}")
            response_parts.append(
                types.Part.from_function_response(name=name, response=result)
            )

        contents.append(types.Content(role="user", parts=response_parts))

    raise RuntimeError(f"agent exceeded {MAX_ITERATIONS} iterations without terminating")


def main() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY in .env")

    prompt = (
        "Look up what I wrote about SSE and about pgvector, and tell me what today's date is. "
        "Give me a one-paragraph summary of both notes plus the date at the end."
    )
    print(f"USER: {prompt}")
    final = run_agent(prompt)
    print("\n=== FINAL ANSWER ===")
    print(final)


if __name__ == "__main__":
    main()
