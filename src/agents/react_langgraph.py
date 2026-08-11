"""Day 10 — Same ReAct loop as Day 9, expressed as a LangGraph StateGraph.

What you gain over react_scratch.py:
  - State is a TypedDict with a messages reducer (append, don't overwrite)
  - Nodes + conditional edges replace your hand-rolled while-loop
  - ToolNode executes native tool_calls (no Thought/Action regex)
  - MemorySaver checkpointer = pause/resume / thread memory
  - stream() shows state after each node (debugging signal)
"""

from __future__ import annotations

import os
from typing import Annotated

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

load_dotenv()

# langchain-google-genai reads GOOGLE_API_KEY
if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


class AgentState(TypedDict):
    # add_messages = reducer: new messages APPEND to history, not replace.
    messages: Annotated[list[BaseMessage], add_messages]


@tool
def search_notes(query: str) -> str:
    """Search engineering notes by semantic/keyword query. Returns matching snippets."""
    try:
        from src.rag.search import search

        hits = search(query, k=2)
        if hits:
            return "\n---\n".join(f"{t}: {c[:300]}" for t, c, _ in hits)
    except Exception as e:
        return f"search error: {type(e).__name__}: {e}"
    return "no matches"


TOOLS = [search_notes]


def build_graph():
    llm = ChatGoogleGenerativeAI(model=MODEL, temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    graph.add_edge(START, "agent")
    # tools_condition: if last AIMessage has tool_calls → "tools", else END
    graph.add_conditional_edges(
        "agent",
        tools_condition,  # returns "tools" | "__end__"
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit("Set GEMINI_API_KEY or GOOGLE_API_KEY in .env")

    app = build_graph()
    question = (
        "What did I write about scaling SSE, and which HNSW query knob "
        "controls recall vs latency? Be concise."
    )
    config = {"configurable": {"thread_id": "day10-demo"}, "recursion_limit": 8}

    print(f"USER: {question}\n")
    print("--- stream (node updates) ---")
    final_text = ""
    for event in app.stream(
        {"messages": [HumanMessage(content=question)]},
        config=config,
        stream_mode="updates",
    ):
        # event = {node_name: {messages: [...]}}
        for node, update in event.items():
            msgs = update.get("messages", [])
            print(f"\n[{node}]")
            for m in msgs:
                kind = type(m).__name__
                if isinstance(m, AIMessage) and m.tool_calls:
                    print(f"  {kind} tool_calls={m.tool_calls}")
                else:
                    content = getattr(m, "content", "")
                    preview = str(content)[:240].replace("\n", " ")
                    print(f"  {kind}: {preview}")
                    if node == "agent" and content and not getattr(m, "tool_calls", None):
                        final_text = str(content)

    print("\n=== FINAL ===")
    print(final_text or "(see last agent text above)")

    # Checkpointer demo: same thread_id → history retained for a follow-up.
    follow = app.invoke(
        {"messages": [HumanMessage(content="Remind me: what was the HNSW knob only?")]},
        config=config,
    )
    print("\n=== FOLLOW-UP (same thread_id, checkpointer) ===")
    print(follow["messages"][-1].content)


if __name__ == "__main__":
    main()
