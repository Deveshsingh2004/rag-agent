# Day 4 — MOCK #1 (Days 1–3)

**Date:** 2026-07-31  
**Scope:** Structured outputs, raw tool calling, Pydantic AI  
**Format:** 30-min screening style — typed answers, graded bluntly  
**Overall:** PASS

---

## Your answers (as written)

1. response_schema is not just a prompt enhancement it is a parameter we pass to the model to describe the exact structure in which we want the response and in gemini response is generated one token at a time and after generating each token it does a probability distribution over the whole vocabulary with a probability of 0 for each token which can make the response invalid which does not follow our response_schema. so it is a constrained decoding at token level.

after this also it can fail validation because of the validation constraints which are not sent like username length max =5 , age > 18 some validation which are present in pydantic model but not send to LLM they can make the validation fail

2. Tool calling loop is a fancy name of a while loop it is nothing complex . the loop is

    user prompt + history is send to LLM with the info about all tools it can use like search, edit, DB query with description

    now LLM decide if the it can answer the query without using the tool or it will require the tool -> if it can answer directly it send no tool call no parameter only the text part -> then backend send the response to user

    but if it need a tool it send the tool name in function call and the parameter for tool -> now our loop find if there is any function call if yes it execute it with the argument and append result in response

    then the appended response is send again this loop goes on till llm only give final answer without tool call then backend send it as response

State :
Start :Call the LLM
Function call : execute the func
STOP : LLM answer with only text no function call
Max Iteration: Max iteration reached without answer  STOP
Error: if something unexpected happen

Termination state: STOP ,Error, Max no of Iteration

If model give 3 func call in one response we loop all function call execute with argument then append all in response and send to LLM
we can do this in parallel if independent or we can loop the sync way

3. It can happen because model responses and validation are not very robust any confusing prompt send to model can make it doubt if it has done action and it can re execute it . so we can use idempotence to do this use any unique key and store that in redis to check if this action is performed already or we can always include robust info about the succeeded action like email send timestamp, sent to, state, task id etc , we can add an approver human in loop to approve these task .

4. Injecting context through dep_types solve 2 problem 1st we don't have to declare a global variable for our context we can make any variable and we can add in that like db context, notes context, previous data any thing and we just have to pass it to the function so function has no overhead of fetching the data from accessing global variable . instead we only add run context to function which require the context like search for plain function we don't all like get today date .

the Test module is a fake model which create a valid input argument for tools from garbage value using function tool's schema and then it call the real function test it and validate if the output coming is valid does it follow the schema which satisfy the output_type but it does not prove any thing about if the function is doing the correct logic it only change the output format should be correct not logic no reasoning only schema.

5. when we are doing some coding thing and we want exact structured output like we need response we have to store it in db , we need it to pass as argument in function we have to pars it to send to frontend in some formate we need json only because we have to use the . operater on result then we use output type so it is impossible to get incorrect response. we will not use output_type when we don't want to restrict model in a lot of constrain , output formate does not matter the content matter , some human want response who don't want very structured . i will not use it while making chatbot because here the LLM should decide response formate becuse diff question need diff response formate like chat , graph , picture table etc . for a chatbot i will give free text . for my medical data OCR i would definitely implement output_type becasue i will not risk any incorrect data

---

## Grades

| # | Topic | Grade | Notes |
|---|---|---|---|
| 1 | Constrained decoding | PASS | Mechanism correct (token-level mask). Named Pydantic-only validators as residual failure. Missed truncation/safety-filter as second failure mode — mention if asked follow-up. |
| 2 | Tool-call state machine | PASS | States + 3 terminations (text, max iter, error). Parallel tool calls correct. Drop "fancy while loop" tone in real interviews — say "agent control loop / state machine." |
| 3 | Agent-as-actor / side effects | PASS | Fixed Day 2 fail. Three distinct defenses: Redis idempotency key, verbose success payload, human approval gate. Why = model uncertainty after weak tool result. |
| 4 | deps_type + TestModel | PASS | TestModel explanation much improved vs Day 3. Nuance: TestModel *does* run your real tools — you *can* assert tool side effects; what it does NOT prove is LLM tool selection / argument quality. |
| 5 | output_type tradeoff | BORDERLINE | Chatbot vs OCR examples good. Still said "impossible to get incorrect response" — wrong. Shape ≠ truth. Hallucinated field values still possible. |

**Verdict: PASS**

Weakest leftover: conflating schema validity with semantic correctness (Q5). Strongest improvement: Q3 side-effect defenses and Q4 TestModel mechanics.
