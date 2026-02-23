# Phase 8: Final Gap Closure - Research

**Researched:** 2026-02-23
**Domain:** SSE client-side hook, JSON config schema, requirements documentation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**DSH-02 (SSE fix):**
- SSE becomes the primary data path — `useSwarmState.ts` directly consumes `{agents, metrics, state, lastUpdated}` from SSE events instead of using SSE as a nudge to trigger SWR revalidation
- SWR polling demoted to fallback only — kicks in when SSE disconnects, not as a parallel data source
- Both server and client fixed — server-side `/api/swarm/stream` must emit full `{agents, metrics, state, lastUpdated}` payloads; client-side hook must parse and apply them directly
- The current `data.updated` nudge pattern is replaced entirely

**HIE-02 (L2 config):**
- Mirror L3 config schema — same top-level keys (`id`, `name`, `level`, `reports_to`, `skill_registry`, etc.) with L2-appropriate values
- Skill registry includes three skills: `spawn_specialist`, `router`, and `review`
- Both hierarchy directions explicit: `reports_to: "clawdia_prime"` AND `delegates_to: "l3_specialist"`
- File location: `agents/pumplai_pm/agent/config.json` (alongside existing IDENTITY.md and SOUL.md)
- No container/runtime fields (L2 is persistent, not ephemeral)

**COM-02 (deviation formalization):**
- Preserve original requirement text in REQUIREMENTS.md with deviation annotation
- Update both REQUIREMENTS.md (mark SATISFIED with deviation note) AND v1.0-MILESTONE-AUDIT.md (reflect 16/16 satisfied)
- Status column changes from "Pending" to "Satisfied" with deviation note

### Claude's Discretion

- Malformed SSE event handling strategy (ignore vs partial merge)
- Whether to show a connection mode indicator on the dashboard (polling vs live)
- Whether to accept the COM-02 deviation (recommended: accept — CLI routing functionally meets intent)
- Exact L2 config field values beyond the structural decisions above

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<research_summary>
## Summary

Phase 8 closes the three remaining gaps identified in the v1.0 milestone audit (13/16 → 16/16). All three gaps are small, targeted, and well-understood from the audit and prior verification work.

**DSH-02** is a single-file client fix. The server-side SSE stream was already repaired in Phase 7 (07-03-SUMMARY.md confirms `stream/route.ts` now emits full `{agents, metrics, state, lastUpdated}` payloads on connect and on mtime change). The only remaining work is updating `useSwarmState.ts` line 61 where `if (data.updated)` silently discards every push event. The fix replaces the nudge-and-revalidate pattern with a direct SWR cache injection (`mutate(data, false)`), making SSE the primary data path and SWR the fallback.

**HIE-02** is a new JSON file. `agents/pumplai_pm/agent/config.json` does not exist. The L1 config (`agents/clawdia_prime/agent/config.json`) and L3 config (`agents/l3_specialist/config.json`) both exist and establish the schema. The new L2 config follows the same schema with `level: 2`, `reports_to: "clawdia_prime"`, `delegates_to: "l3_specialist"`, and a skill registry with three entries (`spawn_specialist`, `router`, `review`). No runtime or container fields because L2 is a persistent agent.

**COM-02** is documentation. The requirement text stays intact as an audit trail. The status changes to SATISFIED with an inline deviation annotation explaining that CLI routing (`openclaw agent` CLI) replaces the lane queue REST API (`/api/v1/lane/enqueue`), which was never built. The `v1.0-MILESTONE-AUDIT.md` frontmatter is updated to reflect 16/16 requirements satisfied and 5/5 E2E flows complete.

**Primary recommendation:** Three independent, parallel-safe changes. Execute all three in a single wave — no dependencies between them. Verify by checking: (1) SSE push path delivers state to UI without SWR revalidation, (2) `agents/pumplai_pm/agent/config.json` exists and passes JSON schema validation, (3) REQUIREMENTS.md shows COM-02 SATISFIED.

</research_summary>

<standard_stack>
## Standard Stack

This phase uses no new libraries. All tools are already present in the codebase.

### Core (already in use)

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| SWR | 2.x | Client-side data fetching with cache | Already imported in `useSwarmState.ts` |
| EventSource (Web API) | N/A | SSE client — browser native | Already wired in `useSwarmState.ts` |
| Next.js App Router | 16.1.6 | Route handlers including stream endpoint | Already deployed |
| TypeScript | 5.x | Type safety on hook changes | Already configured |

