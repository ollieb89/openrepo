---
phase: 05-catch-me-up-experience-runtime-performance
plan: 02
subsystem: synthesis-engine
tags: [llm, rag, streaming, synthesis, confidence]
requires:
  - phase: 05-catch-me-up-experience-runtime-performance
    plan: 01
    provides: intent parsing and filtered retrieval
provides:
  - Streaming RAG pipeline for natural language catch-up
  - Synthesis prompt for multi-source verified timelines
  - Low-confidence detection for ambiguity resolution
  - API endpoint at /api/sync/catch-up using NDJSON streaming
affects: [ollama, synthesis, catch-up-api]
tech-stack:
  added: []
  patterns: [streaming-rag, confidence-gating, ndjson-responses]
key-files:
  created:
    - src/lib/sync/synthesis.ts
    - src/app/api/sync/catch-up/route.ts
  modified:
    - src/lib/ollama.ts
key-decisions:
  - "Implemented `streamCompletion` in the Ollama bridge to enable token-by-token feedback, improving perceived responsiveness."
  - "Set a confidence threshold of 0.4 on the top match score; queries below this threshold bypass synthesis and trigger the Clarification Picker via the API response."
  - "Used NDJSON (Newline Delimited JSON) for the streaming API to allow mixing structured metadata (context records) with raw LLM tokens."
requirements-completed: [CMEU-02, PERF-01]
duration: 60 min
completed: 2026-02-24
---

# Phase 05 Plan 02: Streaming RAG & Synthesis Summary

**The synthesis engine is now live, enabling the "Catch Me Up" experience to transform raw project data into a cohesive, streaming natural language timeline.**

## Accomplishments
- **Streaming LLM:** Extended the Ollama bridge with `streamCompletion` support, allowing for immediate token delivery to the frontend.
- **Verification-First Synthesis:** Designed a synthesis prompt that enforces chronological grouping and explicit source citations ([Slack]/[Linear]) for every claim.
- **Ambiguity Guard:** Implemented confidence-based gating that identifies vague queries and returns matched candidates for clarification instead of attempting to summarize low-quality data.
- **Modern API:** Built a high-performance streaming endpoint using `ReadableStream` and NDJSON to deliver a rich, interactive experience.

## Decisions Made
- **Prompt Isolation:** Kept the synthesis logic in a dedicated `synthesis.ts` service to allow for prompt tuning and model swapping without touching the API route.
- **Context Metadata:** The stream starts by sending a `metadata` chunk containing the source record IDs, allowing the UI to highlight or link to the cited records immediately.

## Next Phase Readiness
- The backend is now fully capable of processing catch-up queries.
- Ready for **Plan 05-03 (The "Catch Me Up" UI)** to provide the final user surface for this feature.
