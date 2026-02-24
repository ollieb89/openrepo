# Phase 1: Local-First Core & Privacy Guardrails - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish local-first privacy behavior as the default product contract for Nexus-Sync: when remote inference is allowed, how consent is captured and revoked, and how users can verify what happened. This phase defines trust and control boundaries; it does not add new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Remote AI Opt-In UX
- Remote inference is offered only when local confidence is low.
- Consent is scoped per workspace/project (not global-only and not per-request).
- If user denies remote inference, Nexus-Sync returns a local-only result and explicitly notes remote could improve the output.
- Users can revoke or change consent from a central Privacy Settings surface with one-click revoke.

### Data Visibility & User Trust Signals
- Product includes a dedicated Privacy Center plus lightweight inline badges.
- Default provenance on generated summaries/answers includes source links, timestamps, and connector label.
- Remote inference events are visible in a filterable audit log.
- Any response that used remote inference must show an explicit badge and short reason.

### Claude's Discretion
- Exact UI wording and visual style for consent prompts, badges, and Privacy Center layout.
- Threshold logic used to determine "local confidence is low".
- Final filter taxonomy for the audit log.

</decisions>

<specifics>
## Specific Ideas

- Prefer low-friction operation with local-first defaults, while making remote usage explicit and reviewable.
- Keep transparency high without overwhelming users in day-to-day flows.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 01-local-first-core-privacy-guardrails*
*Context gathered: 2026-02-24*
