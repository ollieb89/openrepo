# Phase 42: Delta Snapshots - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimise pre-spawn memory retrieval and snapshot storage. The memory client fetches only memories created after the last successful retrieval (cursor-based), and snapshot history is bounded per project by a configurable `max_snapshots` limit. No new UI surfaces — this is a backend performance and housekeeping phase.

</domain>

<decisions>
## Implementation Decisions

### Cursor scope & location
- Cursor is **per-project** — one timestamp shared across all agents in the same project
- Stored under `metadata.memory_cursors` in `workspace-state.json` (nested in existing metadata block, not top-level)
- Cursor is updated **after a successful fetch** — never before. Failed or incomplete fetches leave the cursor unchanged so the next spawn retries the same time window

### Cursor error handling
- If the cursor value is malformed or unparseable: **log a warning and fall back to a full fetch**
- Corrupt cursor does not abort the spawn — graceful degradation, worst case is one extra full fetch before the cursor is repaired

### Snapshot pruning configuration
- `max_snapshots` is **opt-in only** — no default value. Pruning is inactive unless explicitly set in `project.json:l3_overrides.max_snapshots`
- Existing projects retain current (unlimited) behaviour without any change

### Pruning trigger
- Prune check runs **after each L2 review**, when a new snapshot is written to disk
- No separate startup job — check-and-prune happens inline during the review commit path

### Prune ordering & atomicity
- Delete **oldest snapshots first** (by filename/timestamp), keeping the newest N files
- If a prune partially fails (some `.diff` files can't be deleted): **log the error, leave remaining intact** — best-effort housekeeping, do not block the review flow
- Temporary limit breach is acceptable if filesystem permissions fail

### Claude's Discretion
- Exact key name within `metadata.memory_cursors` (e.g., flat string vs nested object if we ever need per-retrieval metadata)
- SHA-based vs timestamp-based cursor identity (requirement specifies ISO timestamp; implementation detail is Claude's)
- How to list snapshot files for oldest-first ordering (mtime vs filename sort)

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches within the constraints above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 42-delta-snapshots*
*Context gathered: 2026-02-24*
