# Phase 67: Integration Cleanup - Research

**Researched:** 2026-03-04
**Domain:** Python package public API surface and import correctness
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROP-02 | Each proposal includes roles, hierarchy, delegation boundaries, coordination model, risk assessment, estimated complexity, and confidence level | `score_proposal()` is the function that produces the rubric scoring needed for PROP-02 confidence level; it must be importable from `openclaw.topology` |
| PROP-03 | Each proposal is scored across a common rubric: complexity, coordination overhead, risk containment, time-to-first-output, cost estimate, preference fit, overall confidence | `score_proposal()` standalone wrapper in `rubric.py` is the public entry point for PROP-03 scoring; missing from `__all__` |
| CORR-02 | User can directly edit a proposed topology and the system executes the edited version (hard correction) | `render_diff_summary()` in `renderer.py` renders structural diff between original and corrected topology; missing from `__all__` |
| CORR-07 | User must explicitly approve a topology before it can be used for execution (approval gate) | INT-02 fix ensures `route_directive` skill is importable; `swarm_router.py` (which imports from it) is the Python-layer approval gate integration path |
</phase_requirements>

---

## Summary

Phase 67 closes two low-severity integration gaps found during the v2.0 milestone audit. Both gaps are straightforward mechanical fixes with zero risk of breaking existing functionality.

**INT-01:** `score_proposal` and `render_diff_summary` are defined in their respective submodules (`rubric.py` and `renderer.py`) and are already imported and used throughout the codebase via direct submodule imports. They are simply absent from `topology/__init__.py` — both the import statement and the `__all__` entry are missing. Adding them makes the public package API complete and enables `from openclaw.topology import score_proposal, render_diff_summary` to work as expected.

**INT-02:** `agents/main/skills/route_directive/__init__.py` imports `RouteDecision` and `RouteType` from `router.py`, but `router.py` only defines `DirectiveRouter`. The `__main__.py` and `swarm_router.py` callers show exactly what `RouteDecision` and `RouteType` must look like: `RouteType` is an enum with values `TO_PM`, `SPAWN_L3`, `COORDINATE`, `ESCALATE`, `QUEUE`; `RouteDecision` is a dataclass with fields `route_type`, `target`, `reasoning`, `confidence`, `priority`, `alternatives`, and optionally `swarm_state`. The `DirectiveRouter.route()` method must be updated to return a `RouteDecision` object instead of its current plain dict.

**Primary recommendation:** Two targeted file edits — (1) add two import lines and two `__all__` entries to `topology/__init__.py`; (2) add `RouteType` enum and `RouteDecision` dataclass to `router.py` and update `DirectiveRouter.route()` to return `RouteDecision`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `enum.Enum` | stdlib | `RouteType` enum for routing categories | Already used throughout codebase (e.g., `EdgeType` in topology models) |
| Python `dataclasses.dataclass` | stdlib | `RouteDecision` return type | Codebase convention — all domain objects use `@dataclass` (see `AgentSpec`, `TopologyGraph`, `CorrectionSession`) |

### No new dependencies required
Both fixes are pure code changes within existing files. No new packages, no new modules.

---

## Architecture Patterns

### INT-01: Adding to `__all__` in a Python package

The `topology/__init__.py` pattern is already established — every symbol exported from a submodule is both:
1. Imported at the top of `__init__.py` using `from .submodule import (symbol,)`
2. Listed in the `__all__` list

The fix follows the exact same pattern already in the file. `score_proposal` comes from `.rubric` (already imported for `RubricScorer`) and `render_diff_summary` comes from `.renderer` (already imported for other renderer functions).

**Current state of `topology/__init__.py` rubric imports:**
```python
from .rubric import (
    RubricScorer,
    find_key_differentiators,
    DEFAULT_WEIGHTS,
    DIMENSIONS,
)
```
`score_proposal` is defined in `rubric.py` (line 186) but NOT listed here.

