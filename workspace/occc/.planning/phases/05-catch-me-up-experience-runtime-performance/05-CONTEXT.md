# Phase 05 Context: Catch Me Up Experience

## Overview
Phase 5 unifies the privacy-first core, source connectivity, and decision extraction into a natural-language "Catch Me Up" query interface. It focuses on synthesizing recent project activity into a verifiable timeline while maintaining low runtime overhead.

## Interaction Model Decisions (Area 1)
- **Low-Confidence Fallback:** When vector similarity scores are low, the UI will present a **Clarification Picker** showing the top 3 fuzzy matches, allowing the user to explicitly select the intended context rather than performing a noisy global search.
- **Remote Inference Escalation:** The experience remains **Strictly Local-First** by default. An optional **"Enhance with Cloud" toggle** will be available for cases where the retrieved context size exceeds the local model's (Phi-3) context window, requiring explicit user action.
- **Result Persistence:** Summaries are **Ephemeral** by default (lost on refresh). Users can use a **"Pin to Project"** action to save a specific summary as a permanent "Project Insight" artifact in the database.
- **Response Delivery:** Responses must **Stream (Token-by-Token)** to provide immediate feedback and allow users to interrupt generation if the synthesis diverges from their intent.

## Natural Language Scoping Logic (Area 4)
- **Implicit Context Weighting:** A **+0.3 score boost** is applied to records matching the currently active `projectId` in the UI. A "Search everywhere" escape hatch will be provided in the interface.
- **Temporal Operator Parsing:** Use **chrono-node** (hard-coded parser) to extract date ranges from the user's string *before* the vector search. This pre-filters the SQL query to improve both performance and accuracy.
- **Ambiguity Resolution:** If a query matches multiple distinct entities (e.g., two different APIs), the system will **summarize both into a unified timeline** using clear visual headers to separate the contexts.
- **Default Look-back Window:** Queries without explicit temporal context will default to the **Last 7 Days**.

## Intent Metadata Interface
Implementation plans should utilize the following structure for intent parsing:

```typescript
interface IntentMetadata {
  query: string;
  timeRange: {
    start: string | null; // ISO Date
    end: string | null;   // ISO Date
  };
  boostedProjectId: string | null;
  limit: number; // Default based on look-back
}
```

## Performance Targets
- **Interactive Responsiveness:** "Catch Me Up" queries should begin streaming within 2 seconds of the request.
- **Background Overhead:** Idle background sync and listening must remain below 5% CPU usage on standard developer hardware.
