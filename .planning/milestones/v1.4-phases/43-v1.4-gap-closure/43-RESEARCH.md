# Phase 43: v1.4 Gap Closure - Research

**Researched:** 2026-02-25
**Domain:** Bug fixes — two broken subprocess path strings in Next.js API routes, one missing Python call site in pool.py
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Path resolution strategy
- Use `OPENCLAW_ROOT` as the base, appending the correct subpaths:
  - `suggest.py` → `packages/orchestration/src/openclaw/cli/suggest.py`
  - `soul_renderer.py` → `packages/orchestration/src/openclaw/soul_renderer.py`
- Define a single `ORCHESTRATION_ROOT` constant in the route file (e.g. `path.join(OPENCLAW_ROOT, 'packages/orchestration/src/openclaw')`) and reference it in both routes — reduces duplication without creating new files or abstractions
- On subprocess failure (script not found, non-zero exit), return HTTP 500 with stderr output — makes failures visible to operators; do not swallow errors
- Add a one-time startup check that logs WARN if the script paths don't exist on disk — catches misconfiguration early without failing hard

#### Shutdown handler placement
- Call `register_shutdown_handler()` inside `spawn_task()` only — single call site, matches the existing production entry point
- Add an idempotent guard (module-level `_shutdown_handler_registered` flag) so repeated calls to `register_shutdown_handler()` are a no-op — safe if `spawn_task()` is ever called more than once
- Log at DEBUG level (`'SIGTERM drain handler registered'`) when the handler is wired — visible with debug logging, silent in normal operation
- Add a regression test that verifies `register_shutdown_handler()` is called from `spawn_task()` — prevents the "implemented but not wired" class of bug from recurring

### Claude's Discretion
- Exact structure of the startup path-existence check (module-level init vs. lazy first-request check)
- Whether `ORCHESTRATION_ROOT` constant belongs in the suggestions route file or a shared API utils file
- Python subprocess invocation details (child_process.execFile vs spawn, buffering)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ADV-01 | Pattern extraction engine queries memU for rejection clusters and identifies recurring failure patterns via frequency counting (threshold: ≥3 similar rejections within lookback window) | `suggest.py` exists at correct path; only dashboard trigger is broken. Fix is path string correction in route.ts:46 |
| ADV-02 | Suggestion generator produces concrete diff-style SOUL amendments with pattern description, evidence count, and exact text to add to soul-override.md | Blocked by ADV-01. `suggest.py` generates correct schema. Unblocked by same path fix. |
| ADV-03 | Pending suggestions stored in `workspace/.openclaw/<project_id>/soul-suggestions.json` | Blocked by ADV-01. Path helper is correct. Unblocked by same path fix. |
| ADV-04 | L2 acceptance flow reads pending suggestions and accepts (appends to soul-override.md, re-renders SOUL) or rejects (memorizes rejection reason) | Append works; `rerenderSoul()` fails silently. Fix is path string correction in action/route.ts:51 |
| REL-08 | Pending fire-and-forget asyncio memorization tasks are drained (gathered) on pool shutdown instead of silently lost | `register_shutdown_handler()` and `drain_pending_memorize_tasks()` exist and are fully tested. Fix is one call site: add `register_shutdown_handler(loop, pool)` in `spawn_task()` |
</phase_requirements>

---

## Summary

Phase 43 closes three specific gaps identified by the v1.4 milestone audit. All three gaps are wiring/path bugs, not missing features — the underlying implementations are correct and fully tested. This phase is purely corrective: two one-line path string fixes in TypeScript API routes and one call-site addition in Python.

**Gap 1 (ADV-01/02/03):** `packages/dashboard/src/app/api/suggestions/route.ts` line 46 constructs the path to `suggest.py` as `path.join(OPENCLAW_ROOT, 'orchestration', 'suggest.py')`. This path does not exist after the `packages/orchestration/` monorepo refactor. Correct path is `path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw', 'cli', 'suggest.py')`.

**Gap 2 (ADV-04):** `packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` line 51 in `rerenderSoul()` constructs the path to `soul_renderer.py` as `path.join(OPENCLAW_ROOT, 'orchestration', 'soul_renderer.py')`. This path does not exist. Error is caught and swallowed silently. Correct path is `path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw', 'soul_renderer.py')`. The accept action already appends correctly to `soul-override.md`; only the re-render step is broken.

