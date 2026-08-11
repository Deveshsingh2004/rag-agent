# Medical form OCR pipeline

## Stack

Django backend, Gemini Vision for field extraction, OpenCV preprocess,
ThreadPoolExecutor for parallel LLM calls, Azure Blob for storage,
React HITL UI for human review.

## Quality

About 95% field accuracy on 200+ US healthcare forms. Failures go to HITL,
not silent wrong writes — same philosophy as approval gates on side-effectful agent tools.

## Why structured outputs matter

Vision model output must land in a Pydantic schema before DB write.
Prompt-only JSON is not enough when a wrong field corrupts a medical record.
