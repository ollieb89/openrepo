# Phase 3: Decision Summaries with Provenance - Research

**Researched:** 2026-02-24
**Domain:** Local-first LLM Summarization, Entity Extraction, UI/UX for Provenance
**Confidence:** HIGH

## Summary

Phase 3 focuses on transforming Slack threads into actionable, verifiable "Decision Cards". The primary technical challenge is detecting consensus ("Convergent Evolution") using local-first models to maintain privacy (PRIV-02). We recommend **Phi-3-mini** (3.8B) via **Ollama** for its superior reasoning-to-size ratio, capable of running on most developer laptops with < 3GB VRAM.

The system will use a **Chain-of-Thought (CoT)** prompt strategy to identify proposals, debate, and final resolutions. To ensure trust, every decision card will feature a "Citation Snippet"—the exact quote that triggered the extraction—linked directly to the Slack desktop client via `slack://` protocols.

**Primary recommendation:** Use Phi-3-mini (quantized) via Ollama with a structured CoT prompt to extract "Inferred Resolutions", prioritizing the "smoking gun" citation for user verification.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Defining a Decision:** Use "Inferred Resolution" (Convergent Evolution). Identify when a question is posed, options are debated, and consensus emerges.
- **Breadth of Outcomes:** Capture "Hard Decisions" and "Actionable Next Steps". Ignore general "let's look into it" noise.
- **Entity Association:** Prioritize and hoist Linear IDs (`PROJ-123`) and `@user` mentions.
- **Temporal Relevance:** Use a "Sliding Window" (48–72 hours) for daily feeds; "On-Demand Retro" for history.
- **Grouping Strategy:** Atomic Items. One thread = multiple decision cards if needed.
- **Detail Depth:** Bulleted List: **Outcome**, **Participants**, **Next Step**.
- **Link Granularity:** Start of Thread (Slack desktop protocol `slack://`).
- **Private Channel Access:** "Show Summary, Hide Link" for unauthorized users.
- **Citation Snippets:** Include the specific message quote in the card.
- **Correction Scope:** Global hide for the project. "Try Again" with user hints.

### Claude's Discretion
- Research options and recommend local models vs. remote privacy-preserving options.
- UI/UX patterns for citation snippets and restricted states.

### Deferred Ideas (OUT OF SCOPE)
- Autonomous Write-back to Slack/Linear.
- Multi-Source Cross-Referencing (linking Slack to Linear in one item).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SUMM-01 | User can view AI-generated summaries of key decisions from Slack threads. | Phi-3-mini reasoning for "Inferred Resolution" detection. |
| SUMM-02 | Each summary includes source references (links, timestamps). | `slack://` protocol and "Citation Snippet" pattern. |
| SUMM-03 | User can mark a summary as incorrect and hide it. | Global hide logic and "Try Again with Hints" prompt pattern. |
| PRIV-01 | Raw content processing and embeddings run locally by default. | Local Ollama execution of Phi-3. |
| PRIV-02 | Remote inference must use encrypted transit and opt-in. | Recommendation for local-first; remote only as opt-in fallback. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Ollama** | 0.1.x+ | LLM Runner | Standard for local-first LLM execution; supports Phi-3/Llama-3. |
| **Phi-3-mini** | 3.8B | Inference Model | Best-in-class reasoning for its size; fits in ~2.2GB VRAM. |
| **ollama-js** | Latest | API Client | Simple integration with Next.js/Node.js backend. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **@tauri-apps/plugin-shell** | Latest | Sidecar Control | If bundling Ollama as a Tauri sidecar binary. |
| **Lucide React** | Latest | UI Icons | For `Lock`, `ExternalLink`, `XCircle` icons. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ollama | Transformers.js | Transformers.js runs in-process but has limited support for 8B+ models compared to Ollama. |
| Phi-3-mini | Llama-3-8B | Llama-3-8B is more "knowledgeable" but requires 5GB+ VRAM and is slower for simple summarization. |

**Installation:**
```bash
# Ensure Ollama is installed locally
ollama pull phi3:mini
npm install ollama
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── lib/
│   ├── summarizer/
│   │   ├── prompt.ts       # CoT prompt definitions
│   │   ├── engine.ts       # Ollama interaction logic
│   │   └── extraction.ts   # Regex & metadata hoisting
├── components/
│   ├── decision-log/
│   │   ├── DecisionCard.tsx
│   │   ├── CitationSnippet.tsx
│   │   └── RestrictedBadge.tsx
```