**Current state of `topology/__init__.py` renderer imports:**
```python
from .renderer import (
    render_dag,
    render_matrix,
    render_assumptions,
    render_justifications,
    render_low_confidence_warning,
    render_full_output,
)
```
`render_diff_summary` is defined in `renderer.py` (line 56) but NOT listed here.

### INT-02: Adding `RouteType` and `RouteDecision` to `router.py`

The callers (`__main__.py`, `swarm_router.py`) reveal the required interface:

**`RouteType` enum** (from usage in `__main__.py` lines 78-82 and `swarm_router.py` lines 124-128):
```python
from enum import Enum

class RouteType(Enum):
    TO_PM = "to_pm"
    SPAWN_L3 = "spawn_l3"
    COORDINATE = "coordinate"
    ESCALATE = "escalate"
    QUEUE = "queue"
```

**`RouteDecision` dataclass** (from usage in `__main__.py` lines 68-74, 91-96 and `swarm_router.py` lines 37, 63-74):
```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RouteDecision:
    route_type: RouteType
    target: str
    reasoning: str
    confidence: float          # used as f"{decision.confidence:.0%}" — must be 0.0-1.0 float
    priority: str              # used in __main__.py output
    alternatives: List[str] = field(default_factory=list)
    swarm_state: Optional[dict] = None  # injected by SwarmAwareRouter wrapper
```

**`DirectiveRouter.route()` must return `RouteDecision`**, not dict.

The current `router.py` `route()` method returns `{"target": target, "run_id": ..., "status": ...}`. This is an async method. The new version must return a `RouteDecision`. The `__main__.py` shows `router = DirectiveRouter(config, swarm_query=None)` — the constructor signature also needs updating to accept `config` and optional `swarm_query` params (currently takes no args).

**Note on constructor signature mismatch:** The current `router.py` `DirectiveRouter.__init__` loads config internally. The `__main__.py` passes `config` dict and `swarm_query=None`. The fix must reconcile: accept optional `config` (use passed config or load internally) and optional `swarm_query` parameter.

**Note on async vs sync:** Current `route()` is `async`. The `__main__.py` calls it synchronously via `decision = router.route(args.directive)` — no `await`. The fixed `route()` should be a regular (sync) method.

### Recommended approach for INT-02

Keep the existing simple keyword-matching logic in `_resolve_target()` unchanged. Wrap the return value in a `RouteDecision` with:
- `route_type`: infer from target string (e.g., `"__propose__"` → `COORDINATE`, named PMs → `TO_PM`, `"l3_specialist"` → `SPAWN_L3`)
- `target`: the resolved agent ID (unchanged)
- `reasoning`: short description of why this target was chosen
- `confidence`: fixed `0.9` for simple keyword matches (reasonable default)
- `priority`: `"normal"` default
- `alternatives`: `[]` default

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Type checking of `__all__` | Custom linter script | Direct inspection via `python -c "from openclaw.topology import score_proposal"` | Test is one line |
| Complex routing logic | ML-based directive classifier | Keyword matching (already in place) | Phase 67 is a cleanup fix, not a feature addition |

---

## Common Pitfalls

### Pitfall 1: Forgetting `score_proposal` is a standalone function, not a class method
**What goes wrong:** Adding `RubricScorer` to `__all__` but not `score_proposal`; they are distinct symbols.
**Why it happens:** `score_proposal` is a module-level function at line 186 of `rubric.py`, separate from the `RubricScorer` class.
**How to avoid:** Add both the import AND the `__all__` entry for `score_proposal` specifically.

### Pitfall 2: Changing `DirectiveRouter.route()` to async when callers expect sync
**What goes wrong:** Keeping `route()` as `async def` breaks `__main__.py` which calls it synchronously.
**Why it happens:** Current `router.py` has `async def route()` because it calls `self.client.dispatch()` (async gateway). But `swarm_router.py` and `__main__.py` call it without `await`.
**How to avoid:** The fixed `route()` does not need to call the gateway — it returns a `RouteDecision` immediately. Make it a regular sync method. The async gateway call happens at execution time in other layers.

