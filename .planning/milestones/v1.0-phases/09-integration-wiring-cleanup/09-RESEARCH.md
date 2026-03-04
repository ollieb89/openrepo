# Phase 9: Integration Wiring Cleanup - Research

**Researched:** 2026-02-23
**Domain:** JSON configuration wiring, Python Docker labels, TypeScript hierarchy building, stub skill creation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Agent hierarchy schema (INT-01)**
- Add `level` and `reports_to` fields **inline on each agent entry** in `openclaw.json`
- `level` uses **numeric values: 1, 2, 3** — matches existing L1/L2/L3 naming convention
- `reports_to` is an **agent ID string, null for L1** (e.g. L3 specialist `reports_to: "pumplai_pm"`, L2 `reports_to: "clawdia_prime"`, L1 `reports_to: null`)
- **Validate `reports_to` references on load** — warn if an agent references a `reports_to` ID that doesn't exist in the agents list. Catches typos and broken wiring early.

**Phantom skill resolution (INT-02)**
- **Create `skills/review_skill/`** as a stub (do NOT remove the config reference)
- Stub is **Python** — aligns with L2 PumplAI_PM's Python-based orchestration layer and spawn_specialist pattern
- Follows the **same directory structure** as existing skills (router_skill, spawn_specialist) — config registration, entry point convention
- When invoked: **log the review request and return success** — non-blocking acknowledged response

**Container label strategy (INT-03)**
- Set **`openclaw.managed=true`** plus **`openclaw.task_id`** and **`openclaw.level=3`** labels on spawned containers in `spawn.py`
- Use **`openclaw.*` prefix namespace** for all labels — prevents collisions with other Docker tooling
- **No backward compatibility needed** — L3 containers are ephemeral, old unlabeled containers clean up naturally
- `listSwarmContainers` filters by **label only** — single source of truth, no name pattern fallback

**Cross-fix coordination**
- **Separate commits per INT item** — one commit per fix for clean audit trail, easier review/revert/bisect
- **Manual smoke test per fix** — verify: 1) hierarchy renders, 2) review_skill responds, 3) container has labels, 4) no WARN on delegation
- COM-01 delegation WARN fix validated with successful roundtrip after schema change

### Claude's Discretion
- COM-01 WARN fix location — Claude investigates the actual WARN source and fixes wherever it originates (router_skill sender vs receiving agent consumer)
- Execution ordering of INT-01/INT-02/INT-03 — Claude determines optimal sequence based on dependencies
- Internal structure of review_skill stub (exact logging format, response schema)
- Validation error severity (WARN vs FATAL for invalid `reports_to` references)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

**Specifics (from CONTEXT.md)**
- Validation should use DFS or similar to detect circular `reports_to` chains (agent reporting to itself or sub-agent)
- Labels should include `openclaw.level` on containers so monitoring can distinguish L3 specialist containers
- The stub review_skill should be minimal but discoverable — future phases can flesh it out
</user_constraints>

---

## Summary

Phase 9 fixes three integration wiring issues surfaced by the v1.0 milestone audit integration checker. All three are purely wiring/configuration problems — no new capabilities are being built. The phase wires together existing components that were already designed to connect but were left disconnected across separate implementation phases.

**INT-01** is a JSON configuration gap: the `openclaw.json` `agents.list` array has 6 entries, none of which carry `level` or `reports_to` fields. The `buildAgentHierarchy()` function in `workspace/occc/src/lib/metrics.ts` already reads these fields (`agent.level` with a fallback of `1`, `agent.reports_to` passed through) — it is ready to consume them. The fix is a targeted edit to `openclaw.json` adding the fields to each of the 6 agents. A validation pass in the dashboard load path (or inline in `buildAgentHierarchy`) should warn on missing `reports_to` referents and detect circular chains.

**INT-02** is a missing directory: `agents/pumplai_pm/agent/config.json` references `skills/review_skill` as a `skill_path` but the directory does not exist. The fix is to create `skills/review_skill/` as a Python stub that mirrors the structure of `skills/spawn_specialist/`. The stub entry point logs the review request and returns success — it is a placeholder with a real call boundary, not dead code.