**Gap 3 (REL-08):** `skills/spawn/pool.py` contains `register_shutdown_handler()` (line 1019) and `drain_pending_memorize_tasks()`, both fully implemented and covered by 6 passing tests. However, `spawn_task()` (the production entry point at line 1053) never calls `register_shutdown_handler()`. Adding one call inside `spawn_task()` after pool creation wires the drain guarantee at runtime.

**Primary recommendation:** Three surgical edits — two path string corrections in TypeScript, one function call addition in Python — plus a regression test for the call site. No new abstractions, no new files beyond the test.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Node.js `child_process.execFile` | stdlib (Node 18+) | Subprocess invocation for Python scripts from Next.js routes | Already used in route.ts:49; no alternative needed |
| `asyncio.get_running_loop()` | Python 3.7+ stdlib | Get event loop from inside async function | Required for `register_shutdown_handler()` — `loop.add_signal_handler()` needs the loop reference |
| Next.js App Router `route.ts` | 14.x | API route handlers for dashboard | Already established pattern |
| pytest + pytest-asyncio | pytest>=7.0, asyncio 1.3.0 | Regression test for wiring check | Existing test infrastructure, 147 tests pass |

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| `promisify(execFile)` | Node stdlib | Async wrapper for execFile | Already used in both routes; maintain consistency |
| `path.join(OPENCLAW_ROOT, ...)` | Node stdlib | Cross-platform path construction | Correct pattern — avoid template strings for paths |
| Module-level `_shutdown_handler_registered` flag | Python stdlib (bool) | Idempotency guard for handler registration | Required per CONTEXT.md to prevent double-registration if spawn_task() is called multiple times |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.get_running_loop()` inside spawn_task | Passing loop from asyncio.run() caller | get_running_loop() is simpler inside async context — no caller change needed |
| Module-level flag for idempotency | Closure flag inside register_shutdown_handler | Module-level flag works across multiple spawn_task() calls even if different loop instances |
| ORCHESTRATION_ROOT constant in each route file | Shared utils module | Route-local constant avoids creating new shared module; CONTEXT.md prefers minimal abstraction |

**Installation:** No new packages needed.

---

## Architecture Patterns

### Relevant File Locations
```
packages/dashboard/src/app/api/suggestions/
├── route.ts                    # Gap 1: fix orchestrationPath line 46
└── [id]/action/route.ts        # Gap 2: fix rerenderSoul() path line 51

skills/spawn/
└── pool.py                     # Gap 3: add register_shutdown_handler() call in spawn_task()

