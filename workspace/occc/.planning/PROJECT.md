# Nexus-Sync

## What This Is

Nexus-Sync is an intelligent context bridge for knowledge workers who operate across chat and project tools. It creates a unified project context layer that links conversations, tickets, and decisions so teams stop losing time to tab switching. The MVP focuses on Slack plus GitHub/Linear workflows with a local-first desktop agent.

## Core Value

A user can ask one question and reliably understand what changed across communication and project systems for a feature.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Summarize key decisions from active chat threads into project context.
- [ ] Suggest bidirectional links between relevant chats and existing GitHub/Linear work items.
- [ ] Provide a natural-language catch-up query across integrated sources.
- [ ] Preserve privacy with local processing or encrypted transit only.

### Out of Scope

- Calendar, meeting transcription, and voice assistant workflows — not core to MVP context sync.
- Broad multi-platform support beyond Slack + GitHub/Linear — defer until quality is proven on core integrations.

## Context

The current workflow pain is context fragmentation between Slack, email, Discord, and planning tools like Linear/Notion/Jira. The initial product direction is a lightweight middleware approach, not a full replacement UI. The first implementation target is a desktop agent using Rust/Tauri with low CPU overhead and strict privacy defaults.

## Constraints

- **Privacy**: No training on customer data — protect trust and meet enterprise expectations.
- **Architecture**: Rust/Tauri desktop agent — low overhead and strong local execution model.
- **Integration Scope**: Slack + GitHub/Linear first — keep MVP shippable and testable.
- **Performance**: Continuous listening must stay unobtrusive — background CPU and memory usage must remain low.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Build local-first middleware rather than cloud-only service | Privacy and latency are core product constraints | — Pending |
| Start with Slack + GitHub/Linear integrations | Highest leverage workflow pair for MVP validation | — Pending |
| Prioritize "Catch Me Up" as primary user-facing capability | Directly targets tab-switching tax and context loss | — Pending |

---
*Last updated: 2026-02-24 after initialization*