**INT-03** is a label gap in `skills/spawn_specialist/spawn.py`: the container labels dict sets `openclaw.tier`, `openclaw.task_id`, `openclaw.spawned_by`, and `openclaw.skill` but omits `openclaw.managed=true`. The `listSwarmContainers()` function in `workspace/occc/src/lib/docker.ts` uses `openclaw.managed=true` as its primary filter; the name-pattern fallback currently compensates. The fix adds `openclaw.managed`, `openclaw.level`, and confirms `openclaw.task_id` to the labels dict and removes the name-pattern fallback from `listSwarmContainers`.

**Primary recommendation:** Fix in dependency order — INT-01 first (openclaw.json schema), INT-03 second (spawn.py labels, independent of INT-01), INT-02 third (review_skill stub, fully independent). COM-01 WARN investigation should be done before committing INT-01 since adding `level` to `openclaw.json` may be the exact change that triggers or resolves the WARN.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python 3 | 3.x (host) | review_skill stub entry point | Matches spawn_specialist pattern, no new language deps |
| JSON (stdlib) | — | openclaw.json schema extension | Config file is already JSON, no serialization library needed |
| Docker SDK for Python | 7.1.0 (already in requirements.txt) | Existing spawn.py labels dict | Already a project dependency |
| TypeScript | — (existing occc build) | buildAgentHierarchy validation | Any validation lives in metrics.ts, no new tools |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `fcntl.flock()` | NOT needed for this phase | review_skill stub does not touch state.json |
| `docker.listContainers` filter API | Already used in docker.ts | No change to API call signature, only label key added |

### Alternatives Considered
| Standard choice | Alternative | Why standard wins |
|----------------|-------------|-------------------|
| Python stub | Node.js stub | Python matches L2 orchestration pattern; spawn_specialist is Python |
| Inline `level`/`reports_to` in openclaw.json | Separate hierarchy config file | User locked decision: inline on agent entries |
| Remove `review` from pumplai_pm config | Create stub directory | User locked decision: keep config reference, create stub |

---

## Architecture Patterns

### Recommended Project Structure (new files this phase)

```
skills/review_skill/
├── review.py          # Entry point — logs and returns success
└── skill.json         # Skill registration matching spawn_specialist pattern
```

### Pattern 1: openclaw.json Agent Schema Extension

**What:** Add `level` (int) and `reports_to` (string | null) inline on each agent entry in the `agents.list` array.

**Current state of `openclaw.json` agents.list (6 entries, none have level/reports_to):**
```json
{
  "id": "main",
  "name": "Central Core"
}
```

**Target schema per agent:**
```json
{
  "id": "clawdia_prime",
  "name": "Head of Development",
  "level": 1,
  "reports_to": null,
  "sandbox": { "mode": "off" }
}
```

**Full mapping for all 6 agents:**
| id | level | reports_to |
|----|-------|------------|
| main | 1 | null |
| clawdia_prime | 1 | null |
| pumplai_pm | 2 | "clawdia_prime" |
| nextjs_pm | 2 | "clawdia_prime" |
| python_backend_worker | 3 | "pumplai_pm" |
| l3_specialist | 3 | "pumplai_pm" |

Note: `main` is a system agent (Central Core), not part of the L1/L2/L3 swarm hierarchy. Level 1 with null `reports_to` is the safest assignment; it will not affect hierarchy display if `main` is excluded from hierarchy rendering.

### Pattern 2: spawn.py Label Dict Extension

**What:** Add `openclaw.managed`, `openclaw.level` to the labels dict in `spawn_l3_specialist()`.

**Current labels dict (lines 130-135 in spawn.py):**
```python
"labels": {
    "openclaw.tier": f"l{l3_config.get('level', 3)}",
    "openclaw.task_id": task_id,
    "openclaw.spawned_by": spawned_by,
    "openclaw.skill": skill_hint,
},
```

**Target labels dict:**
```python
"labels": {
    "openclaw.managed": "true",
    "openclaw.level": str(l3_config.get("level", 3)),
    "openclaw.task_id": task_id,
    "openclaw.spawned_by": spawned_by,
    "openclaw.skill": skill_hint,
    "openclaw.tier": f"l{l3_config.get('level', 3)}",
},
```

Docker label values must be strings. `"true"` not `True`. The `openclaw.tier` label can be preserved for backward compatibility with any existing tooling.

### Pattern 3: listSwarmContainers Simplification

**What:** Remove the name-pattern fallback from `listSwarmContainers()` in `docker.ts`. Once spawn.py sets `openclaw.managed=true`, the label filter is the single source of truth.

