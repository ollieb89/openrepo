# Phase 3: Decision Summaries with Provenance - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform synced Slack threads into a chronological "Decision Log" and context-aware summaries. The goal is to produce trustworthy, atomic decision items that link back to their original sources, with built-in human-in-the-loop correction controls.

</domain>

<decisions>
## Implementation Decisions

### Extraction & Summarization Criteria
- **Defining a Decision:** Use "Inferred Resolution" (Convergent Evolution). Identify when a question is posed, options are debated, and consensus emerges (e.g., "Sounds good," 👍 reactions), even without explicit keywords like "we decided."
- **Breadth of Outcomes:** Capture "Hard Decisions" (project state changes) and "Actionable Next Steps" (soft decisions with a specific owner or "When"). General "let's look into it" without a name/date is ignored as noise.
- **Entity Association:** Explicitly prioritize and hoist Linear IDs (`PROJ-123`) and `@user` mentions into metadata for relational querying.
- **Temporal Relevance:** Use a "Sliding Window" (48–72 hours) for daily newsfeeds, but provide an "On-Demand Retro" (Deep Index) to scan historical synced data.

### Summary Presentation & Density
- **Primary Surface:** Hybrid. A dedicated "Decision Log" (chronological source of truth) + "Context Cards" surfacing in "Catch Me Up" results.
- **Grouping Strategy:** Atomic Items. One thread can yield multiple separate decision cards to allow granular linking.
- **Detail Depth:** Bulleted List. Standard format: **Outcome**, **Participants**, **Next Step**.
- **UI Density:** Collapsed by Default. Headline + Metadata view that expands on click to avoid "walls of text."

### Provenance & Source Linking
- **Link Granularity:** Start of Thread. Linking to the thread start provides the full narrative arc and context for the decision.
- **Link Target:** Dual-mode (Contextual). Prioritize `slack://` for desktop speed, but include a secondary Web link icon.
- **Private Channel Access:** "Show Summary, Hide Link." Show the summary to maintain project awareness, but replace the link with a "Source Restricted" badge if the user lacks access.
- **Citation Snippets:** Include the "smoking gun" quote (the specific message triggering extraction) directly in the card for instant verification.

### Correction & Hiding UX
- **Correction Scope:** Global. If a summary is incorrect, it is hidden for the entire project to maintain a single source of truth.
- **"Try Again" Logic:** Re-summarize with Hints. Allow users to provide specific context (e.g., "Focus on budget") when regenerating a summary.
- **Flagging vs. Deleting:** Removed from Active UI, Archived in Audit. Hidden items disappear from the feed but are stored in a "Hidden/Flagged" tab for admin review.
- **Feedback Loop:** Single-Click Reject ("❌") with an optional, low-friction pop-over for metadata (e.g., "Wrong owner?").

</decisions>

<specifics>
## Specific Ideas
- **Trust over Noise:** Prioritize extraction accuracy over volume. It is better to miss a minor decision than to hallucinate a false one.
- **Verifiability:** The "Citation Snippet" is the primary trust-building mechanism; it should be prominent in the expanded card view.
</specifics>

<deferred>
## Deferred Ideas
- **Autonomous Write-back:** Posting summaries back to Slack or Linear — defer to a later phase for safety.
- **Multi-Source Cross-Referencing:** Linking a Slack decision directly to a Linear update in the same summary — initially keep them as separate atomic items.
</deferred>

---

*Phase: 03-decision-summaries-with-provenance*
*Context gathered: 2026-02-24*
