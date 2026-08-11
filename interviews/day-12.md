# Day 12 — MOCK #3 (Days 9–11)

**Date:** 2026-08-11  
**Scope:** ReAct, LangGraph, supervisor routing  
**Format:** Screening style — typed answers, graded bluntly  
**Overall:** PASS

---

## Your answers (as written)

1. User -> supervisor -> retrival -> supervisor -> writer -> supervisor -> Finish (if it has supervisor in it)
the state are like think -> act-> tool call -> observe response -> think  -> finish (correct one) in this the new think is thinking and we get to know what it is thinking and why it do this because we can transcript the thinking use full in debugging
the 2 terminal condition except success it if it cross Max_Iteration gaurd , if any error occured like the tool call failed or the fodel has some error

2. natice gemini langchain toolcall we should do when the project is very simple and we don't need heavey library or increse complexity so we can so simple tool call in a while loop . but when you want to do it in a more prefessional way where the library handell all the things and the project is complex then we should use natice tool call using library because we don't have to do regex  . in text based we have to do regex and if regx fail of not correctly get function name or argument the functioncall can give error of incorrect result

3. i) the most important is the no regex based function calling it is handelled by library . ii) eleminate the while loop the agent think and proceed how it think is good we don't have to manage the loop the agent do it itself and the gaurd in max iteration for preventing infinite loop . iii) state and chekpoint for saving the context and start from where you have left also for human in loop approval

4. a checkpoint is a save point where the agent save all context of the things happened and make state out of it and it is saved so when user comeback after interruption , error failaur then the user don't have to reming it . so in send mail we can tell the agent and give tool for writting sending mail all the thing but just before sending we can inrurrept the model and fit an human approver which approve the agent to use send email so here we intrupt and take approve .

5. A supervisor + specialists is better when you need different roles, permissions, prompts, or models, and want clearer control over who does what.
The downside is extra LLM calls—the supervisor may run on every hop, increasing token usage, latency, and cost.
You can audit routing by storing a route_log containing each decision, selected specialist, reason, and relevant state/context.

---

## Grades

| # | Topic | Grade | Notes |
|---|---|---|---|
| 1 | ReAct state machine | PASS | THINK/ACT/OBSERVE/FINISH correct; max-iter + error as non-success exits. Opening mixed supervisor graph with ReAct — fine if you label which is which. |
| 2 | Native tools vs text ReAct | BORDERLINE | Regex fragility correct (you lived it Day 9). Flip the framing: **prefer native tools in production**; hand-rolled while-loop is fine for learning/simple. Don't say "native only when complex library." |
| 3 | LangGraph gains | PASS | Native tools, explicit graph (not "agent manages itself"), checkpointer/HITL. Minor: you still set `recursion_limit` — graph doesn't remove the guard. |
| 4 | Checkpointer / HITL | PASS | Persist thread state + interrupt before side-effect. Good. |
| 5 | Supervisor when/why + cost | PASS | Permissions/roles + cost/latency + route_log audit. Clean. |

**Verdict: PASS**

Leftover: Q2 production default = native structured tool calls; text ReAct is for pedagogy / visible Thoughts, not because "project is simple."