### Pattern 1: Chain-of-Thought (CoT) Extraction
**What:** A multi-step prompt that instructs the model to think through the thread before outputting JSON.
**When to use:** Crucial for "Inferred Resolution" where consensus isn't explicit.
**Example:**
```typescript
const DECISION_PROMPT = `
Analyze the following Slack thread.
1. Identify all proposals made.
2. For each proposal, look for consensus (e.g., "Sounds good", "👍", "Agreed").
3. Extract final decisions where a resolution was reached.

Format as a list of decisions:
- Outcome: [Brief description]
- Participants: [@user1, @user2]
- Next Step: [Action item or "None"]
- Citation: [The exact sentence that confirms the decision]
- LinearID: [PROJ-123 if mentioned]

Thread:
{{thread_content}}
`;
```

### Pattern 2: Citation Snippet UX
**What:** A `blockquote` component that acts as the "smoking gun" proof.
**When to use:** Displayed in the expanded state of a Decision Card.
**Implementation:** Use a `slack://` deep link to open the exact thread in the desktop app.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM Quantization | Custom scripts | Ollama Library | Ollama handles model management, quantization, and cross-platform GPU acceleration. |
| Mention Parsing | Manual string split | Regex `<@U[A-Z0-9]+>` | Slack mention format is standardized; manual parsing is brittle. |
| Linear ID matching | Complex NLP | Regex `[A-Z0-9]{2,}-\d+` | Issue IDs are high-entropy and easily matched via RegEx. |

## Common Pitfalls

### Pitfall 1: Hallucinated Citations
**What goes wrong:** The LLM "invents" a quote that sounds like the decision but doesn't exist in the source.
**How to avoid:** Use the LLM to identify the *Index* of the message or a unique substring, then verify it exists in the original text before displaying the snippet.

### Pitfall 2: Context Window Overflow
**What goes wrong:** Long Slack threads (50+ messages) exceed the model's context window.
**How to avoid:** Chunk threads or use a "Summarize the Summary" approach for extremely long discussions.

### Pitfall 3: Slack Deep Link Failure
**What goes wrong:** `slack://` links fail if the user is on the web or has a different workspace ID.
**How to avoid:** Always include both `slack://channel?team=T...&id=...` and the standard `https://app.slack.com/...` web fallback.

## Code Examples

### Standard Regex Patterns
```typescript
// Source: Slack API Docs / Linear Best Practices
export const SLACK_USER_REGEX = /<@(U[A-Z0-9]+)>/g;
export const LINEAR_ID_REGEX = /([A-Z0-9]{2,}-\d+)/g;

// Helper to map mentions to names (assuming we have a local user map)
export const resolveMentions = (text: string, userMap: Record<string, string>) => {
  return text.replace(SLACK_USER_REGEX, (_, id) => userMap[id] || id);
};
```

### Citation Snippet Component (Tailwind)
```tsx
const CitationSnippet = ({ quote, url }: { quote: string, url: string }) => (
  <blockquote className="border-l-4 border-blue-500 bg-slate-50 p-3 my-2 dark:bg-slate-900">
    <p className="italic text-sm text-slate-700 dark:text-slate-300">"{quote}"</p>
    <a href={url} className="text-xs text-blue-600 hover:underline mt-1 block">
      View in Slack →
    </a>
  </blockquote>
);
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Keyword matching ("Decided:") | Semantic Consensus Detection | 2023 (LLM Boom) | Higher recall for "Inferred Resolutions". |
| Cloud-only (OpenAI) | Local SLMs (Phi-3) | 2024 (Phi-3 launch) | Full privacy for corporate Slack data. |

## Open Questions

1. **User Map Synchronization:**
   - What we know: We can sync users from Slack.
   - What's unclear: How to handle users who are no longer in the workspace but exist in historical summaries.
   - Recommendation: Store a "User Cache" in the local DB.

2. **Ollama Distribution:**
   - What we know: Tauri can sidecar Ollama.
   - What's unclear: Whether users find a 2GB download acceptable for the MVP.
   - Recommendation: Offer a "Remote (Encrypted)" opt-in during onboarding for users with low disk space.

## Sources

### Primary (HIGH confidence)
- **Microsoft Phi-3 Technical Report** - Benchmarks for reasoning and extraction.
- **Ollama API Documentation** - Integration patterns for Node/JS.
- **Slack Deep Linking Docs** - `slack://` protocol details.

### Secondary (MEDIUM confidence)
- **Linear API Docs** - Standard issue ID patterns.
- **Tauri Sidecar Guides** - Best practices for bundling external binaries.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Phi-3/Ollama is proven.
- Architecture: HIGH - CoT is standard for reasoning.
- Pitfalls: MEDIUM - Hallucinations are always a risk with LLMs.

**Research date:** 2026-02-24
**Valid until:** 2026-05-24 (Fast-moving LLM space)
