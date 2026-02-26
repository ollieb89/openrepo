# Phase 07: Risk Drift Intelligence - Research

**Researched:** 2025-05-22
**Domain:** LLM-based automated reconciliation and drift detection
**Confidence:** HIGH

## Summary

This phase implements a "Drift Guard" system that monitors the gap between natural language decisions (Slack) and structured project states (GitHub/Linear). The core challenge is mapping unstructured "intent" to structured "reality" at scale. Research indicates that the most effective approach is **Retrieval-Augmented Reconciliation (RAR)**, which uses vector search for candidate linking and LLM-based Natural Language Inference (NLI) for contradiction detection.

**Primary recommendation:** Use a tiered audit pipeline: Embedding-based pre-filtering (cheap) -> Structured extraction (Zod) -> NLI Comparison with Chain-of-Thought reasoning (high-quality).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Immediate Auditing**: New Slack decisions trigger audits against linked items immediately.
- **Tracker Updates**: GitHub/Linear updates trigger re-audits of related decisions.
- **Transparency**: The "Contradiction Reason" must be exposed to the user.
- **Low-Confidence Display**: Show low-confidence risks as "Potential Risk" or "Needs Review".
- **User Sensitivity Control**: A "Risk Sensitivity" slider (1-10) defines the confidence threshold.
- **Missing Data Alerts**: Flag if a decision (e.g., deadline) is missing from the tracker.
- **30-Day TTL**: Only audit Slack decisions < 30 days old.
- **Ephemeral Resolution**: Delete risk alerts once reconciled/fixed.

### Claude's Discretion
- LLM prompt strategies for "Decision vs. Tracker" contradiction detection and scoring.
- Implementation of the audit pipeline and risk scoring engine.

### Deferred Ideas (OUT OF SCOPE)
- Global tuning of the auditing engine based on "Not a Contradiction" feedback.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REAS-06 | Decision-to-Tracker Comparison pipeline | Retrieval-Augmented Reconciliation (RAR) pattern |
| REAS-07 | Contradiction Scoring (Dates, Status, etc.) | NLI-based scoring with field-level weights |
| REAS-08 | Actionable Insight Generation | Chain-of-Thought (CoT) reasoning for "Contradiction Reason" |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zod` | ^3.23 | Structured extraction | Best-in-class for TS schema validation and LLM structured output. |
| `fuzzball` | ^2.1 | Entity Resolution | High-performance fuzzy string matching for mapping names/labels. |
| `deep-object-diff` | ^1.1 | State Comparison | Identifies exact field-level changes between extraction snapshots. |
| `openai/anthropic` | latest | NLI Engine | GPT-4o-mini is SOTA for cost-effective logical comparison. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `date-fns` | ^3.6 | Date normalization | Comparing "Friday" vs "2024-05-24". |
| `p-limit` | ^5.0 | Concurrency control | Managing bulk audits without hitting rate limits. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fuzzball` | `string-similarity` | Fuzzball has better support for partial matching (useful for Slack names). |
| `deep-object-diff` | `deepdiff` | `deep-object-diff` is lighter and more idiomatic for TS. |

**Installation:**
```bash
npm install zod fuzzball deep-object-diff date-fns p-limit
```

## Architecture Patterns

### Recommended Project Structure: "The Drift Guard Pipeline"
```
src/lib/risk/
├── pipeline.ts       # Orchestrator (Trigger -> Fetch -> Compare -> Alert)
├── extraction.ts     # Maps Slack/GitHub data to shared Zod schemas
├── comparison.ts     # LLM logic for NLI and contradiction detection
├── entity-resolver.ts # Fuzzy mapping for users/labels
└── scoring.ts        # Normalizes sensitivity and confidence
```

### Pattern 1: Retrieval-Augmented Reconciliation (RAR)
**What:** Instead of auditing every message against every ticket, use vector embeddings to link Slack decisions to specific tracker items *before* running the LLM audit.
**When to use:** All real-time triggers to keep costs low.
**Workflow:**
1. **Embed** the Slack message.
2. **Search** Vector DB for relevant Tracker items (GitHub issues).
3. **Filter** candidates by similarity > 0.7.
4. **Compare** only the linked pairs using the LLM.

### Pattern 2: Multi-Stage Contradiction Scoring
**What:** Combine heuristic scoring (exact mismatches) with LLM-based semantic scoring.
**Formula:** `Final Score = (Heuristic Conflict * 0.4) + (LLM NLI Score * 0.6)`
- **Heuristic:** Boolean (1 or 0) for Date/Status/Assignee mismatch.
- **LLM NLI:** Continuous (0.0 to 1.0) based on "Entailment" vs "Contradiction".

