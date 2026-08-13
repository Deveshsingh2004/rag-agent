# Day 21 — FINAL MOCK (full repo / system design)

**Date:** 2026-08-13  
**Scope:** Entire rag-agent — ingest → retrieve → agent → SSE → cache → evals → ops  
**Format:** ~45 min screening / system design. Typed answers, graded bluntly.  
**Prompt:** Design a RAG agent for a company knowledge base at **10k users**.

**Overall:** PASS (weak) — after correction pass. First take was BORDERLINE.

---

## Questions

Answer in this file under **Your answers**. Use this repo as the reference architecture — say what you would keep, what you would change at 10k users.

1. **Ingest vs query path.** A PM says “when a user chats, just embed the question, search, and also re-embed any new docs they just uploaded — all inside the `/chat` request.” Draw the production ingest path vs the query path. What is allowed to be sync in the request? What must be async/batch (Celery/queue)? Why is embedding-on-chat a bad default at 10k users?

2. **Retrieval stack.** You have markdown + PDFs, ~500k chunks, 10k users. Pick: embedding model/dim, distance metric, index type + 2 HNSW knobs you’d tune first, chunking strategy (and what you would *not* use), and when you add a cross-encoder rerank. How do you talk about recall vs latency without lying?

3. **Agent + tools + safety.** When do you use Pydantic AI vs a raw tool loop vs LangGraph vs a supervisor? What goes in `deps_type` vs tools? Name 3 things that must never be a free-form tool. When is MCP worth it vs a normal Python function?

4. **Serving.** SSE vs WebSocket for this product. Why this demo’s in-process stream breaks with 2+ uvicorn workers — and what you reuse from EdusmarkAI. Semantic cache: key design, `user_id` TAG, when a cache hit is *wrong*. Where does context trim/filter/summarize sit?

5. **Eval, observability, tenancy.** LLM-as-judge vs hit@k — what each measures, why judge ≠ generator. What you put in Langfuse (and sampling). Multi-tenant company KB: schema-per-tenant vs RLS vs Redis TAG — pick one stack and say the failure mode.

6. **Failure modes / scale.** Gemini 429, Postgres down mid-ingest, HNSW recall drop at 1M+ chunks, prompt injection via uploaded notes, stale cache after re-ingest. For each: detect + mitigate in one sentence. What is the first metric you’d alert on in week 1?

---

## Your answers

_(type here)_

1. 

assuming currently we are catering text based answer :

first Ingest:
we will devide the whole document in small chunk using semantic chunking we will try to group same looking paragraph together to keep the meaning we use de limiter to find new line break new para . 
and we will save using HNSW so when finding we get more accurate result faster we will use m = 16 ef construction from 150-200 then we use an LLm to add a summary before embedding the chunk then we use an embedding model to convert the chunk to vector and save the vector in pg vector in a 768 size vector for faster processing .

second query :
whenever some one post a query on our chat endpoint we will embed the query to vector using an embedding model then that vector will be used to calculate the top 50 most similar vector with the query vector using the cosign method after getting the vector we will get the top 50 result and send that to a cross encoder to verify this can anser the query then we will get 5 chunk from where and send those to model and query and then we we stream the response to the client 

the whole process of embedding and engesting data will be async using celery with idempotent and the process of reciving the query  embedding the message for response and sending response and the whole query process should be sync . because we want fast result we can't keep user wating .

embedding on chat when you have 10 k user is bad because if 10 k user send you a document or pdf or image embedding ingesting it on fly will create enormous load and the server will melt or run out of memory so we should do these kind of things async and simple plan text query sync 


2. if we have approx. 500 k chunk i will embed it using an embedding model with 768 dim vector with cosign similarity because that is a standard . i will use HNSW for indexing with 2 knob m = 12(a lot of data more ram) and ef_construction= 200 to improve recall and accuracy it will take time to build but will be crucial one time for chunking i would use use document chunking because if i use semantic chunking it will cost a lot and lot of latency for LLM so i will use document chunking 

i will definitely add cross encoder because it is a large database and including cross encoder will improve accuracy a lot 

for good recall we have used m and ef_construction wirh HNSW so recall will be good latency will be a little because  we have added a cross encoder but it will improve accuracy and will help in long run . we will pick top 50 from vector search and top 5 from cross encoder 

3. i will explain all these in one line 

pydantic AI : in this we have to define tool decorater five function doc string description so that that model understand the pourpose of tool . and we always send the tool info to model 

raw loop: we make a while loop and control the flow we implement max iteration as gaurd first we send the query and function tools then model give us the tool name and argument we regex the tool name and argument and execute the tool and append the result in response and send again when the model call no tool we return the response as result 

langraph : here lang graph provide us the things by which we can enhance our agent functioning with state tool nodes checkpoint . one agent which act as all it think run tool and write response all it has these additional feature which it can use to be efficient like add human in loop 

supervisor : this is the most sofesticated one it  control the flow and assign task to other agent and receive result from them and think . on one worg it control the routing 