packages/orchestration/tests/
└── test_pool_shutdown.py       # Add regression test for spawn_task wiring
```

### Pattern 1: ORCHESTRATION_ROOT Constant (both routes)

**What:** Define one constant at module level that resolves the correct base for Python script paths.
**When to use:** Both routes reference Python scripts in the same package tree; one constant eliminates duplication and makes future path changes a single-line edit.

```typescript
// Source: CONTEXT.md locked decision
const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '~/.openclaw';
const ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw');
// Then:
const orchestrationPath = path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py');  // route.ts
const rendererPath = path.join(ORCHESTRATION_ROOT, 'soul_renderer.py');        // action/route.ts
```

### Pattern 2: Startup Path-Existence Check (route.ts)

**What:** Log a WARN at module load time if the script path doesn't exist on disk.
**When to use:** Module-level check (lazy first-request also acceptable per CONTEXT.md discretion). Catches misconfiguration without crashing.

```typescript
// Module-level startup check (runs when Next.js imports the route module)
import { existsSync } from 'fs';
if (!existsSync(path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py'))) {
  console.warn(`[suggestions] suggest.py not found at expected path: ${ORCHESTRATION_ROOT}/cli/suggest.py`);
}
```

### Pattern 3: register_shutdown_handler() in spawn_task()

**What:** Call `register_shutdown_handler()` inside the `spawn_task()` async function after pool creation, using `asyncio.get_running_loop()`.
**When to use:** Exactly once — inside spawn_task() before spawn_and_monitor() is called.

```python
# Source: CONTEXT.md locked decisions + pool.py existing pattern
async def spawn_task(...) -> Dict[str, Any]:
    ...
    pool = L3ContainerPool(max_concurrent=max_concurrent, project_id=project_id)
    pool._pool_config = pool_cfg
    await pool.run_recovery_scan()

    # Wire SIGTERM drain handler — uses get_running_loop() (safe inside async context)
    if not _shutdown_handler_registered:
        loop = asyncio.get_running_loop()
        register_shutdown_handler(loop, pool)
        # _shutdown_handler_registered flag update handled inside register_shutdown_handler
        logger.debug("SIGTERM drain handler registered")

    return await pool.spawn_and_monitor(...)
```

**Note on idempotency guard:** The `_fired` closure inside `register_shutdown_handler()` handles repeated SIGTERM signals, but the CONTEXT.md decision requires a module-level `_shutdown_handler_registered` flag to prevent `loop.add_signal_handler()` from being called multiple times across multiple `spawn_task()` invocations. The flag should be set inside `register_shutdown_handler()` itself.

### Pattern 4: Regression Test — spawn_task calls register_shutdown_handler

**What:** Unit test that patches `register_shutdown_handler` and `asyncio.get_running_loop`, calls `spawn_task()`, and asserts that `register_shutdown_handler` was called with the pool.
**When to use:** New test in `test_pool_shutdown.py` — prevents "implemented but not wired" regression.

```python
# Source: CONTEXT.md + existing test_pool_shutdown.py patterns
@pytest.mark.asyncio
async def test_spawn_task_wires_shutdown_handler():
    """spawn_task() must call register_shutdown_handler() — prevents wiring regression."""
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_pool = MagicMock()
    mock_pool.run_recovery_scan = AsyncMock()
    mock_pool.spawn_and_monitor = AsyncMock(return_value={"status": "ok"})
    mock_pool._pool_config = {}

    with patch("pool.L3ContainerPool", return_value=mock_pool), \
         patch("pool.register_shutdown_handler") as mock_register, \
         patch("pool.get_workspace_path", return_value="/tmp/workspace"), \
         patch("pool.get_active_project_id", return_value="test"), \
         patch("pool.get_pool_config", return_value={"max_concurrent": 3}), \
         patch("pool._shutdown_handler_registered", False):
        await spawn_task("t1", "code", "do something")

    mock_register.assert_called_once()
```

### Anti-Patterns to Avoid
- **Swallowing ENOENT silently in rerenderSoul:** Current code catches error and logs but continues — this is correct and must be preserved (CONTEXT.md: "rerenderSoul failure logged but does not fail accept request"). Do NOT change the error handling semantics, only the path.
- **Using `signal.signal()` for SIGTERM:** This is an anti-pattern documented in the existing code comments — causes fcntl deadlock when signal fires while a state lock is held. The existing `loop.add_signal_handler()` approach is correct.
- **Using `asyncio.get_event_loop()` in Python 3.10+:** This is deprecated in async context. Use `asyncio.get_running_loop()` inside async functions.
- **Calling `register_shutdown_handler()` in `__main__`:** The CONTEXT.md decision locks the call site to `spawn_task()` only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess path resolution | Runtime path discovery, relative imports | `path.join(OPENCLAW_ROOT, ...)` constant | Path is known at deploy time; constant is sufficient and explicit |
| Event loop reference in async context | Passing loop as parameter | `asyncio.get_running_loop()` | Python stdlib, no extra complexity |
| Idempotency guard | Re-checking signal handler state | Module-level boolean flag | Simplest possible guard; no thread-safety concern (single-threaded asyncio) |

---

## Common Pitfalls

### Pitfall 1: Using ORCHESTRATION_ROOT with wrong subpath for suggest.py
**What goes wrong:** `suggest.py` lives at `cli/suggest.py` under the orchestration package, not directly under `src/openclaw/`. Forgetting the `cli/` subdirectory gives a new ENOENT.
**Why it happens:** The two Python scripts have different depths: `soul_renderer.py` is directly in `src/openclaw/`, while `suggest.py` is in `src/openclaw/cli/`.
**How to avoid:** `path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py')` vs `path.join(ORCHESTRATION_ROOT, 'soul_renderer.py')`.
**Warning signs:** ENOENT on POST /api/suggestions after the fix.

### Pitfall 2: Module-level idempotency flag vs. closure flag scope
**What goes wrong:** The existing `_fired` closure inside `register_shutdown_handler()` prevents double-firing of SIGTERM, but does NOT prevent `loop.add_signal_handler()` from being registered twice if `spawn_task()` is called twice. A second call would silently overwrite the first handler with a new pool reference.
**Why it happens:** The closure is local to each `register_shutdown_handler()` call.
**How to avoid:** The CONTEXT.md decision specifies a module-level `_shutdown_handler_registered` flag. Set it inside `register_shutdown_handler()` before the `loop.add_signal_handler()` call; check it in `spawn_task()` before calling `register_shutdown_handler()`.
**Warning signs:** If `spawn_task()` is called twice in test, `add_signal_handler` called twice.

### Pitfall 3: asyncio.get_event_loop() vs. asyncio.get_running_loop()
**What goes wrong:** `asyncio.get_event_loop()` in Python 3.10+ emits a DeprecationWarning inside async context and may return a new loop not the running one.
**Why it happens:** The rest of pool.py uses `get_event_loop()` (lines 373, 573, 591) — this is a pre-existing pattern that works but is technically deprecated.
**How to avoid:** For the new call site in `spawn_task()` (which IS inside async context), use `asyncio.get_running_loop()` — it is the correct API and raises RuntimeError if no loop is running (fast failure vs. silent wrong loop).
**Warning signs:** DeprecationWarning in test output.

### Pitfall 4: Startup check breaks route import if fs.existsSync is async
**What goes wrong:** Using `fs.promises.access` (async) at module level doesn't work — module init is synchronous in Next.js route modules.
**Why it happens:** Next.js imports routes synchronously.
**How to avoid:** Use synchronous `existsSync` from `fs` (not `fs/promises`) for the startup check.

### Pitfall 5: Error swallowing semantics in rerenderSoul — must be preserved
**What goes wrong:** If the try/catch around `rerenderSoul()` is removed or the error re-thrown, accepting a suggestion fails entirely even though soul-override.md was already written.
**Why it happens:** The decision from Phase 41 Plan 02: "rerenderSoul failure logged but does not fail accept request."
**How to avoid:** Only change the path string inside `rerenderSoul()`. Do not change error handling.

---

## Code Examples

Verified patterns from codebase inspection:

### Fix 1: Correct path for suggest.py (route.ts)
```typescript
// Source: packages/dashboard/src/app/api/suggestions/route.ts — CURRENT (broken)
const orchestrationPath = path.join(OPENCLAW_ROOT, 'orchestration', 'suggest.py');

// FIXED — add ORCHESTRATION_ROOT constant and use correct subpath
const ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw');
const orchestrationPath = path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py');
```

### Fix 2: Correct path for soul_renderer.py (action/route.ts)
```typescript
// Source: packages/dashboard/src/app/api/suggestions/[id]/action/route.ts — CURRENT (broken)
await execFileAsync('python3', [
  path.join(OPENCLAW_ROOT, 'orchestration', 'soul_renderer.py'),
  '--project', projectId, '--write', '--force',
], { cwd: OPENCLAW_ROOT });

// FIXED — add ORCHESTRATION_ROOT constant and use correct subpath
const ORCHESTRATION_ROOT = path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw');
await execFileAsync('python3', [
  path.join(ORCHESTRATION_ROOT, 'soul_renderer.py'),
  '--project', projectId, '--write', '--force',
], { cwd: OPENCLAW_ROOT });
```

### Fix 3: Wire register_shutdown_handler in spawn_task() (pool.py)
```python
# Source: skills/spawn/pool.py — add at module level
_shutdown_handler_registered = False  # module-level idempotency guard

# Inside register_shutdown_handler(), at the top:
def register_shutdown_handler(loop: asyncio.AbstractEventLoop, pool: "L3ContainerPool") -> None:
    global _shutdown_handler_registered
    _shutdown_handler_registered = True  # mark before add_signal_handler
    ...

# Inside spawn_task(), after pool creation and before spawn_and_monitor():
    pool = L3ContainerPool(max_concurrent=max_concurrent, project_id=project_id)
    pool._pool_config = pool_cfg
    await pool.run_recovery_scan()

    global _shutdown_handler_registered
    if not _shutdown_handler_registered:
        loop = asyncio.get_running_loop()
        register_shutdown_handler(loop, pool)
        logger.debug("SIGTERM drain handler registered")

    return await pool.spawn_and_monitor(...)
```

### Startup warning check (route.ts, module level)
```typescript
// Source: CONTEXT.md locked decision — "one-time startup check that logs WARN if script paths don't exist"
import { existsSync } from 'fs';  // sync, not fs/promises

// After ORCHESTRATION_ROOT constant definition:
if (!existsSync(path.join(ORCHESTRATION_ROOT, 'cli', 'suggest.py'))) {
  console.warn('[suggestions] suggest.py not found at expected path — check OPENCLAW_ROOT');
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `path.join(OPENCLAW_ROOT, 'orchestration', '...')` | `path.join(OPENCLAW_ROOT, 'packages', 'orchestration', 'src', 'openclaw', '...')` | refactor/repo-structure branch | Old paths resolve to non-existent locations |
| `signal.signal(SIGTERM, handler)` | `loop.add_signal_handler(signal.SIGTERM, callback)` | Phase 39 design decision | Prevents fcntl deadlock when state engine holds lock during signal |

**Deprecated/outdated:**
- `OPENCLAW_ROOT/orchestration/` path prefix: Does not exist after packages/ refactor. All orchestration code is now at `packages/orchestration/src/openclaw/`.

---

## Open Questions

1. **Where exactly should ORCHESTRATION_ROOT constant live?**
   - What we know: CONTEXT.md says Claude has discretion. Two route files both need it.
   - What's unclear: Whether to put it in each route file independently or a shared `lib/` util. CONTEXT.md lean is "no new files."
   - Recommendation: Put it in each route file independently (two files, one constant each). Both files already import from `path`, no additional imports needed. Avoids creating new shared module.

2. **Startup check placement in action/route.ts?**
   - What we know: CONTEXT.md says "one-time startup check" for soul_renderer.py path as well.
   - What's unclear: Whether CONTEXT.md intended the check for both routes or only route.ts.
   - Recommendation: Add startup check in both route files — same pattern, same logic. Low cost, high value for misconfiguration detection.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `~/.openclaw/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest packages/orchestration/tests/test_pool_shutdown.py -v` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -v` |
| Estimated runtime | ~3 seconds |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ADV-01 | suggest.py invoked at correct path from POST /api/suggestions | manual-only (Next.js route, no Python test env) | Manual: `curl -X POST http://localhost:6987/api/suggestions?project=pumplai` | N/A — TypeScript route test out of scope |
| ADV-02 | Suggestions populated in soul-suggestions.json after POST | manual-only | Manual: check file after POST | N/A |
| ADV-03 | soul-suggestions.json written to correct path | manual-only | Manual: check file path | N/A |
| ADV-04 | SOUL.md re-rendered after accept action | manual-only (Next.js route) | Manual: accept suggestion, check SOUL.md mtime | N/A |
| REL-08 | register_shutdown_handler() called from spawn_task() | unit | `uv run pytest packages/orchestration/tests/test_pool_shutdown.py::test_spawn_task_wires_shutdown_handler -v` | ❌ Wave 0 gap — must be written |

### Nyquist Sampling Rate
- **Minimum sample interval:** After each committed task → run: `uv run pytest packages/orchestration/tests/test_pool_shutdown.py -v`
- **Full suite trigger:** Before final plan merge → run: `uv run pytest packages/orchestration/tests/ -v`
- **Phase-complete gate:** Full suite green (147+1 tests) before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~3 seconds

### Wave 0 Gaps (must be created before implementation)
- [ ] `test_spawn_task_wires_shutdown_handler` test in `packages/orchestration/tests/test_pool_shutdown.py` — covers REL-08 wiring regression

*(TypeScript route fixes for ADV-01/02/03/04 are not testable in the Python test suite — manual verification is the appropriate gate for those)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `packages/dashboard/src/app/api/suggestions/route.ts` — confirmed broken path line 46
- Direct codebase inspection: `packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` — confirmed broken path line 51
- Direct codebase inspection: `skills/spawn/pool.py` lines 1019-1105 — confirmed register_shutdown_handler defined, spawn_task() has zero call to it
- Direct codebase inspection: `packages/orchestration/src/openclaw/cli/suggest.py` — confirmed file exists at correct path
- Direct codebase inspection: `packages/orchestration/src/openclaw/soul_renderer.py` — confirmed file exists at correct path
- `.planning/v1.4-MILESTONE-AUDIT.md` — authoritative evidence of all three gaps with exact line numbers
- `packages/orchestration/tests/test_pool_shutdown.py` — confirmed 6 existing shutdown tests pass

### Secondary (MEDIUM confidence)
- `asyncio.get_running_loop()` vs `asyncio.get_event_loop()` — Python 3.10+ docs; `get_running_loop()` is correct inside async context

### Tertiary (LOW confidence)
- None — all findings verified directly from codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all changes use existing stdlib (Node path, Python asyncio)
- Architecture: HIGH — gaps are precisely documented in audit report with exact file:line references
- Pitfalls: HIGH — identified from code inspection and prior phase decisions in STATE.md

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days — stable codebase, no fast-moving dependencies)
