"""Day 11 — Supervisor / routing pattern in LangGraph.

One LLM (supervisor) decides which specialist runs next:
  - retriever : search notes (tool)
  - writer    : draft a short answer from retrieved context (no tools)
  - FINISH    : done

Gemini constraint: the last turn in a generate call must be a user message or
tool response — not an AIMessage. So retriever/writer use fresh prompts ending
in HumanMessage; they do not replay a history that ends on the model.
"""

from __future__ import annotations

import os
import operator
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

load_dotenv()

if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_RETRIEVES = 2


class RouteDecision(BaseModel):
    next: Literal["retriever", "writer", "FINISH"] = Field(
        description="Which node should run next"
    )
    reason: str = Field(description="One short sentence why")


class SupervisorState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    route: str
    route_reason: str
    context: str
    retrieve_count: int
    wrote: bool
    route_log: Annotated[list[str], operator.add]


@tool
def search_notes(query: str) -> str:
    """Search engineering notes. Returns matching snippets."""
    try:
        from src.rag.search import search

        hits = search(query, k=2)
        if hits:
            return "\n---\n".join(f"{t}: {c[:500]}" for t, c, _ in hits)
    except Exception as e:
        return f"search error: {type(e).__name__}: {e}"
    return "no matches"


def _user_question(state: SupervisorState) -> str:
    for m in state["messages"]:
        if isinstance(m, HumanMessage):
            return str(m.content)
    return ""


def build_supervisor_graph():
    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)
    router = llm.with_structured_output(RouteDecision)
    writer_llm = llm
    retriever_llm = llm.bind_tools([search_notes])

    def supervisor(state: SupervisorState) -> dict:
        # Hard guards — don't trust the router to stop loops.
        if state.get("wrote"):
            return {
                "route": "FINISH",
                "route_reason": "writer already produced an answer",
                "route_log": ["FINISH: writer already produced an answer"],
            }
        if state.get("retrieve_count", 0) >= MAX_RETRIEVES and (state.get("context") or ""):
            return {
                "route": "writer",
                "route_reason": f"hit retrieve cap ({MAX_RETRIEVES}); write from context",
                "route_log": [
                    f"writer: hit retrieve cap ({MAX_RETRIEVES}); write from context"
                ],
            }

        decision: RouteDecision = router.invoke(
            [
                SystemMessage(
                    content=(
                        "You route a notes Q&A agent.\n"
                        "- retriever: need more facts (context empty or missing a subtopic).\n"
                        "- writer: context is enough to answer.\n"
                        "- FINISH: only if a final written answer already exists "
                        "(wrote=true — the system will set this).\n"
                        "Typical path: retriever → writer → FINISH. Max 2 retrieves."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question: {_user_question(state)}\n"
                        f"retrieve_count: {state.get('retrieve_count', 0)}\n"
                        f"wrote: {state.get('wrote', False)}\n"
                        f"context ({len(state.get('context') or '')} chars):\n"
                        f"{(state.get('context') or '(empty)')[:800]}\n"
                        "Choose next."
                    )
                ),
            ]
        )
        nxt = decision.next
        # Don't FINISH before writing.
        if nxt == "FINISH" and not state.get("wrote"):
            nxt = "writer" if (state.get("context") or "") else "retriever"
            reason = f"overrode FINISH → {nxt} (no written answer yet)"
        else:
            reason = decision.reason
        return {
            "route": nxt,
            "route_reason": reason,
            "route_log": [f"{nxt}: {reason}"],
        }

    def retriever(state: SupervisorState) -> dict:
        # Fresh prompt ending in HumanMessage — required by gemini-*-flash-lite.
        ai: AIMessage = retriever_llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You only retrieve. Always call search_notes once with a focused "
                        "query covering what is still missing. Do not answer the user."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question: {_user_question(state)}\n"
                        f"Context so far:\n{(state.get('context') or '(empty)')[:600]}\n"
                        "Call search_notes now."
                    )
                ),
            ]
        )
        return {
            "messages": [ai],
            "retrieve_count": state.get("retrieve_count", 0) + 1,
        }

    def run_tools(state: SupervisorState) -> dict:
        out = ToolNode([search_notes]).invoke(state)
        chunks = [
            str(getattr(m, "content", ""))
            for m in out.get("messages", [])
            if getattr(m, "content", "")
        ]
        extra = "\n---\n".join(chunks)
        prev = state.get("context") or ""
        merged = f"{prev}\n{extra}".strip() if prev else extra
        return {"messages": out["messages"], "context": merged}

    def writer(state: SupervisorState) -> dict:
        ai = writer_llm.invoke(
            [
                SystemMessage(
                    content=(
                        "Write the final answer using ONLY the context. Be concise. "
                        "If context is empty, say you lack notes."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question: {_user_question(state)}\n\n"
                        f"Context:\n{state.get('context') or '(empty)'}"
                    )
                ),
            ]
        )
        return {"messages": [ai], "wrote": True}

    def route_after_supervisor(state: SupervisorState) -> str:
        nxt = state.get("route") or "FINISH"
        return END if nxt == "FINISH" else nxt

    def route_after_retriever(state: SupervisorState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        # No tool call — don't loop into Gemini prefilling errors; go write or re-route.
        if state.get("context"):
            return "writer"
        return "supervisor"

    g = StateGraph(SupervisorState)
    g.add_node("supervisor", supervisor)
    g.add_node("retriever", retriever)
    g.add_node("tools", run_tools)
    g.add_node("writer", writer)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"retriever": "retriever", "writer": "writer", END: END},
    )
    g.add_conditional_edges(
        "retriever",
        route_after_retriever,
        {"tools": "tools", "writer": "writer", "supervisor": "supervisor"},
    )
    g.add_edge("tools", "supervisor")
    g.add_edge("writer", "supervisor")
    return g.compile()


