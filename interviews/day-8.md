# Day 8 — MOCK #2 (Days 5–7)

**Date:** 2026-08-11  
**Scope:** Embeddings, pgvector, HNSW, chunking  
**Format:** Screening style — typed answers, graded bluntly  
**Overall:** BORDERLINE

---

## Your answers (as written)

1. Embedding means converting free document text to a 765 dimention vector using an LLM which will convert the text to high dimention vector . we do this because it give us a vector by which we can compare the distance with query and computer understach number well . we use cosine with the gemini because we want to ignore the magnitude difference between the to vector we only want the distance between the points and in cosine we only see distance which indicate the similarity between the two query and the vector . the size length of text does not matter

2. so we use vector 768 + matching vector cogign because in HNSW the node are connected according to their similarity and in cosign also we find the distance between the vector and in HNSW we already have close vecort connected so it is very easy to find what you are looking for . 2 things can happen either the DB will reject the query and do a ful table scan or it will return a query error .

3. the 3 HNSW knobs are m= the no of connection a node have (the quality network of node, more ram), ef_construction =the no of candidate is explored before it it connect a vector to a need , ef_search= the no of vector it explore before giving the best result . this is a querytime knob not build time .

m = better recall , more build time more ram, build time increse- default valuse 16
ef_construction = more build time, better recall , build time increse - default value 100-200
ef_search = more query time , build time don't increse , query time increse

when ef_search=1 then it mean it is only exploring 1 level of nodes or not even exploring it is just like returning whatever we get

4. Naive = fixed length chunking no other logic apply , it cut mid sentence ,mid word ,not practical only faster
Paragraph = it uses regx for chunking finding new line new paragraph try to capture the context of para but the context is very different from over all meaning of document
context retrival = here we all a small summary of the chunk and then embedd it , good for long document, better capture the sentiment of the document and far better than the other 2 but is more caustly we have to use a LLM

in long document or anyother thing naive is very bad and not practical because it loss whole ides of the chunk because it cut mid way only can be used if we can compromise quality a lot for time  and minimum cot for building .
pay for Contextual Retrieval most of the time if you want good result from the rag and the response should have similarity with the query

5. currently i am not learning code i only have the conceptual idea

can that is :chunk → embed → store → index → query
i will do it in celery if the order of response not matter for multiple agent . and i will use sync if the order matter like after query 1 only you should give answer of quert 2 or query 2 need context of query 1

---

## Grades

| # | Topic | Grade | Notes |
|---|---|---|---|
| 1 | Embeddings + cosine | BORDERLINE | Concept OK. Dim is **768** not 765. Embedding model ≠ chat LLM. Cosine = direction/similarity; magnitude often noise for text — say that cleanly. |
| 2 | pgvector schema / ops | BORDERLINE | Missed: `vector(768)` **enforces dim at DB**. Mismatch op class vs `<=>` → wrong graph metric / bad neighbors (not always hard error). |
| 3 | HNSW knobs | PASS | m / ef_construction build; ef_search query. ef_search=1 ≈ broken recall. Defaults sane. |
| 4 | Chunking strategies | BORDERLINE | Naive failure correct. "Pay for contextual most of the time" is wrong — skip short/self-contained notes; pay when chunks are ambiguous without doc context. |
| 5 | System design glue | FAIL | Pipeline slogan only. Celery answer was about agent turn order — wrong question. Ingest 5k notes = **async Celery/batch job**; user query = **sync path** (embed query + ANN). |

**Verdict: BORDERLINE**

Fix before Day 9: Q5 Celery vs sync for **ingest vs query**, not multi-agent ordering. Q2: dim constraint + op-class match.