### Pitfall 3: Breaking existing direct submodule callers for INT-01
**What goes wrong:** Changing the import structure in a way that moves or renames the functions.
**Why it happens:** Developer restructures `rubric.py` unnecessarily.
**How to avoid:** The functions `score_proposal` and `render_diff_summary` stay exactly where they are in their submodule files. Only `__init__.py` is modified.

### Pitfall 4: `RouteDecision.confidence` type confusion
**What goes wrong:** Using `int` (e.g., 90) instead of `float` (0.9) for confidence.
**Why it happens:** `__main__.py` formats it as `f"{decision.confidence:.0%}"` — this format code multiplies by 100, so `0.9` becomes `"90%"`. If you store `90`, it prints `"9000%"`.
**How to avoid:** Use `float` in range `[0.0, 1.0]`.

---

## Code Examples

Verified from source files in this repository:

### INT-01 Fix: Add to `topology/__init__.py`

```python
# Source: packages/orchestration/src/openclaw/topology/__init__.py
# Current rubric imports block — add score_proposal:
from .rubric import (
    RubricScorer,
    score_proposal,           # ADD THIS
    find_key_differentiators,
    DEFAULT_WEIGHTS,
    DIMENSIONS,
)

# Current renderer imports block — add render_diff_summary:
from .renderer import (
    render_dag,
    render_matrix,
    render_assumptions,
    render_justifications,
    render_low_confidence_warning,
    render_full_output,
    render_diff_summary,      # ADD THIS
)

# In __all__ list — add both:
__all__ = [
    # ... existing entries ...
    "score_proposal",         # ADD
    "render_diff_summary",    # ADD
]
```

### INT-02 Fix: Add `RouteType` and `RouteDecision` to `router.py`

```python
# Source: agents/main/skills/route_directive/router.py
# Inferred from __main__.py and swarm_router.py usage
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class RouteType(Enum):
    TO_PM = "to_pm"
    SPAWN_L3 = "spawn_l3"
    COORDINATE = "coordinate"
    ESCALATE = "escalate"
    QUEUE = "queue"


@dataclass
class RouteDecision:
    route_type: RouteType
    target: str
    reasoning: str
    confidence: float
    priority: str
    alternatives: List[str] = field(default_factory=list)
    swarm_state: Optional[dict] = None
```

### Verification (both fixes)

```bash
# INT-01
uv run python -c "from openclaw.topology import score_proposal, render_diff_summary; print('INT-01 OK')"

# INT-02
uv run python -c "
import sys; sys.path.insert(0, 'agents/main/skills')
import route_directive
from route_directive import DirectiveRouter, RouteDecision, RouteType
print('INT-02 OK')
"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `topology/__init__.py` missing `score_proposal`, `render_diff_summary` | Add both to imports and `__all__` | Phase 67 | Enables `from openclaw.topology import score_proposal` to work |
| `router.py` returns plain dict | Returns `RouteDecision` dataclass | Phase 67 | Makes `route_directive` package importable; fixes INT-02 |

---

## Open Questions

1. **`DirectiveRouter` constructor signature**
   - What we know: `__main__.py` passes `(config, swarm_query=None)`, current `__init__` takes `(self)` and loads config internally.
   - What's unclear: Should `config` be optional with fallback to internal load, or required?
   - Recommendation: Make `config` optional (`config: Optional[dict] = None`); if `None`, load internally. Preserves backward compatibility while satisfying `__main__.py` usage.

2. **`route_type` inference in the new `route()` method**
   - What we know: `_resolve_target()` returns strings like `"__propose__"`, `"python_backend_worker"`, `"l3_specialist"`.
   - What's unclear: The exact mapping to `RouteType` enum values is not documented.
   - Recommendation: `"__propose__"` → `RouteType.COORDINATE`; named PM agents → `RouteType.TO_PM`; `"l3_specialist"` → `RouteType.SPAWN_L3`. This matches the intent of the enum values.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | `packages/orchestration/pyproject.toml` |
| Quick run command | `uv run pytest packages/orchestration/tests/test_proposal_rubric.py packages/orchestration/tests/test_renderer.py -x -q` |
| Full suite command | `uv run pytest packages/orchestration/tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROP-02 / PROP-03 | `from openclaw.topology import score_proposal` works | unit | `uv run pytest packages/orchestration/tests/test_topology_public_api.py -x` | ❌ Wave 0 |
| CORR-02 | `from openclaw.topology import render_diff_summary` works | unit | `uv run pytest packages/orchestration/tests/test_topology_public_api.py -x` | ❌ Wave 0 |
| CORR-07 | `import route_directive` succeeds (INT-02 fixed) | unit | `uv run pytest packages/orchestration/tests/test_route_directive_importable.py -x` | ❌ Wave 0 |
| CORR-07 | `RouteDecision`, `RouteType` accessible via package | unit | `uv run pytest packages/orchestration/tests/test_route_directive_importable.py -x` | ❌ Wave 0 |