def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY in .env")

    app = build_supervisor_graph()
    question = (
        "Using my notes: how did SSE scale at EdusmarkAI, and which HNSW knob "
        "tunes recall vs latency at query time?"
    )
    print(f"USER: {question}\n")
    print("--- stream ---")

    init: SupervisorState = {
        "messages": [HumanMessage(content=question)],
        "route": "",
        "route_reason": "",
        "context": "",
        "retrieve_count": 0,
        "wrote": False,
        "route_log": [],
    }

    state: dict = dict(init)
    for event in app.stream(init, stream_mode="updates", config={"recursion_limit": 12}):
        for node, update in event.items():
            print(f"\n[{node}]")
            if update.get("route"):
                print(f"  route -> {update['route']} ({update.get('route_reason', '')})")
            for line in update.get("route_log") or []:
                print(f"  log: {line}")
            if "retrieve_count" in update:
                print(f"  retrieve_count={update['retrieve_count']}")
            for m in update.get("messages") or []:
                kind = type(m).__name__
                if isinstance(m, AIMessage) and m.tool_calls:
                    print(f"  {kind} tool_calls={m.tool_calls}")
                else:
                    content = str(getattr(m, "content", ""))[:220].replace("\n", " ")
                    print(f"  {kind}: {content}")
            if update.get("context"):
                print(f"  context_len={len(update['context'])}")

            if "messages" in update:
                state["messages"] = list(state.get("messages", [])) + list(
                    update["messages"]
                )
            if "route_log" in update:
                state["route_log"] = list(state.get("route_log", [])) + list(
                    update["route_log"]
                )
            for k in (
                "route",
                "route_reason",
                "context",
                "retrieve_count",
                "wrote",
            ):
                if k in update and update[k] is not None:
                    state[k] = update[k]

    print("\n=== ROUTE LOG ===")
    for line in state.get("route_log") or []:
        print(f"- {line}")
    print("\n=== FINAL ANSWER ===")
    print(getattr(state["messages"][-1], "content", state["messages"][-1]))


if __name__ == "__main__":
    main()