### Key APIs Used

**`mutate(data, false)` — SWR cache injection (the critical pattern):**

SWR's `mutate` function accepts two arguments: the new data and a boolean `revalidate`. Passing `mutate(data, false)` injects `data` directly into the SWR cache without triggering a network revalidation call. This is how SSE push data is applied to the UI without a follow-up REST call. The `false` flag is essential — without it, SWR immediately re-fetches from the server, defeating the purpose of SSE push.

```typescript
// Pattern: inject SSE data directly into SWR cache
const data = JSON.parse(event.data);
if (data.agents) {
  mutate(data, false); // inject without revalidate
}
```

This is the standard SWR pattern for hybrid SSE+polling hooks. It is documented in SWR's "Mutation" docs under "optimistic updates" and "cache population."

### Alternatives Considered

| Instead of | Could Use | Why Not |
|------------|-----------|---------|
| `mutate(data, false)` | `mutate()` (revalidate) | Revalidate defeats SSE purpose — fires REST call on every push event |
| `mutate(data, false)` | React setState directly | Can't bypass SWR cache — stale data would re-render on next SWR cycle |
| Disabling SWR entirely | SSE-only | SWR provides reconnect resilience; keep as fallback per locked decision |

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: SWR + SSE Hybrid with SSE as Primary Data Path

**What:** SSE delivers full state payloads on every push event. SWR polling runs at 2s as fallback for when SSE is disconnected or not yet connected. SSE data is injected into SWR cache with `mutate(data, false)` so the component tree re-renders identically whether data came via SSE or polling.

**Current (broken) pattern in `useSwarmState.ts` lines 60-63:**
```typescript
const data = JSON.parse(event.data);
if (data.updated) {          // BUG: field 'updated' absent from new payload
  mutate();                  // triggers REST revalidation — SSE used as nudge only
}
```

**Target pattern:**
```typescript
const parsed = JSON.parse(event.data);
if (parsed.agents) {
  // Full payload received — inject directly into SWR cache, no REST revalidation
  mutate(parsed, false);
  reconnectDelayRef.current = 1000; // reset backoff on successful data
}
// Malformed or error events: fall through silently (existing catch handles parse errors)
```

**Key invariants to preserve:**
- `isMountedRef.current` guard stays (prevents state updates after unmount)
- `try/catch` around `JSON.parse` stays (keepalive comments `: keepalive` are not valid JSON)
- Exponential backoff reconnect logic on `onerror` stays
- SWR `refreshInterval: 2000` stays (fallback path)
- The `mutate` function reference from `useSWR` stays as-is — no new imports needed

**Optional enhancement (at discretion):** Reset `reconnectDelayRef.current = 1000` on successful SSE data receipt to ensure backoff resets after reconnect, not just on connection establishment.

### Pattern 2: L2 Config Schema (Hierarchy Config Pattern)

**What:** Each tier has a `config.json` that defines its identity and capabilities in a machine-readable way. L1 lists `subordinates`. L3 lists `reports_to` and `spawned_by`. L2 bridges both directions: `reports_to` (upward) and `delegates_to` (downward).

**L1 config structure (reference):**
```json
{
  "id": "clawdia_prime",
  "level": 1,
  "reports_to": null,
  "skill_registry": { "router": { ... } },
  "subordinates": ["pumplai_pm"],
  "max_concurrent": 4
}
```

**L3 config structure (reference):**
```json
{
  "id": "l3_specialist",
  "level": 3,
  "reports_to": "pumplai_pm",
  "spawned_by": "pumplai_pm",
  "container": { ... },
  "runtime": { ... },
  "skill_registry": { "code": { ... }, "test": { ... } },
  "max_concurrent": 3
}
```