### Anti-Patterns to Avoid
- **Hand-rolling Name Matching:** Don't write `name.toLowerCase() === slackName.toLowerCase()`. Use `fuzzball`.
- **Global Re-Audits on Every Message:** Never audit the whole project for a single Slack message. Use the RAR pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string matching | Custom regex/levenshtein | `fuzzball` | Handles partial matches and weighted scoring out of the box. |
| Deep object diffing | Recursive comparison logic | `deep-object-diff` | Handles edge cases in object trees (dates, arrays). |
| Structured extraction | Raw prompt with "JSON only" | `zod` + JSON mode | Guarantees schema compliance and type safety. |

**Key insight:** The complexity of "Decision vs Reality" lies in the **normalization** layer. Hand-rolling date parsing or entity resolution will lead to high false-positive rates.

## Common Pitfalls

### Pitfall 1: The "I vs Bob" Identity Crisis
**What goes wrong:** Slack decision says "I'll do it," but GitHub says `@bob`. The system flags a contradiction.
**Why it happens:** Failure to resolve the Slack `user_id` to the GitHub `username`.
**How to avoid:** Maintain an `identity_map` or use fuzzy matching on display names as a fallback.

### Pitfall 2: Temporal Drift (Date Formats)
**What goes wrong:** Slack says "Next Friday," GitHub says "2024-05-31". LLM might fail if not given the "Current Date" context.
**How to avoid:** Always inject `current_date` into the prompt and normalize GitHub dates via `date-fns`.

### Pitfall 3: Sentiment False Positives
**What goes wrong:** LLM flags "Let's *maybe* move it" as a contradiction to the current date.
**How to avoid:** Use a "Confidence threshold" and only alert if the LLM is > 80% sure the decision is *final*.

## Code Examples

### Structured Comparison Pattern (Zod)
```typescript
import { z } from 'zod';
import { diff } from 'deep-object-diff';

const ProjectStateSchema = z.object({
  assignee: z.string().optional(),
  due_date: z.string().optional(),
  priority: z.enum(['low', 'medium', 'high']).optional(),
  status: z.string(),
});

type ProjectState = z.infer<typeof ProjectStateSchema>;

function detectDirectDrift(decision: ProjectState, reality: ProjectState) {
  // Use deep-object-diff to find structural changes
  const changes = diff(reality, decision);
  return Object.keys(changes).length > 0 ? changes : null;
}
```

### NLI Contradiction Prompt Pattern
```typescript
const CONTRADICTION_PROMPT = `
Compare the DECISION from a conversation with the TRACKER_STATE from a ticket.
Identify if the tracker state CONTRADICTS the decision.

DECISION: "{decisionText}"
TRACKER_STATE: {trackerJson}
CONTEXT_DATE: {currentDate}

Output format:
{
  "isContradiction": boolean,
  "confidence": 0-1,
  "reason": "Explain the contradiction in 1 sentence.",
  "severity": "low" | "medium" | "high"
}
`;
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword matching | NLI (Natural Language Inference) | 2023 (LLM) | Can detect "Priority" drift even if words don't match exactly. |
| Manual reconciliation | RAR (Retrieval-Augmented Recon) | 2024 (RAG) | Drastically reduces costs by avoiding O(N*M) LLM calls. |

## Open Questions

1. **How to handle "Scope Drift"?**
   - What we know: LLMs can detect if a description changes.
   - What's unclear: How to quantify "Scope" in a way that doesn't trigger on minor rewordings.
   - Recommendation: Use a higher threshold (Sensitivity < 5) for Scope-only alerts.

## Sources

### Primary (HIGH confidence)
- **DeepEval Documentation** - Hallucination/Contradiction metrics patterns.
- **Promptfoo Documentation** - Semantic similarity and NLI assertions.
- **LLM Research Papers (NLI)** - Standard patterns for Entailment vs Contradiction.

### Secondary (MEDIUM confidence)
- **GitHub/Linear API Specs** - Field types and webhook trigger patterns.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Very stable libraries.
- Architecture: HIGH - RAR is the industry standard for reconciliation at scale.
- Pitfalls: MEDIUM - Based on common RAG/Audit system failures.

**Research date:** 2025-05-22
**Valid until:** 2025-08-22 (3 months)
