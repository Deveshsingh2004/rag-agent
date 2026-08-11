# SSE fanout at EdusmarkAI

## Problem

Teachers trigger bulk assessment generation. Students need live progress over Server-Sent Events.
A single Django worker holding open SSE sockets did not scale past a few hundred connections.

## Design

Redis pub/sub is the fanout bus. Each uvicorn worker subscribes to `user:{id}` on connect.
Celery tasks publish progress JSON. If a corporate proxy buffers SSE, clients fall back to
DB polling every 3 seconds keyed by `last_event_id`.

## Load reality

Design target was 50k concurrent. Load-tested to 2k concurrent on modest hardware.
Real peak traffic sat around 2–5k concurrent, not 50k.

## Failure modes

- Redis blip: clients reconnect; events are idempotent by event_id.
- DB poll fallback is slower but correct.
- Never put S3 I/O inside a database transaction.
