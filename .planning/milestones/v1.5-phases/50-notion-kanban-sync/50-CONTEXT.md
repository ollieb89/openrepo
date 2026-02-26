# Phase 50: Notion Kanban Sync - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

A reactive L2-level skill that mirrors OpenClaw state to a Notion kanban board as a read-only visibility layer, covering both dev projects and life areas. Includes event bus infrastructure, Notion DB bootstrap, event sync, conversational capture, reconciliation, and hardening. Full end-to-end delivery in one phase.

Bidirectional sync (Notion → OpenClaw), calendar integration, habit tracking, financial data ingestion, sub-task hierarchy, and dashboard integration are out of scope.

</domain>

<decisions>
## Implementation Decisions

### Event Hook Wiring
- Event bus / hook registry pattern — components emit events to a central registry, listeners subscribe
- Fire-and-forget emission — Notion sync failure never blocks orchestration. Errors logged, not propagated
- Claude's discretion on module placement (new `event_bus.py` vs extending existing module)
- Failed events persisted for retry (small queue file), not just logged and lost. Reconcile covers gaps but retry queue improves reliability

### Notion API Interaction
- Use existing Notion MCP tools (notion-search, notion-create-pages, notion-update-page) — no custom HTTP client
- Skill runs inside agent context where MCP tools are already available (same as other L2 skills)
- NOTION_TOKEN stored as environment variable — standard secret management pattern
- Persist discovered Notion DB IDs to `skills/notion-kanban-sync/config.json` across sessions — avoid re-discovering on every invocation

### Conversational Capture UX
- Keyword detection for routing — ClawdiaPrime detects capture intent from natural language ("remind me to", "add task", "I need to")
- Silent creation with summary — create card immediately, show brief confirmation: "Added 'Renew gym' to Health / This Week"
- Ambiguous area inference: best guess + tag as uncertain (e.g., note "(area inferred)") — user corrects in Notion if wrong
- Batch input supported — parse comma-separated or listed items in one message ("Add: gym, taxes, call mom")

### Phasing & Rollout
- All 6 internal phases (plumbing, schema, event sync, capture, reconcile, hardening) covered in this single GSD phase
- New milestone — not appended to v1.5 Config Consolidation. Notion sync is a new capability
- Independent of v1.5 — no dependency on config consolidation completing first
- Event bus infrastructure built inline as part of this phase, not a separate prerequisite phase

### Claude's Discretion
- Event bus module placement and internal architecture
- Rate limiting wrapper implementation details
- Area keyword matching algorithm specifics
- Exact retry queue format and cleanup strategy
- Reconcile scheduling mechanism

</decisions>

<specifics>
## Specific Ideas

- SPEC.md at `.planning/phases/50-notion-kanban-sync/SPEC.md` contains the full detailed spec with 12 decisions, Notion DB schemas (Projects DB + Cards DB), event-to-mutation mappings, field ownership matrix, idempotency/dedupe key model, status ownership carve-out rules, discovery/bootstrap flow, and error handling strategy
- The spec is the authoritative reference for schema design, event envelopes, and mutation logic — downstream agents should read it directly

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 50-notion-kanban-sync*
*Context gathered: 2026-02-25*