**Current implementation (lines 89-115 in docker.ts):**
```typescript
export async function listSwarmContainers(): Promise<Docker.ContainerInfo[]> {
  // ... label filter for openclaw.managed=true
  // ALSO: name-pattern fallback (openclaw-* names)
  // THEN: merge and deduplicate
}
```

**Target implementation:**
```typescript
export async function listSwarmContainers(): Promise<Docker.ContainerInfo[]> {
  if (!(await checkDockerAvailability())) return [];
  try {
    return await docker.listContainers({
      filters: { label: ['openclaw.managed=true'] },
    });
  } catch (error) {
    console.error('[Docker] Error listing swarm containers:', error);
    return [];
  }
}
```

### Pattern 4: review_skill Stub Structure

**What:** Mirror the spawn_specialist pattern — a `skill.json` registration file and a Python entry point.

**`skills/review_skill/skill.json`:**
```json
{
  "id": "review_skill",
  "name": "L3 Work Reviewer",
  "description": "Reviews L3 git diffs on staging branches and merges or rejects to main. Stub: logs request and returns success.",
  "owner": "pumplai_pm",
  "commands": [
    {
      "name": "review",
      "description": "Review L3 staging branch and merge or reject.",
      "parameters": {
        "task_id": { "type": "string", "required": true },
        "staging_branch": { "type": "string", "required": true },
        "action": { "type": "string", "enum": ["merge", "reject"], "required": true }
      },
      "handler": "python3 review.py"
    }
  ]
}
```

**`skills/review_skill/review.py`:**
```python
"""
L3 Work Review Skill - Stub Implementation

Placeholder for L2 (PumplAI_PM) to review L3 staging branch diffs
and merge or reject work. Current implementation acknowledges the request
and returns success. Full implementation deferred to a future phase.
"""

import json
import sys


def review_l3_work(task_id: str, staging_branch: str, action: str) -> dict:
    """
    Review L3 work on a staging branch.

    Stub: logs the request and returns acknowledged success.
    Future: inspect git diff, validate quality, merge or reject branch.
    """
    print(f"[review_skill] Review request received")
    print(f"[review_skill] task_id={task_id}, branch={staging_branch}, action={action}")
    print(f"[review_skill] STUB: acknowledging {action} request and returning success")

    return {
        "status": "acknowledged",
        "task_id": task_id,
        "staging_branch": staging_branch,
        "action": action,
        "note": "Stub implementation — full review logic pending future phase"
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Review L3 staging branch work")
    parser.add_argument("task_id", help="Task identifier")
    parser.add_argument("staging_branch", help="L3 staging branch name")
    parser.add_argument("action", choices=["merge", "reject"], help="Review action")
    args = parser.parse_args()

    result = review_l3_work(args.task_id, args.staging_branch, args.action)
    print(json.dumps(result, indent=2))
```

### Pattern 5: buildAgentHierarchy Validation (Claude's Discretion)

**What:** Add `reports_to` referent validation and circular chain detection to `buildAgentHierarchy()` in `metrics.ts`.

**Approach — warn, never throw:**
```typescript
export function buildAgentHierarchy(
  agents: OpenClawAgent[],
  state: JarvisState
): AgentNode[] {
  // Build ID set for referent validation
  const agentIds = new Set(agents.map((a) => a.id));

  // Validate reports_to references (warn on missing, detect cycles)
  agents.forEach((agent) => {
    if (agent.reports_to && !agentIds.has(agent.reports_to)) {
      console.warn(
        `[hierarchy] Agent '${agent.id}' reports_to '${agent.reports_to}' which is not in the agents list`
      );
    }
  });

  // Detect circular chains via DFS
  // (simple: if walking reports_to chain exceeds agents.length steps, it's cyclic)
  agents.forEach((agent) => {
    let current = agent.reports_to;
    let steps = 0;
    while (current && steps <= agents.length) {
      const parent = agents.find((a) => a.id === current);
      current = parent?.reports_to ?? null;
      steps++;
    }
    if (steps > agents.length) {
      console.warn(`[hierarchy] Circular reports_to chain detected starting from '${agent.id}'`);
    }
  });

  return agents.map((agent) => { /* ... existing map logic ... */ });
}
```

### Anti-Patterns to Avoid

