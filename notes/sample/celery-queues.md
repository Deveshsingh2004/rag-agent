# Celery queues at EdusmarkAI

## Topology

Five Celery queues. High-priority for interactive assessment paths.
Background queues for bulk PDF and OCR style work.

## Reliability knobs

`acks_late=True` and `prefetch=1` so a killed worker redelivers instead of silently dropping work.
Side-effectful tasks must be idempotent — same pattern as agent tools that send email.

## Dual-write onboarding

Two-database onboarding used a custom Django DB router, a MigrationJob state machine,
and dual-write with compensation on failure. Queue choice mattered: HP for user-visible
steps, BG for heavy backfill.