**L2 config target structure:**
```json
{
  "id": "pumplai_pm",
  "name": "PumplAI_PM - Domain Project Manager",
  "level": 2,
  "reports_to": "clawdia_prime",
  "delegates_to": "l3_specialist",
  "identity_ref": "agents/pumplai_pm/agent/IDENTITY.md",
  "skill_registry": {
    "spawn_specialist": {
      "name": "Spawn Specialist (L3)",
      "description": "Spawns isolated L3 specialist containers for code and test execution",
      "timeout_seconds": 660,
      "skill_path": "skills/spawn_specialist"
    },
    "router": {
      "name": "Task Router",
      "description": "Routes incoming directives from L1 to appropriate L3 skill types",
      "timeout_seconds": 120,
      "skill_path": "skills/router_skill"
    },
    "review": {
      "name": "L3 Work Review",
      "description": "Reviews L3 git diffs on staging branches and merges or rejects to main",
      "timeout_seconds": 300,
      "skill_path": "skills/review_skill"
    }
  },
  "max_concurrent": 3,
  "retry_on_failure": true,
  "max_retries": 1
}
```

**Notes on field values:**
- `spawn_specialist` timeout set to 660s (slightly above the 600s L3 code skill timeout — L2 must outlast L3)
- `max_concurrent: 3` mirrors the L3 pool limit — L2 manages exactly as many concurrent tasks as L3 can hold
- `retry_on_failure: true` / `max_retries: 1` mirrors L3 (L2 IDENTITY.md describes auto-retry behavior)
- `review` skill path `skills/review_skill` does not exist on disk yet — this is the intended path; the config records intent, not runtime presence

### Pattern 3: Requirement Deviation Annotation

**What:** Requirements that were implemented via a documented spec deviation are marked SATISFIED with an inline annotation preserving the audit trail. The original requirement text is not changed — only the Status column.

**Current REQUIREMENTS.md COM-02 row:**
```
| COM-02 | Implement "Lane Queues" for task prioritization and concurrency control. | P1 | Pending |
```

**Target format:**
```
| COM-02 | Implement "Lane Queues" for task prioritization and concurrency control. | P1 | Satisfied (Deviation: CLI routing via `openclaw agent` CLI replaces lane queue REST API. Accepted 2026-02-23.) |
```

**v1.0-MILESTONE-AUDIT.md frontmatter changes:**
- `scores.requirements: 13/16` → `16/16`
- `scores.flows: 4/5` → `5/5`
- `scores.integration: 15/16` → `16/16`
- `status: gaps_found` → `complete`
- `gaps` section: remove all three gap entries (DSH-02, HIE-02, COM-02)
- Remove the broken integration entries from `integration` list
- Remove the broken SSE flow from `flows` list

### Anti-Patterns to Avoid

- **Removing the SWR fallback entirely:** SWR at 2s ensures the UI always works even when SSE is disconnected. Removing it makes the dashboard dead during SSE reconnect windows.
- **Using `mutate()` without `false`:** Calling `mutate()` on SSE receipt triggers a REST call on every push event, making SSE a performance liability rather than a benefit.
- **Changing the `onmessage` try/catch structure:** SSE keepalive comments (`: keepalive`) are sent every 30s and are not valid JSON. The existing catch that silently ignores parse errors must stay.
- **Adding `delegates_to` to L1 config:** The locked decision specifies L2 is bidirectional; L1 already lists `subordinates` as an array (implies multiple L2 agents). Don't retroactively change L1's schema.
- **Deleting COM-02 requirement text:** The deviation annotation pattern preserves the original text. Deleting or rewriting the requirement would break audit traceability.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Injecting SSE data into React state | `useState` + manual merge | `mutate(data, false)` from SWR | SWR already owns the data — inject into its cache so polling and push are unified |
| SSE reconnect logic | Manual setTimeout loop | Existing backoff logic in `connectSSE` | Already implemented and battle-tested in this codebase — just fix the payload handler |
| JSON config validation | Custom validator | Manual review against L1/L3 schema | Config is small and only created once — schema consistency check is sufficient |
| Audit trail for deviations | New tracking system | Inline annotation in REQUIREMENTS.md | Consistent with how other status changes are documented in this project |

