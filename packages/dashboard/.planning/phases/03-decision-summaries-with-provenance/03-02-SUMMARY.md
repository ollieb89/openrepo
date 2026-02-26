---
phase: 03-decision-summaries-with-provenance
plan: 02
subsystem: extraction-engine
tags: [llm, ollama, phi-3, decisions, summarization]
requires:
  - phase: 03-decision-summaries-with-provenance
    plan: 01
    provides: storage and data models
provides:
  - Local LLM bridge to Ollama/Phi-3
  - Chain-of-Thought extraction logic for thread decisions
  - Entity hoisting for Slack mentions and Linear IDs
  - Automated summarization runner triggered by sync
affects: [sync-engine, summarizer, ollama]
tech-stack:
  added: [ollama-js]
  patterns: [cot-extraction, citation-validation]
key-files:
  created:
    - src/lib/ollama.ts
    - src/lib/sync/summarizer.ts
    - src/lib/ollama.test.ts
    - src/lib/sync/summarizer.test.ts
  modified:
    - src/lib/sync/engine.ts
    - package.json
key-decisions:
  - "Used Phi-3 Mini (3.8B) as the default local model for its high performance-to-size ratio on reasoning tasks."
  - "Implemented a 'Smoking Gun' citation validation step: if the LLM-extracted citation doesn't exist in the raw source text, the decision block is rejected to prevent hallucinations."
  - "Integrated the summarizer directly into the sync engine's source loop to ensure local context is updated immediately after ingestion."
requirements-completed: [SUMM-01, SUMM-02]
duration: 45 min
completed: 2026-02-24
---

# Phase 03 Plan 02: Local Decision Extraction Engine Summary

**The Local Decision Extraction Engine is now operational, enabling the automated transformation of raw Slack threads into structured decisions using local LLM inference.**

## Accomplishments
- **Ollama Integration:** Established a robust bridge to local Ollama instances, verified with unit tests.
- **CoT Extraction:** Implemented a sophisticated Chain-of-Thought prompt that extracts outcomes, participants, and next steps with high reliability.
- **Provenance & Validation:** Added entity hoisting for Linear/Slack IDs and a critical citation validation step to ensure summary trust.
- **Background Automation:** Wired the summarization runner into the background sync engine, making decision extraction a seamless part of the ingestion pipeline.

## Decisions Made
- **Local-First LLM:** Chose Phi-3 via Ollama to strictly adhere to Phase 1 privacy mandates; no data leaves the user's machine during summarization.
- **Implicit Summarization:** Decisions are extracted per thread during the sync cycle, ensuring that "Catch Me Up" queries have immediate access to recent consensus.

## Next Phase Readiness
- The system is now generating structured decisions in local storage.
- Ready for **Plan 03-03 (Decision Log UI and Correction Loop)** to provide the user-facing surface for these summaries.
