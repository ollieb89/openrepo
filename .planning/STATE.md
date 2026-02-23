# Project State: OpenClaw

## Project Reference
**Core Value:** Hierarchical AI Swarm Orchestration (Grand Architect Protocol) with physical isolation and real-time monitoring.
**Current Focus:** v1.1 Project Agnostic — general-purpose multi-project framework.

See: .planning/PROJECT.md (updated 2026-02-23)

## Current Position
- **Milestone:** v1.1 Project Agnostic
- **Phase:** Not started (defining requirements)
- **Status:** Defining requirements
- **Last activity:** 2026-02-23 — Milestone v1.1 started

## Accumulated Context
### Decisions
- Adopted 3-tier hierarchy (L1/L2/L3) as the core architectural principle.
- Selected Next.js 16 (occc) for the dashboard.
- Enforced Docker-based isolation for all agent tiers.
- Migrated from Snap Docker to Native Docker 29.1.5 to support `no-new-privileges` isolation.
- CLI routing replaces lane queue REST API (accepted spec deviation).
- Jarvis Protocol state engine with thread-safe file locking.
- Semantic snapshot system with git staging branches.
- SSE stream emits full state object on change, not bare notification events.
- Quick-win project context layer landed: project.json manifests, project_config.py resolver, env var overrides.
- v1.1 SOUL approach: convention-over-configuration (default template + custom override per project).
- v1.1 L3 pool approach: configurable isolation (shared default, isolated opt-in per project).
- v1.1 CLI approach: `openclaw project` subcommand group with templates.
- v1.1 dashboard approach: project switcher dropdown, default to active project.

## Session Continuity
- **Last Action:** Started v1.1 milestone — gathering requirements.
- **Next Step:** Define requirements, then create roadmap.