- **Do not throw on validation failures** — `buildAgentHierarchy` is called in the dashboard render path. A throw would break the UI. Use `console.warn` only.
- **Do not use `"True"` for Docker label values** — Docker label values are strings. Use `"true"` (lowercase). The Python `True` boolean will silently produce incorrect filter matches.
- **Do not remove `openclaw.tier` from spawn.py labels** — It may be read by other tooling. Keep it alongside the new `openclaw.managed` and `openclaw.level` labels.
- **Do not create review_skill as a Node.js file** — Locked decision: Python only, matching L2 orchestration pattern.
- **Do not add level/reports_to to the `agents.defaults` block** — These are per-agent identity fields. The defaults block is for operational configuration (model, sandbox, memorySearch).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular dependency detection | Custom graph traversal | Simple path-length guard (steps > agents.length) | agents.length is always small (<10); full DFS graph library is overkill |
| Docker label filtering | Custom container name parser | `docker.listContainers({ filters: { label: [...] } })` | Already used in docker.ts; dockerode handles filter API |
| Skill registry config | New format | Mirror spawn_specialist `skill.json` exactly | Consistency; planner/executor can read any skill the same way |

**Key insight:** This phase has zero new algorithms. Every component already exists and is designed to work — the fixes are purely additive JSON fields, one label key, one directory with two files. Resist the temptation to redesign any subsystem.

---

## Common Pitfalls

### Pitfall 1: COM-01 WARN source ambiguity
**What goes wrong:** The audit notes the COM-01 WARN is a "schema issue (unrecognized 'level' key)" in `openclaw.json`. This is paradoxical — INT-01 requires *adding* `level` to `openclaw.json`, but the WARN is about `level` being *present*. The WARN may originate from a different config file (e.g., the per-agent `config.json` files already have `level`), not from the root `openclaw.json`.
**Why it happens:** The `agents/clawdia_prime/agent/config.json` and `agents/pumplai_pm/agent/config.json` already carry `level` fields. The openclaw CLI may validate these against an internal schema that does not expect `level`. Adding `level` to `openclaw.json` may or may not affect the WARN.
**How to avoid:** Before editing `openclaw.json`, run a delegation roundtrip to capture the WARN in context. Inspect the WARN message for the file path and field name. Then apply the targeted fix — either patch the openclaw CLI schema validation, or if the WARN is from the CLI consuming `agents/*/config.json`, the fix is there rather than in `openclaw.json`.
**Warning signs:** If the WARN disappears after INT-01 without a separate fix, the WARN was coming from `openclaw.json` lacking `level` (gateway was expecting it). If the WARN persists after INT-01, the source is elsewhere.

### Pitfall 2: `main` agent level assignment
**What goes wrong:** The `main` agent ("Central Core") is a system agent that does not map to L1/L2/L3 semantics. Assigning it `level: 1` may cause it to appear in the hierarchy display as a peer of ClawdiaPrime.
**Why it happens:** `buildAgentHierarchy` maps all agents in the list uniformly.
**How to avoid:** Assign `level: 1, reports_to: null` to `main` (safe default). If the dashboard should exclude non-swarm agents from the hierarchy, the filter belongs in the dashboard component, not in the data layer — but that's out of scope for this phase. This phase only adds fields; UI filtering is deferred.

### Pitfall 3: Docker label value type
**What goes wrong:** `"openclaw.managed": True` (Python bool) instead of `"openclaw.managed": "true"` (string).
**Why it happens:** Python dict values can be any type, but Docker label values must be strings. The Docker SDK may silently convert or reject non-string label values, causing the filter `openclaw.managed=true` to miss containers.
**How to avoid:** Use `"true"` string literal. Verify with `docker inspect <container_id>` after spawning.

### Pitfall 4: listSwarmContainers fallback removal timing
**What goes wrong:** Removing the name-pattern fallback before ensuring existing running containers (spawned without the `managed` label) are drained.
**Why it happens:** Old containers spawned pre-Phase-9 have no `openclaw.managed` label but may still appear in `docker ps`.
**How to avoid:** The CONTEXT.md locked decision addresses this — L3 containers are ephemeral, old ones clean up naturally. No backward compatibility handling required. The fallback removal is safe after the label fix is applied, as new spawns will always have the label.