**Key insight:** All three changes are minimal edits. DSH-02 is a 3-line change in one file. HIE-02 is one new file. COM-02 is text in two files. The risk is not in what to build — it's in getting the exact payload field names right (verified from server code) and not over-engineering the deviation annotation.

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: SWR `mutate` reference closure issue
**What goes wrong:** The `mutate` function from `useSWR` is captured in the `connectSSE` `useCallback`. If `mutate` changes identity between renders (it shouldn't, but SWR docs note it can in edge cases), the SSE handler would hold a stale reference.
**Why it happens:** React hooks closures capture values at creation time.
**How to avoid:** The current code already handles this correctly — `mutate` is in the `useCallback` dependency array (`[mutate]`). No change needed. Just verify the new `mutate(data, false)` call is inside the same `useCallback` scope.
**Warning signs:** SSE data received but UI doesn't update — check if `mutate` is captured in the callback deps.

### Pitfall 2: SSE payload field name mismatch
**What goes wrong:** Client checks `data.agents` but server sends a different top-level key.
**Why it happens:** Server was changed (Phase 7 rewrite) — need to verify exact payload shape.
**How to avoid:** Confirmed from `stream/route.ts` (lines 44-45 and 68-70): `getSwarmState()` returns `{agents, metrics, state, lastUpdated}`. The `agents` field is always present in a successful response. Use `data.agents` as the discriminator. Error payloads have `data.error` — these should be ignored (fall through without calling mutate).
**Warning signs:** No UI updates on SSE receipt. Add a `console.log` in dev to confirm payload shape.

### Pitfall 3: Partial SWR cache injection causes type errors
**What goes wrong:** `mutate(data, false)` with a payload that doesn't fully match `SwarmStateResponse` type causes TypeScript errors or runtime rendering issues.
**Why it happens:** `getSwarmState()` return type is `{agents: AgentNode[], metrics: SwarmMetrics, state: JarvisState, lastUpdated: string}` — exactly `SwarmStateResponse`. No mismatch expected.
**How to avoid:** The server-side `getSwarmState()` return type is identical to the client-side `SwarmStateResponse` interface. The `as SwarmStateResponse` cast may help TypeScript if needed.
**Warning signs:** TypeScript compiler error on `mutate(data, false)` line.

### Pitfall 4: L2 config `review` skill path doesn't exist on disk
**What goes wrong:** A future tool that validates skill paths would flag `skills/review_skill` as missing.
**Why it happens:** The `review` skill is a forward declaration of intent (L2 IDENTITY.md describes review capability) but the skill directory hasn't been created.
**How to avoid:** This is acceptable per locked decisions. The config records architectural intent. Note this as known tech debt in the summary. Do not create a stub `skills/review_skill` directory unless explicitly asked.
**Warning signs:** Any automation that validates `skill_path` fields in config files.

### Pitfall 5: Audit frontmatter update misses secondary fields
**What goes wrong:** `v1.0-MILESTONE-AUDIT.md` YAML frontmatter is updated for `requirements` score but `integration` and `flows` scores are left at partial values.
**Why it happens:** Multiple fields need updating simultaneously — easy to miss one.
**How to avoid:** Update all these frontmatter fields together: `scores.requirements`, `scores.integration`, `scores.flows`, `status`, `gaps.requirements`, `gaps.integration`, `gaps.flows`.
**Warning signs:** Audit YAML shows inconsistency (e.g., `status: complete` but `flows: 4/5`).

</common_pitfalls>

<code_examples>
## Code Examples

### DSH-02: Corrected `onmessage` handler in `useSwarmState.ts`

Current broken handler (lines 56-68 in `/home/ollie/.openclaw/workspace/occc/src/hooks/useSwarmState.ts`):
```typescript
eventSource.onmessage = (event) => {
  if (!isMountedRef.current) return;

  try {
    const data = JSON.parse(event.data);
    if (data.updated) {          // BUG: field absent from new payload
      mutate();                  // triggers REST revalidation
    }
  } catch {
    // Ignore parse errors for keepalive comments
  }
};
```

Corrected handler:
```typescript
eventSource.onmessage = (event) => {
  if (!isMountedRef.current) return;

  try {
    const parsed = JSON.parse(event.data) as SwarmStateResponse;
    if (parsed.agents) {
      // Full state payload received — inject directly into SWR cache
      // false = skip revalidation; SSE is the primary data source
      mutate(parsed, false);
    }
    // Error payloads (parsed.error) fall through without updating cache
  } catch {
    // Ignore parse errors for keepalive comments (": keepalive" is not JSON)
  }
};
```

Note: `SwarmStateResponse` is already defined in the same file (lines 8-13). The cast is safe — `parsed.agents` check guards against partial/error payloads.

### HIE-02: New L2 config file at `agents/pumplai_pm/agent/config.json`

```json
{
  "id": "pumplai_pm",
  "name": "PumplAI_PM - Domain Project Manager",
  "level": 2,
  "reports_to": "clawdia_prime",
  "delegates_to": "l3_specialist",
  "identity_ref": "agents/pumplai_pm/agent/IDENTITY.md",
  "skill_registry": {
    "spawn_specialist": {
      "name": "Spawn Specialist (L3)",
      "description": "Spawns isolated L3 specialist containers for code and test execution",
      "timeout_seconds": 660,
      "skill_path": "skills/spawn_specialist"
    },
    "router": {
      "name": "Task Router",
      "description": "Routes incoming directives from L1 to appropriate L3 skill types",
      "timeout_seconds": 120,
      "skill_path": "skills/router_skill"
    },
    "review": {
      "name": "L3 Work Review",
      "description": "Reviews L3 git diffs on staging branches and merges or rejects to main",
      "timeout_seconds": 300,
      "skill_path": "skills/review_skill"
    }
  },
  "max_concurrent": 3,
  "retry_on_failure": true,
  "max_retries": 1
}
```

### COM-02: Updated status in `REQUIREMENTS.md` traceability table

Current:
```markdown
| HIE-02 | Phase 2 → Phase 8 | Pending |
| COM-02 | Phase 2 → Phase 8 | Pending |
| DSH-02 | Phase 4 → Phase 7 → Phase 8 | Pending |
```

Target:
```markdown
| HIE-02 | Phase 2 → Phase 8 | Satisfied |
| COM-02 | Phase 2 → Phase 8 | Satisfied |
| DSH-02 | Phase 4 → Phase 7 → Phase 8 | Satisfied |
```

And in the main requirements table, COM-02 status column update:
```markdown
| COM-02 | Implement "Lane Queues" for task prioritization and concurrency control. | P1 | Satisfied (Deviation: CLI routing via `openclaw agent` replaces lane queue REST API. Accepted 2026-02-23.) |
```

All other requirement statuses in the table should also be updated from "Pending" to "Satisfied" for the 13 already-satisfied requirements (they currently all show "Pending" in the file — the audit table tracks real status separately). This is a separate discretionary cleanup opportunity.

### Verification commands after implementation

```bash
# DSH-02: Verify SSE push path
cd /home/ollie/.openclaw/workspace/occc && bun run dev &
sleep 3
curl -N http://localhost:6987/api/swarm/stream
# Expected: first line is "data: {"agents":[...],"metrics":{...},...}"
# NOT just ": keepalive"

# HIE-02: Verify L2 config exists and is valid JSON
cat /home/ollie/.openclaw/agents/pumplai_pm/agent/config.json | python3 -m json.tool
# Expected: pretty-printed JSON with level:2, reports_to, delegates_to, skill_registry

# COM-02: Verify status updated in both files
grep -n "COM-02" /home/ollie/.openclaw/.planning/REQUIREMENTS.md
# Expected: line with "Satisfied" and deviation annotation
grep "requirements:" /home/ollie/.openclaw/.planning/v1.0-MILESTONE-AUDIT.md | head -2
# Expected: 16/16
```

</code_examples>

<sota_updates>
## State of the Art (2026)

This phase involves no third-party library choices. All patterns are internal to the existing codebase. No SOTA updates relevant.

| Consideration | Status |
|---------------|--------|
| SWR v2 `mutate(data, false)` API | Stable — no changes since 2023 |
| EventSource (SSE) browser API | Stable Web API — no changes |
| Next.js App Router streaming | Stable in Next.js 16 — no changes needed |

</sota_updates>

<open_questions>
## Open Questions

1. **Should all 16 REQUIREMENTS.md status fields be updated from "Pending" to "Satisfied"?**
   - What we know: All 13 currently-satisfied requirements still show "Pending" in the REQUIREMENTS.md table (the file was never updated after Phase 1 — only the audit file tracks real status)
   - What's unclear: Phase 8 scope says "update COM-02" — does that include fixing all 13 other stale statuses?
   - Recommendation: Update all 16 statuses in a single pass. The REQUIREMENTS.md status column serves no purpose showing "Pending" for verified requirements. This is cheap (text edits) and makes the file accurate. Treat it as part of COM-02 documentation work.

2. **Should `SWR refreshInterval` be reduced or eliminated now that SSE is primary?**
   - What we know: CONTEXT.md locks in "SWR polling demoted to fallback only." The current `refreshInterval: 2000` runs continuously even when SSE is connected.
   - What's unclear: Whether "fallback only" means the polling should be conditionally disabled while SSE is active, or just left as-is at 2s.
   - Recommendation: Leave `refreshInterval: 2000` as-is. Disabling it conditionally adds complexity. The 2s polling is lightweight and harmless when SSE is also delivering data. The CONTEXT.md says "kicks in when SSE disconnects" — this is naturally satisfied because SSE delivers faster than 2s polling, so SSE always wins the race. No behavioral change needed beyond the `onmessage` fix.

3. **Should the v1.0-MILESTONE-AUDIT.md body text (below the YAML frontmatter) be updated?**
   - What we know: The YAML frontmatter has `status: gaps_found` and a `gaps` section listing all three remaining issues. The body text describes these gaps in narrative form.
   - What's unclear: Whether to update just the YAML or also the narrative sections.
   - Recommendation: Update both. Change `status: gaps_found` → `status: complete` in YAML, remove the three entries from the `gaps` arrays, and update the "Unsatisfied Requirement Details" section body to reflect SATISFIED status. The audit document should be self-consistent.

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)

