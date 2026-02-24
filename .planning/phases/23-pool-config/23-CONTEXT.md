# Phase 23: Per-Project Pool Config - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Each project can declare its own concurrency limit, pool isolation mode, and overflow behavior in project.json — no code changes required to adjust. This phase makes `PoolRegistry` and `L3ContainerPool` config-driven instead of hardcoded.

</domain>

<decisions>
## Implementation Decisions

### Config Schema Design
- Extend existing `l3_overrides` block in project.json (don't create a separate top-level key)
- New keys: `max_concurrent` (integer), `pool_mode` ("shared" | "isolated"), `overflow_policy` ("reject" | "wait" | "priority")
- Also add `queue_timeout_s` (integer) for configurable wait timeout
- Naming matches existing codebase conventions (e.g., max_concurrent matches L3ContainerPool parameter)

### Default Behavior
- `max_concurrent` defaults to 3 (matches current hardcoded behavior — backward compatible)
- `pool_mode` defaults to "shared" (projects share the global pool by default)
- `overflow_policy` defaults to "wait" (matches current semaphore blocking behavior)
- Projects with no pool config in l3_overrides behave exactly as they do today

### Overflow Policies
- **reject**: Immediate error with detailed info — slot count, running task IDs, suggestion to retry later
- **wait**: Queue the task, wait for a slot up to `queue_timeout_s` (configurable, sensible default e.g. 300s), then reject on timeout
- **priority**: Priority queue wrapper replaces simple semaphore FIFO — priority tasks jump ahead of standard-priority queued tasks (no preemption of running tasks)

### Hot-Reload Semantics
- Read project.json fresh on every `spawn_and_monitor` call — always up-to-date, tiny I/O cost
- Config changes enforced on next spawn only — running containers keep running under their original config
- Pool mode changes (shared→isolated or vice versa) also apply on next spawn only — no disruption to running containers
- When max_concurrent changes mid-flight (e.g., 3→1 while 2 running), running containers continue; new spawns respect updated limit; semaphore recreated with new value

### Validation
- Invalid config values (negative max_concurrent, unknown overflow_policy, etc.) log a warning and fall back to defaults — don't crash or block spawns

### Claude's Discretion
- Whether to add a global defaults section in openclaw.json or keep defaults hardcoded in code
- Default value for `queue_timeout_s`
- Internal priority queue implementation details

</decisions>

<specifics>
## Specific Ideas

- Example target project.json shape:
  ```json
  "l3_overrides": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"],
    "max_concurrent": 1,
    "pool_mode": "isolated",
    "overflow_policy": "reject"
  }
  ```
- PoolRegistry.get_pool() should read config fresh and update the pool instance if config changed since last spawn
- Shared mode projects share a global semaphore; isolated mode projects get their own dedicated pool/semaphore

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 23-pool-config*
*Context gathered: 2026-02-24*
