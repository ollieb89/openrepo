# Phase 43: v1.4 Gap Closure - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix three specific gaps identified by the v1.4 milestone audit — two broken dashboard subprocess path calls and one missing production wiring. No new features:
1. `POST /api/suggestions` calls `suggest.py` at wrong path → ENOENT, pattern analysis cannot be triggered from dashboard
2. `rerenderSoul()` calls `soul_renderer.py` at wrong path → error swallowed silently, SOUL.md never updated after suggestion accept
3. `register_shutdown_handler()` is implemented and tested but has zero call sites in production — SIGTERM drain guarantee does not hold at runtime

</domain>

<decisions>
## Implementation Decisions

### Path resolution strategy
- Use `OPENCLAW_ROOT` as the base, appending the correct subpaths:
  - `suggest.py` → `packages/orchestration/src/openclaw/cli/suggest.py`
  - `soul_renderer.py` → `packages/orchestration/src/openclaw/soul_renderer.py`
- Define a single `ORCHESTRATION_ROOT` constant in the route file (e.g. `path.join(OPENCLAW_ROOT, 'packages/orchestration/src/openclaw')`) and reference it in both routes — reduces duplication without creating new files or abstractions
- On subprocess failure (script not found, non-zero exit), return HTTP 500 with stderr output — makes failures visible to operators; do not swallow errors
- Add a one-time startup check that logs WARN if the script paths don't exist on disk — catches misconfiguration early without failing hard

### Shutdown handler placement
- Call `register_shutdown_handler()` inside `spawn_task()` only — single call site, matches the existing production entry point
- Add an idempotent guard (module-level `_shutdown_handler_registered` flag) so repeated calls to `register_shutdown_handler()` are a no-op — safe if `spawn_task()` is ever called more than once
- Log at DEBUG level (`'SIGTERM drain handler registered'`) when the handler is wired — visible with debug logging, silent in normal operation
- Add a regression test that verifies `register_shutdown_handler()` is called from `spawn_task()` — prevents the "implemented but not wired" class of bug from recurring

### Claude's Discretion
- Exact structure of the startup path-existence check (module-level init vs. lazy first-request check)
- Whether `ORCHESTRATION_ROOT` constant belongs in the suggestions route file or a shared API utils file
- Python subprocess invocation details (child_process.execFile vs spawn, buffering)

</decisions>

<specifics>
## Specific Ideas

- The audit evidence is authoritative: broken paths are `OPENCLAW_ROOT/orchestration/suggest.py` and `OPENCLAW_ROOT/orchestration/soul_renderer.py` — correct paths confirmed in audit report
- Keep the fix minimal — `ORCHESTRATION_ROOT` constant + corrected subpaths + 500 error surfacing + startup warning. No new abstraction layers.
- The wiring test for `register_shutdown_handler()` should be a simple mock/spy — the drain behavior itself is already tested in existing test suite

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 43-v1.4-gap-closure*
*Context gathered: 2026-02-25*