### Pitfall 5: review_skill directory resolution
**What goes wrong:** Creating `skills/review_skill/review.py` but having the `skill_path` in `pumplai_pm/agent/config.json` resolve incorrectly (relative path from wrong working directory).
**Why it happens:** The `skill_path` in config.json is `"skills/review_skill"` — this is relative to the OpenClaw project root. Verify that the orchestration layer resolves skill paths from the project root, not from the agent directory.
**How to avoid:** Follow the exact same path convention as `skills/spawn_specialist` which is already working. The `skill_path` in pumplai_pm config for `spawn_specialist` is `"skills/spawn_specialist"` and it works. review_skill follows the identical pattern.

---

## Code Examples

Verified patterns from direct codebase inspection:

### INT-01: openclaw.json complete agents list (target state)
```json
"list": [
  {
    "id": "main",
    "name": "Central Core",
    "level": 1,
    "reports_to": null
  },
  {
    "id": "clawdia_prime",
    "name": "Head of Development",
    "level": 1,
    "reports_to": null,
    "sandbox": { "mode": "off" }
  },
  {
    "id": "pumplai_pm",
    "name": "PumpLAI Project Manager",
    "level": 2,
    "reports_to": "clawdia_prime",
    "workspace": "~/Development/Projects/pumplai",
    "sandbox": { "mode": "all" }
  },
  {
    "id": "nextjs_pm",
    "name": "Frontend Architect",
    "level": 2,
    "reports_to": "clawdia_prime",
    "workspace": "~/Development/Projects/pumplai",
    "sandbox": { "mode": "off" }
  },
  {
    "id": "python_backend_worker",
    "name": "ML Pipeline Worker",
    "level": 3,
    "reports_to": "pumplai_pm",
    "workspace": "~/Development/Projects/pumplai",
    "sandbox": { "mode": "off" }
  },
  {
    "id": "l3_specialist",
    "name": "L3 Specialist Executor",
    "level": 3,
    "reports_to": "pumplai_pm",
    "workspace": "~/Development/Projects/pumplai",
    "sandbox": { "mode": "all" }
  }
]
```

### INT-03: spawn.py labels dict (target state)
```python
# Labels for tracking (INT-03 fix: openclaw.managed=true is the primary filter key)
"labels": {
    "openclaw.managed": "true",
    "openclaw.level": str(l3_config.get("level", 3)),
    "openclaw.task_id": task_id,
    "openclaw.spawned_by": spawned_by,
    "openclaw.skill": skill_hint,
    "openclaw.tier": f"l{l3_config.get('level', 3)}",  # preserved for backward compat
},
```

### INT-03: docker.ts listSwarmContainers (target state)
```typescript
export async function listSwarmContainers(): Promise<Docker.ContainerInfo[]> {
  if (!(await checkDockerAvailability())) return [];

  try {
    // Label-only filter: openclaw.managed=true is the single source of truth
    // spawn.py now sets this label on all managed containers (Phase 9: INT-03)
    return await docker.listContainers({
      filters: {
        label: ['openclaw.managed=true'],
      },
    });
  } catch (error) {
    console.error('[Docker] Error listing swarm containers:', error);
    return [];
  }
}
```

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSH-01 | Deploy occc dashboard with Next.js 16 and Tailwind 4 | INT-01 fix ensures buildAgentHierarchy renders correct 3-tier hierarchy in the dashboard |
| DSH-03 | Live log feeds from isolated agent containers | INT-03 fix ensures listSwarmContainers primary filter correctly identifies managed containers |
| DSH-04 | Global metrics visualization (task throughput, error rates) | INT-01 fix ensures deriveSwarmMetrics gets correct tier counts (L1/L2/L3) |
| HIE-01 | Establish ClawdiaPrime (Level 1) as strategic orchestrator | INT-01 fix wires clawdia_prime's level:1 field into openclaw.json, surfacing correctly in hierarchy |
| HIE-02 | Implement Domain Project Managers (Level 2) | INT-01 fix wires pumplai_pm's level:2 and reports_to into openclaw.json |
| COM-01 | Hub-and-spoke communication via OpenClaw Gateway | COM-01 WARN fix resolves runtime validation noise on delegation roundtrip |
| COM-04 | Semantic snapshotting for workspace state persistence | INT-02 fix resolves phantom review_skill reference — review workflow has a real skill entrypoint |
</phase_requirements>

---

## Execution Order Recommendation