deps_type: it is the dependency we provide using the runcontext like the db connection anything which will be required with the tool or in the tool we provide it in parameter like user id 

tools: these are the function which are availsbe for model to run and get the result like search docs search db , email someone. any thing which require a fixed structured output should never be a freeform tool because this can cause mistake 

tool args: these are the argument provided by model to run a tool correctly 

MCP: it is a protocal for agent to get acces to the local MCP server's tool it help the model to discover the tool it does this by it self so you can connect multiple agents with your MCP server

python function : we have to import a function to use it we have to send this always to the model it is thghtly coppeled with code 


4. SSE is better because : simple work with POST, unidirection
WS: not good for LLm res stream because bidirection,complex,layer 3 , hard , good for multiplayer game
 
multiple worker can suscribe redis channel and when there is any publish all the connected worker will recieve the stream . so different worker suscribe different channel like stream:{user_id} this prevent cross tenent

semantic cache means first we embedd the query then redis search the KNN if find and the similarity is high we return that  when we encounter same generic question  multiple tile me should make a semantic vector of that and cache it don't cache the exact query  cache it also use user tag with the key because we don't want to show some other user do to other when the hig is wrong we use the db vector search . 

wrong hit = getting someone else data dat leak 


trim : give the k top recent chat cost free
filter : remove useless chat and then give cost free 
summarize : summarize the long conversation in small important query cost 1 llm call 


5. judge should not be also the generator of the response because it can produce bias and flag some unaccepted response as accepted .  

hit@k : it meand if search vector for 100 times the how mant times the correct or expected vector come in the top K vectors . 

in langfuse we store logs related whole flow the trace and span whe are used for debugging . in time system produce unexpected result we can debug what goes wrong.
schema: Schema-per-tenant is possible, but at thousands/10k+ tenants, migration and operational complexity can make RLS or another approach more attractive.
RLS: we implement row level security this mean the details of one user in db will be invisible for different user it is a secutity feature given by postgres 
redis tag: it isolates one user cache from other source of truth is the  db only 

faliour mode can me cross tenant data leak , i don't know any other 

6. i think these are different type of faliour and you want me to implement solution to handell this 

429: retry after some time and rate limit 
postgres down mid ingest: i will make the ingest idempotend and will try again 
recall drop at 1M+: we have to first test the situation with hit@k if bad we have to adjust the HNWS knob like m and ef_search for better recall but also keep in mind ram and latency 
prompt injection : we have to implement gaurd rail on out tools so no sencitive data can go out and also don't trust any data from user 
we have to invalidate all cache after new injest so new cache get created with correct new data 

we will set alert on /chat if anything happen we can log that and give user a meaning full messag e

if 95percentile of chat are taking more than 5 sen it is an alarm 



---

## Grades

First take: BORDERLINE. Regrade after correction:

| # | Topic | Grade | Notes |
|---|---|---|---|
| 1 | Ingest vs query path | PASS | Ingest = Celery + idempotent; `/chat` = embed **query** + retrieve + stream, sync. Docs never re-embedded inside `/chat`. Paths (50 → rerank 5 → SSE) still right. |
| 2 | Retrieval stack | BORDERLINE | Unchanged. Shape OK. Still missing **`ef_search`** (tune this first at query time). “Document chunking” still vague. Don’t claim recall is “good” without hit@k — HNSW is approximate. |
| 3 | Agent + tools + safety | BORDERLINE | `deps_type` via `RunContext` (db, user_id) vs tool args from the model — **fixed**. Supervisor = routing, not MCP — **fixed**. LangGraph: state / ToolNode / checkpointer / HITL — **fixed**. Still wrong on forbidden tools: you banned “structured output,” not **shell / raw SQL / send_email**. |
| 4 | Serving (SSE, workers, cache) | PASS | Redis pub/sub `stream:{user_id}` + workers subscribe is the EdusmarkAI fix. Cache = embed query → KNN + user TAG. Missing one sentence: **why the demo breaks** (in-process generator dies if the SSE socket is on another worker). Wrong-hit still only “other user’s data” — also stale docs + similar-text / different intent. |
| 5 | Eval + observability + tenancy | PASS | Schema-per-tenant possible but ops-hell at 10k tenants; RLS = SoT; Redis TAG = cache only. Judge ≠ generator + hit@k OK. Langfuse still “logs” — say traces/spans + **sampling** + cost/latency, not 100% in prod. |
| 6 | Failure modes / scale | PASS | p95 `/chat` > 5s as week-1 alert — correct. Idempotent ingest, hit@k + `ef_search`, don’t trust notes, invalidate cache. 429 still needs **backoff + jitter**, not only “retry later.” |

**Verdict: PASS (weak)**

Round-sinkers from the first take are gone. Would survive a screen if they probe Q2/`ef_search` and Q3 tool allowlist. Would still lose if they stop at “what must never be a free-form tool” and you repeat the structured-output line.

Memorize tonight (do not skip): **never expose shell, raw SQL, or send_email as free-form tools.** Query-time HNSW knob is **`ef_search`**, not only `m` / `ef_construction`.
