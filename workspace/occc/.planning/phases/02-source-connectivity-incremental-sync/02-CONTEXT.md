# Phase 2: Source Connectivity & Incremental Sync - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver reliable connectivity for one Slack workspace and one project tracker (GitHub Issues or Linear), then run incremental sync with resumable checkpoints and clear sync/health visibility. This phase clarifies operational behavior and user-facing status semantics within that fixed boundary.

</domain>

<decisions>
## Implementation Decisions

### Incremental Sync Behavior
- First sync must be user-scoped by time window, not forced full backfill. Provide a selectable window at setup (for example, last 30/90/all days) with a safe default favoring controlled initial load.
- Changed-record detection must include updates to existing records, not only newly created items (edits, state changes, reopen/close transitions, and newly added comments/messages).
- Sync operation must support both automatic periodic runs and a manual `Sync now` trigger.
- Interrupted sync must resume from the last confirmed checkpoint/cursor and avoid duplicate ingestion.
- Cursor/watermark semantics should be source-aware (Slack timestamp/thread cursor style; tracker `updated_at` style).

### Sync Progress Visibility
- Show sync status in two places: a dedicated sync dashboard and a compact always-visible status indicator in primary UI.
- Progress reporting should include per-connector and per-source counters; do not rely solely on percent-complete bars when total work is unknown.
- For long-running syncs, show persistent active-state progress with current step and throughput; ETA is best-effort only and must tolerate rate-limit variance.
- Completion/failure feedback must include transient notification plus persistent status card with actionable recovery controls.

### Health Status Semantics
- Connector state model is explicitly: `connected`, `syncing`, `rate_limited`, `auth_expired`, `error`, `disconnected`.
- Any provider 429 response should immediately transition connector state to `rate_limited` with pause/backoff behavior.
- Backoff policy should consume provider `Retry-After` when present; otherwise use exponential fallback windows.
- `auth_expired` is a hard block: stop sync, show explicit re-auth call-to-action, and retain last-successful-sync metadata for user reassurance.
- Status priority order is fixed for UI and action routing: `auth_expired` > `error` > `rate_limited` > `syncing` > `connected`.
- Compact status may use traffic-light semantics for glanceability (green healthy, blue syncing, yellow rate-limited, red action required).

### Claude's Discretion
- Exact visual treatment (icons, spacing, typography, card composition) for dashboard and compact indicators.
- Precise polling interval for periodic syncs, provided behavior remains consistent with the decisions above.
- Detailed wording of helper text/tooltips for progress and health states.

</decisions>

<specifics>
## Specific Ideas

- Use explicit counters and/or throughput indicators to reduce confusion in API-driven workloads where total count may be unknown at start.
- Design for constrained local resources by preventing surprise massive first-import behavior.
- Favor fail-fast + recover-gracefully connector semantics for auth and provider-limit scenarios.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-source-connectivity-incremental-sync*
*Context gathered: 2026-02-24*