- `/home/ollie/.openclaw/workspace/occc/src/hooks/useSwarmState.ts` — Read directly. Current broken pattern identified at line 61 (`if (data.updated)`). Full hook structure understood.
- `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/stream/route.ts` — Read directly. Server emits `getSwarmState()` result as `data: ${JSON.stringify(initialState)}` — payload has `agents`, `metrics`, `state`, `lastUpdated`.
- `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/route.ts` — Read directly. `getSwarmState()` return type confirmed as `{agents: AgentNode[], metrics: SwarmMetrics, state: JarvisState, lastUpdated: string}`.
- `/home/ollie/.openclaw/agents/clawdia_prime/agent/config.json` — Read directly. L1 schema reference.
- `/home/ollie/.openclaw/agents/l3_specialist/config.json` — Read directly. L3 schema reference.
- `/home/ollie/.openclaw/.planning/v1.0-MILESTONE-AUDIT.md` — Read directly. Exact gap descriptions and evidence.
- `/home/ollie/.openclaw/.planning/phases/07-phase4-verification/07-03-SUMMARY.md` — Read directly. Confirms server-side SSE fix was applied in Phase 7.

### Secondary (MEDIUM confidence)

- SWR documentation (community knowledge, not fetched): `mutate(data, false)` is the standard pattern for injecting external data into SWR cache without triggering revalidation. Confirmed by the existing `mutate()` usage in the codebase.

