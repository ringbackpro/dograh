# DECISION LOG

## 2026-05-26
date: 2026-05-26
decision: Native auto transition mode implemented for Dograh workflow edges
reason: BOARD approved the native GAP-2 fix to replace Retell skip_response_edge behavior without relying on prompt workarounds.
outcome: Added `transition_mode` with `llm`, `auto`, `timer`, and `external_event` values; implemented runtime-owned auto transition traversal after full bot speech; added interruption abort, duplicate-frame protection flags, LLM context stitching, dead-path warnings, telemetry counters, and focused tests. Implementation and tests were committed separately. Test execution was blocked in this environment because `pytest` is not installed.