**Note on test location:** Tests for `route_directive` (an `agents/` skill, not a `packages/orchestration/` module) may live in a `tests/` directory adjacent to the skill itself, or in `packages/orchestration/tests/` using `sys.path` manipulation (as `swarm_router.py` does). The plan should decide one location.

### Sampling Rate
- **Per task commit:** `uv run pytest packages/orchestration/tests/test_topology_public_api.py packages/orchestration/tests/test_route_directive_importable.py -x -q`
- **Per wave merge:** `uv run pytest packages/orchestration/tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/orchestration/tests/test_topology_public_api.py` — tests `from openclaw.topology import score_proposal, render_diff_summary` (covers PROP-02, PROP-03, CORR-02)
- [ ] `packages/orchestration/tests/test_route_directive_importable.py` OR `agents/main/skills/route_directive/tests/test_importable.py` — tests package import and RouteDecision/RouteType symbols (covers CORR-07)

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection: `packages/orchestration/src/openclaw/topology/__init__.py` — confirmed `score_proposal` and `render_diff_summary` absent
- Direct source inspection: `packages/orchestration/src/openclaw/topology/rubric.py` — `score_proposal` function exists at line 186
- Direct source inspection: `packages/orchestration/src/openclaw/topology/renderer.py` — `render_diff_summary` function exists at line 56
- Direct source inspection: `agents/main/skills/route_directive/__init__.py` — imports `RouteDecision`, `RouteType` which don't exist
- Direct source inspection: `agents/main/skills/route_directive/router.py` — `DirectiveRouter` exists, `RouteDecision`/`RouteType` do not
- Live verification: `uv run python -c "from openclaw.topology import score_proposal"` → `ImportError` confirmed
- Live verification: `uv run python -c "import sys; sys.path.insert(0, 'agents/main/skills'); import route_directive"` → `ImportError` confirmed
- `.planning/v2.0-MILESTONE-AUDIT.md` — INT-01 and INT-02 gap descriptions

### Secondary (MEDIUM confidence)
- `agents/main/skills/swarm_router.py` — inferred `RouteDecision` field requirements from usage
- `agents/main/skills/route_directive/__main__.py` — inferred `RouteDecision` field requirements and constructor signature

---

## Metadata

**Confidence breakdown:**
- INT-01 fix (topology `__all__`): HIGH — exact symbols located, exact change identified, verified failing import
- INT-02 fix (RouteDecision/RouteType): HIGH — exact callers show required interface, standard dataclass/enum pattern
- Pitfalls: HIGH — all identified from direct code inspection
- Test infrastructure: MEDIUM — test file locations are a judgment call (plan should decide)

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable Python package patterns; no external dependencies)
