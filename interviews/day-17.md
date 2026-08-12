# Day 17 — MOCK #4 (Days 13–16)

**Date:** 2026-08-12  
**Scope:** FastAPI SSE, context window mgmt, MCP server + client, semantic cache concept  
**Format:** Screening style — typed answers, graded bluntly  
**Overall:** PASS

---

## Your answers (as written)

1. SSE because uni direction , work with simple POST rest api , simple to implement  good for LLM streaming because that is also unidirection. Websocker hard to debug ,very complex , bidirectional not suited for LLM response streaming. all uvicorn suscribe to redis channel and when message came it stream to the channel SSE send it to webbrowser.

2. trim : send recent messages . low cost
summarize : use LLM to summarize the conversation.  high cost
filter : remove unusefull message  low cost
halucination and change meaning dut to shortening message

3. MCP give a standard way to connect different client from different agent also give the tools and argument it self
server : it provide cilent the info about tools and argument and acces to tools
client:  it ask the server on behalf of model and tell the model about all tools server has and tell user server to execute the tools

4. If the MCP server dies mid-request, the agent should timeout/retry and return a clear fallback/error instead of hanging. Amortize list_tools latency by discovering/caching tool schemas once per connection/session and reusing them.

5. TAG filtering matters for semantic caches when multiple users/tenants share the same Redis. Without user_id filtering, a semantically similar query could return another user's cached answer, causing a serious data/privacy leak.

---

## Grades

| # | Topic | Grade | Notes |
|---|---|---|---|
| 1 | SSE vs WebSocket + multi-worker | PASS | Uni-dir + HTTP is the right reason. Nuance: workers subscribe to **user-scoped** channels (`user:{id}`), not one global channel blasting every browser. |
| 2 | Context window strategies | PASS | Costs right. Summarize failure = omit/flip constraints. |
| 3 | MCP vs OpenAPI / server-client | PASS | Standard tool advertise/call across hosts. Client = host/agent; server = execute. |
| 4 | MCP consume + failure modes | PASS | Timeout/retry/clear error + cache `list_tools` per session. That's the amortization. |
| 5 | Semantic cache (concept) | PASS | TAG = tenant isolation. Skip it = cross-user leak. Best answer of the set. |

**Verdict: PASS**

Leftover: Q1 fanout is per-user channel, not "all uvicorn → all browsers."