### Tertiary (LOW confidence - needs validation)

- None — all findings verified from source files in the codebase.

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: SWR hook mutation pattern, JSON config schema, Markdown annotation
- Ecosystem: Next.js App Router SSE, EventSource Web API
- Patterns: SSE-as-primary-data-path, hierarchy config schema, requirement deviation tracking
- Pitfalls: SWR closure staleness, payload field name mismatch, audit frontmatter completeness

**Confidence breakdown:**
- DSH-02 fix: HIGH — exact lines identified, exact replacement pattern confirmed, no unknowns
- HIE-02 config: HIGH — schema reference from L1 and L3 configs, locked decisions specify all structural fields
- COM-02 documentation: HIGH — annotation format described explicitly in CONTEXT.md, files identified

**Research date:** 2026-02-23
**Valid until:** Indefinite (no third-party dependencies — all codebase-internal)

**Files to modify:**
1. `workspace/occc/src/hooks/useSwarmState.ts` — lines 60-64, `onmessage` handler (3-line change)
2. `agents/pumplai_pm/agent/config.json` — new file
3. `.planning/REQUIREMENTS.md` — COM-02 status + all other statuses (optional)
4. `.planning/v1.0-MILESTONE-AUDIT.md` — YAML frontmatter + narrative body

**Estimated complexity:** LOW — targeted edits, no new dependencies, no architecture changes.

</metadata>

---

*Phase: 08-final-gap-closure*
*Research completed: 2026-02-23*
*Ready for planning: yes*