Based on dependency analysis (Claude's discretion):

1. **INT-03 first** — `spawn.py` label fix is fully independent. Pure Python dict addition, no schema impacts, no WARN side-effects. Easiest win, demonstrates progress, can be smoke-tested immediately with `docker inspect`.

2. **INT-01 second** — `openclaw.json` schema extension. Investigate COM-01 WARN before committing: run a delegation roundtrip, capture WARN message with file/field context, then add `level`/`reports_to` fields. If WARN resolves, commit both INT-01 and COM-01 fix together (they are one root cause). If WARN persists, investigate the per-agent `config.json` files as the WARN source.

3. **INT-02 last** — `skills/review_skill/` stub creation. Fully independent. Two new files, no edits to existing files. Create after INT-01 is committed to keep the `pumplai_pm` config reference consistent with the new stub's existence.

Each fix gets its own commit per the locked decision.

---

## Open Questions

1. **COM-01 WARN exact source**
   - What we know: The audit says WARN is from "openclaw.json schema issue (unrecognized 'level' key)". The per-agent `config.json` files already have `level` (clawdia_prime, pumplai_pm, l3_specialist). The root `openclaw.json` does not currently have `level` on any agent.
   - What's unclear: Is the WARN triggered by (a) `openclaw.json` missing `level` and gateway expecting it, (b) `agents/*/config.json` having `level` that the CLI schema rejects, or (c) something else entirely?
   - Recommendation: Run `openclaw agent --agent pumplai_pm --message "test" 2>&1 | grep -i warn` before any edits. The WARN message should identify the file and key. Fix wherever it originates.

2. **`main` agent semantics in hierarchy**
   - What we know: `main` is listed as "Central Core" in openclaw.json but has no L1/L2/L3 role in the Grand Architect Protocol.
   - What's unclear: Should `main` be excluded from the hierarchy display, or is it acceptable as a pseudo-L1?
   - Recommendation: Assign `level: 1, reports_to: null` (safest default, matches its position as the root system agent). No filtering needed in this phase.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Name-pattern fallback for container discovery | Label-only filter (`openclaw.managed=true`) | Old approach compensated for missing label; new approach is correct and simpler |
| `openclaw.tier` as only tier identifier | `openclaw.level` + `openclaw.tier` | `level` is a clean integer, `tier` is a legacy string prefix |
| No `level`/`reports_to` in openclaw.json | Inline fields per agent | Agent identity config already had these in per-agent config.json files |

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `~/.openclaw/openclaw.json` (confirmed: no level/reports_to in agents.list)
- Direct codebase inspection — `~/.openclaw/workspace/occc/src/lib/metrics.ts` (confirmed: buildAgentHierarchy reads agent.level with fallback 1, agent.reports_to passed through)
- Direct codebase inspection — `~/.openclaw/workspace/occc/src/lib/docker.ts` (confirmed: listSwarmContainers uses openclaw.managed=true filter + name fallback)
- Direct codebase inspection — `~/.openclaw/skills/spawn_specialist/spawn.py` (confirmed: labels dict has openclaw.tier/task_id/spawned_by/skill, missing openclaw.managed)
- Direct codebase inspection — `~/.openclaw/agents/pumplai_pm/agent/config.json` (confirmed: skill_registry.review.skill_path = "skills/review_skill"; directory does not exist)
- Direct codebase inspection — `~/.openclaw/.planning/v1.0-MILESTONE-AUDIT.md` (confirmed: INT-01, INT-02, INT-03 descriptions and evidence)
- Direct codebase inspection — `~/.openclaw/agents/l3_specialist/config.json` (confirmed: level:3, reports_to:"pumplai_pm" already present in per-agent config)

### Secondary (MEDIUM confidence)
- CONTEXT.md locked decisions — user has confirmed all INT item resolution strategies

### Tertiary (LOW confidence)
- COM-01 WARN root cause — the audit describes it but it has not been reproduced in this research session. The fix location (router_skill vs per-agent config.json vs openclaw.json) is unverified until delegation roundtrip is inspected live.

---

## Validation Architecture

> nyquist_validation is not set to true in .planning/config.json — skipping this section.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external libraries, all components already in project
- Architecture patterns: HIGH — patterns derived from direct codebase inspection of existing working analogues
- Pitfalls: MEDIUM — COM-01 WARN source is plausible inference from audit text; not live-tested
- Execution order: HIGH — dependency analysis from codebase structure

**Research date:** 2026-02-23
**Valid until:** 2026-03-25 (stable config, no fast-moving dependencies)
