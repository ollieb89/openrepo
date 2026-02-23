# Phase 10: Housekeeping & Documentation - Research

**Researched:** 2026-02-23
**Domain:** Code cleanup, retroactive documentation, configuration correction, export hygiene
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**redactWithReport() removal:**
- Full removal — delete the function, its types, any test stubs, and all imports referencing it. Clean slate.
- Claude traces the call graph; if nothing calls it at runtime, remove regardless of how many modules import it.
- Commit message references the audit item it closes (e.g. `fix(debt): remove unused redactWithReport (closes TD-XX)`)

**Retroactive verification docs (Phase 5 & 8):**
- Evidence from git — pull evidence from commit history and existing code state (diffs, test results, code inspection). Pragmatic, not re-running live checks.
- Same format as other VERIFICATION.md files — no special 'retroactive' marker or lighter format
- Best-effort inference where criteria can't be fully evidenced — note confidence level where uncertain, don't mark as unverifiable
- Separate commits — one commit per phase's verification doc

**Path & export fixes:**
- Audit all agent configs — while fixing `pumplai_pm` workspace path, check all `agents/` config files for stale or incorrect path references
- Audit all orchestration exports — while adding `snapshot.py` to `orchestration/__init__.py` `__all__`, verify all modules in `orchestration/` are properly exported
- Fix trivial findings discovered during audits (simple path/export corrections). Log anything structural as new tech debt.
- Group commits by type — one commit for all path fixes, one commit for all export fixes

### Claude's Discretion
- Exact audit methodology for path and export scanning
- How to structure git evidence in verification docs (which commits to reference, how to present diffs)
- Whether to scan beyond `agents/` and `orchestration/` if patterns suggest broader issues
- Ordering of the work items within the phase

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 10 is a pure housekeeping pass — no new capabilities, no requirement gaps to close. It cleans up five specific tech debt items surfaced by the v1.0 milestone audit. The work divides cleanly into three independent tracks: (1) retroactive verification docs for Phases 5 and 8, (2) removal of the unused `redactWithReport()` function from the TypeScript redaction module, and (3) two configuration/export fixes (pumplai_pm workspace path in SOUL.md and missing `snapshot.py` export in `orchestration/__init__.py`).

All five items are mechanical — the audit found them, the codebase state is already final, and the fixes require no architectural decisions. The retroactive VERIFICATION.md files require the most judgment because the evidence must be inferred from git history and code inspection rather than live test runs. The `redactWithReport()` removal requires call-graph tracing. The path/export fixes are single-line edits.

The phase depends on Phase 9 having completed, but the five items are independently addressable and can be planned and executed in any order. The natural sequence is: verification docs first (documentation, no risk), then redactWithReport() removal (one TypeScript file), then path/export fixes (two separate commits).

**Primary recommendation:** Sequence the work as three logical commits: (a) Phase 5 VERIFICATION.md, (b) Phase 8 VERIFICATION.md, (c) redactWithReport() removal, (d) path fixes, (e) export fixes. Each is independently reviewable and revertable.

---

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python stdlib (pathlib, json) | 3.x | orchestration/__init__.py export fix | All orchestration code uses stdlib only |
| TypeScript | 5.x (project standard) | redaction.ts edit | Already in workspace/occc stack |
| git log / git show | project git | Evidence gathering for retroactive docs | Version-controlled evidence is authoritative |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `grep` / Read tool | Call-graph tracing for redactWithReport() | Verifying no consumers before removal |
| Existing VERIFICATION.md files as templates | Format reference for retroactive docs | All VERIFICATION.md files follow the same YAML + markdown structure |

### No External Dependencies

This phase introduces zero new libraries. All edits are to existing files using existing patterns.

---

## Architecture Patterns

### VERIFICATION.md Format

All verification docs in this project follow a consistent two-part format:

**YAML frontmatter:**
```yaml
---
phase: {phase-slug}
verified: {ISO timestamp}
status: complete | passed
score: N/N must-haves verified
gaps: []
---
```

**Markdown body sections:**
1. Header with Phase Goal, Verified date, Status, Re-verification note
2. `## Goal Achievement` with Observable Truths table (# | Truth | Status | Evidence)
3. `## Required Artifacts` table (Artifact | Expected | Status | Details)
4. `## Key Link Verification` table (From | To | Via | Status | Details)
5. `## Requirements Coverage` table (Requirement | Source Plan | Description | Status | Evidence)
6. `## Anti-Patterns Found`
7. `## Remediation Summary` (if applicable)
8. `## Phase Completion` summary paragraph

Reference files: `/home/ollie/.openclaw/.planning/phases/01-environment-substrate/01-VERIFICATION.md` and `/home/ollie/.openclaw/.planning/phases/06-phase3-verification/06-VERIFICATION.md`.

### Retroactive Evidence Sourcing

For phases without live test runs, evidence comes from three sources ranked by authority:

1. **Git commits** — `git log --oneline` and `git show {hash}` provide timestamped proof of what was changed and when
2. **Code inspection** — Read current file state and verify presence of expected artifacts, patterns, and integrations
3. **SUMMARY.md files** — Each executed plan has a SUMMARY.md with verification output captured at execution time

For Phase 5 and Phase 8, all three sources are available. The SUMMARY files contain the actual verification output from when the work was executed.

### Export Audit Pattern

For `orchestration/__init__.py`, the pattern is:
1. List all `.py` files in `orchestration/` that define public symbols
2. Cross-reference against current `__all__` list
3. For any module not in `__all__`: determine if it exports public symbols, add if yes
4. For each addition: also add the `from .{module} import {Symbol}` line

Current state of `orchestration/__init__.py`:
```python
from .state_engine import JarvisState
from .config import STATE_FILE, LOCK_TIMEOUT, POLL_INTERVAL, SNAPSHOT_DIR
from .init import initialize_workspace, verify_workspace

__all__ = ['JarvisState', 'STATE_FILE', 'LOCK_TIMEOUT', 'POLL_INTERVAL', 'SNAPSHOT_DIR', 'initialize_workspace', 'verify_workspace']
```

`snapshot.py` is missing — it exports: `create_staging_branch`, `capture_semantic_snapshot`, `l2_review_diff`, `l2_merge_staging`, `l2_reject_staging`, `cleanup_old_snapshots`, `GitOperationError`.

`monitor.py` is a CLI module (has `if __name__ == '__main__'`) — not appropriate for `__all__`.

### Anti-Patterns to Avoid

- **Retroactive fabrication:** Do not write verification evidence that wasn't gathered at execution time. Use phrases like "Code inspection confirms..." or "Commit {hash} shows..." rather than claiming test runs.
- **Over-export:** Do not add `monitor.py` to `__all__` — it is a CLI entry point, not a library module.
- **Partial removal:** When removing `redactWithReport()`, also remove its return type `RedactionResult` interface IF it is not used by anything else. Check `redactSensitiveData()` — it returns `string`, not `RedactionResult`. `RedactionResult` is used only by `redactWithReport()`. Both should be removed together.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verification evidence | New test script runs | Existing SUMMARY.md output + code inspection | Phase is already complete — re-running live tests is not necessary and may fail if environment differs |
| Export scanning | Custom introspection tool | Read `orchestration/*.py` files and grep for `def ` at module level | Simple and auditable |

---

## Common Pitfalls

### Pitfall 1: Retroactive docs feel weaker than live-run docs

**What goes wrong:** Writer hedges every statement with "probably" or "likely", making the doc feel unverifiable.

**Why it happens:** Uncertainty about whether inferred evidence is acceptable.

**How to avoid:** The locked decision explicitly allows "best-effort inference" with confidence notes where uncertain. Where SUMMARY.md output is available (it is, for both Phase 5 and Phase 8), that output IS the verification result. Cite it directly. The doc should read the same as a live-run verification.

**Warning signs:** Overuse of qualifiers; check if a SUMMARY.md has actual output first.

### Pitfall 2: Removing redactWithReport() leaves a dangling RedactionResult type

**What goes wrong:** `redactWithReport` is deleted but `RedactionResult` interface remains, causing a TypeScript warning or an orphaned export.

**Why it happens:** The interface is defined before the function and might look independent.

**How to avoid:** Check whether `RedactionResult` is used anywhere other than `redactWithReport`. Search confirms it is not — `redactSensitiveData()` returns `string`. Remove both the function and the interface together.

**Warning signs:** TypeScript will catch this if interface is used elsewhere; grep confirms it isn't.

### Pitfall 3: pumplai_pm "workspace path" is in SOUL.md, not config.json

**What goes wrong:** Fixer edits config.json looking for a workspace path field that doesn't exist there.

**Why it happens:** The audit item says "pumplai_pm workspace path" — natural assumption is config.json.

**How to avoid:** The actual stale path is in `agents/pumplai_pm/agent/SOUL.md` line 6: `"Scope: Primary authority over the /home/ollie/Development/Projects/pumplai workspace."` The correct path should be the openclaw workspace: `/home/ollie/.openclaw/workspace`.

**The config.json** has no workspace path field — it uses `skill_path` references (relative paths to skills) and `identity_ref`. Those are correct.

### Pitfall 4: Over-scoping the agent path audit

**What goes wrong:** During the "audit all agent configs" sweep, fixer changes SOUL.md/IDENTITY.md content that is intentionally about the pumplai project domain (PumplAI_PM's role is to manage the pumplai project).

**Why it happens:** The locked decision says "audit all agents for stale or incorrect path references." This could be read too broadly.

**How to avoid:** The audit scopes to machine-readable **path references** (config.json files, SOUL.md Scope lines that reference filesystem paths). Content describing the agent's domain/specialization (e.g. IDENTITY.md's "PumplAI Ecosystem" description) is intentional and should not be changed. Only fix filesystem paths that are factually incorrect for where openclaw actually runs.

### Pitfall 5: Phase 9 dependency

**What goes wrong:** Phase 10 tasks assume Phase 9's INT-01 fixes (openclaw.json hierarchy fields) are in place when writing Phase 8 VERIFICATION.md evidence.

**Why it happens:** Phase 10 depends on Phase 9, but Phase 9 has not yet been executed (no SUMMARY files exist).

**How to avoid:** Phase 10's five items are all independent of Phase 9's INT-01/INT-02/INT-03 fixes. The retroactive verification docs cover Phases 5 and 8 only, which were fully complete before Phase 9. The export and path fixes are unrelated to Phase 9's changes. No Phase 10 task requires Phase 9 to have landed — but the planner should sequence Phase 10 execution after Phase 9 completion.

---

## Code Examples

### Current orchestration/__init__.py (confirmed by code inspection)

```python
# Source: /home/ollie/.openclaw/orchestration/__init__.py (line 1-5)
from .state_engine import JarvisState
from .config import STATE_FILE, LOCK_TIMEOUT, POLL_INTERVAL, SNAPSHOT_DIR
from .init import initialize_workspace, verify_workspace

__all__ = ['JarvisState', 'STATE_FILE', 'LOCK_TIMEOUT', 'POLL_INTERVAL', 'SNAPSHOT_DIR', 'initialize_workspace', 'verify_workspace']
```

**Required change** — add snapshot.py public symbols:
```python
from .state_engine import JarvisState
from .config import STATE_FILE, LOCK_TIMEOUT, POLL_INTERVAL, SNAPSHOT_DIR
from .init import initialize_workspace, verify_workspace
from .snapshot import (
    create_staging_branch,
    capture_semantic_snapshot,
    l2_review_diff,
    l2_merge_staging,
    l2_reject_staging,
    cleanup_old_snapshots,
    GitOperationError,
)

__all__ = [
    'JarvisState',
    'STATE_FILE', 'LOCK_TIMEOUT', 'POLL_INTERVAL', 'SNAPSHOT_DIR',
    'initialize_workspace', 'verify_workspace',
    'create_staging_branch', 'capture_semantic_snapshot',
    'l2_review_diff', 'l2_merge_staging', 'l2_reject_staging',
    'cleanup_old_snapshots', 'GitOperationError',
]
```

### redactWithReport() removal scope (confirmed by code inspection)

```typescript
// Source: /home/ollie/.openclaw/workspace/occc/src/lib/redaction.ts
// Lines to REMOVE:
// - Interface RedactionResult (lines 19-22) — only consumed by redactWithReport
// - Function redactWithReport (lines 147-167) — unused export

// Lines to KEEP:
// - Interface RedactionPattern (lines 12-17)
// - Constant REDACTION_PATTERNS (lines 27-125)
// - Function redactSensitiveData (lines 131-141) — actively used by docker.ts
```

Verification after removal:
```bash
grep -n "redactWithReport\|RedactionResult" workspace/occc/src/lib/redaction.ts
# Expected: no output (both removed)
grep -rn "redactWithReport\|RedactionResult" workspace/occc/src/
# Expected: no output (no consumers existed)
```

### pumplai_pm SOUL.md workspace path fix

```markdown
# Current (stale — references pumplai project, not openclaw workspace)
- **Scope:** Primary authority over the `/home/ollie/Development/Projects/pumplai` workspace.

# Corrected (openclaw workspace)
- **Scope:** Primary authority over the `/home/ollie/.openclaw/workspace` workspace.
```

File: `/home/ollie/.openclaw/agents/pumplai_pm/agent/SOUL.md` line 6.

### Phase 5 retroactive verification evidence anchors

All three SUMMARY files exist and contain captured verification output:

- `05-01-SUMMARY.md` — L1 Config creation and delegation wiring. Contains test run output showing `[✓] Config Loading`, `[✓] Skill Resolution`, `[✓] Gateway Connectivity`, and PASS result for `verify_l1_delegation.py`.
- `05-02-SUMMARY.md` — Snapshot initialization. Contains test run showing `✓ Snapshots directory already exists`, `✓ Orchestration modules importable`, and `verify_snapshots.py` PASS result.
- `05-03-SUMMARY.md` — Integration verification. Contains `verify_phase5_integration.py` run showing `PHASE 5 COMPLETE` (exit 0).

Requirements covered by Phase 5: COM-01 (partial — wiring correct, delegation WARN due to schema issue), COM-04 (snapshots directory guaranteed).

### Phase 8 retroactive verification evidence anchors

- `08-01-SUMMARY.md` — All three gap closures with inline verification commands and their expected results.
- Commit `8bca125` — `feat(hie-02): add pumplai_pm L2 machine-readable config`
- Commit `a7826bc` — `docs(com-02): formalize deviation and mark v1.0 complete`
- Verification commands from SUMMARY: `grep "mutate(parsed, false)"`, `python3 -c "import json; assert d['level']==2"`, `grep "COM-02" | grep "Satisfied"`.

Requirements covered by Phase 8: DSH-02 (SSE push path), HIE-02 (L2 config), COM-02 (spec deviation accepted).

---

## Findings by Item

### Item 1: Phase 5 VERIFICATION.md

**Evidence quality:** HIGH — three SUMMARY files with captured test output; all success criteria explicitly listed in each SUMMARY.

**Approach:** Pull Observable Truths from the Phase 5 success criteria (05-CONTEXT.md SC1/SC2/SC3). For each truth, cite the specific SUMMARY file section and verification command output. Note the COM-01 delegation WARN as a known limitation (wiring correct, runtime schema issue is tech debt, not a failure of Phase 5's scope).

**Key truths to verify:**
1. `agents/clawdia_prime/agent/config.json` exists with skill_registry.router referencing `skills/router_skill`
2. L1 → L2 delegation wiring is correct (script PASS, with WARN for schema validation — not a wiring failure)
3. `workspace/.openclaw/snapshots/` directory exists and snapshot module importable
4. `orchestration/init.py` initializes workspace idempotently

**File to create:** `.planning/phases/05-wiring-fixes/05-VERIFICATION.md`

### Item 2: Phase 8 VERIFICATION.md

**Evidence quality:** HIGH — 08-01-SUMMARY.md contains explicit verification commands and their expected outputs; two named commits with specific diffs.

**Approach:** Three requirements, three Observable Truths with git commit hashes as evidence. The verification commands from the SUMMARY become the "Evidence" column entries.

**Key truths to verify:**
1. `useSwarmState.ts` contains `mutate(parsed, false)` with `parsed.agents` guard (commit `8bca125` + `a7826bc`)
2. `agents/pumplai_pm/agent/config.json` valid JSON with `level: 2`, `reports_to`, `delegates_to`, skill_registry
3. REQUIREMENTS.md shows COM-02 Satisfied with deviation annotation; v1.0-MILESTONE-AUDIT.md shows 16/16, 5/5

**File to create:** `.planning/phases/08-final-gap-closure/08-VERIFICATION.md`

### Item 3: redactWithReport() removal

**Call graph trace (confirmed by codebase search):**
- Defined in: `workspace/occc/src/lib/redaction.ts` lines 147-167
- Consumers: **zero** — no file in `workspace/occc/src/` imports `redactWithReport`
- `RedactionResult` interface: only consumed by `redactWithReport` — safe to remove
- `redactSensitiveData` (the used function): returns `string`, does not use `RedactionResult`

**Scope of deletion:** Lines 19-22 (`RedactionResult` interface) and lines 147-167 (`redactWithReport` function body + JSDoc comment). No other files need editing.

**Verification:** grep for `redactWithReport` and `RedactionResult` across `workspace/occc/src/` returns empty.

### Item 4: pumplai_pm workspace path fix

**Location confirmed:** `agents/pumplai_pm/agent/SOUL.md` line 6 — `Scope:` references `/home/ollie/Development/Projects/pumplai`.

**Correct value:** `/home/ollie/.openclaw/workspace` — this is where openclaw's actual workspace lives.

**Agent config audit sweep results:**
- `clawdia_prime/agent/config.json`: No path references; gateway endpoint is a URL (not filesystem path). Clean.
- `pumplai_pm/agent/config.json`: No filesystem paths; skill_paths are relative. Clean.
- `l3_specialist/config.json`: No filesystem paths. Clean.
- `pumplai_pm/agent/SOUL.md`: **STALE** — `/home/ollie/Development/Projects/pumplai` should be `/home/ollie/.openclaw/workspace`
- Other agent identity/soul files reference hierarchy relationships, not filesystem paths. No other stale paths found.

**Trivial finding:** `pumplai_pm/agent/IDENTITY.md` line 3 says "Specialization: PumplAI Ecosystem (Next.js 16 / FastAPI)" and line 12 says "Project Context: Maintain deep knowledge of the PumplAI codebase." This is intentional domain description, not a stale path. Do not change.

### Item 5: snapshot.py export

**Current state:** `orchestration/__init__.py` exports `JarvisState`, `STATE_FILE`, `LOCK_TIMEOUT`, `POLL_INTERVAL`, `SNAPSHOT_DIR`, `initialize_workspace`, `verify_workspace`. `snapshot.py` is NOT in `__all__`.

**Public symbols in snapshot.py** (confirmed by file inspection): `GitOperationError`, `create_staging_branch`, `capture_semantic_snapshot`, `l2_review_diff`, `l2_merge_staging`, `l2_reject_staging`, `cleanup_old_snapshots`.

**Orchestration module audit results:**
- `state_engine.py`: `JarvisState` — already exported. Clean.
- `config.py`: `STATE_FILE`, `LOCK_TIMEOUT`, `POLL_INTERVAL`, `SNAPSHOT_DIR` — already exported. Clean.
- `init.py`: `initialize_workspace`, `verify_workspace` — already exported. Clean.
- `snapshot.py`: All 7 public symbols — **NOT exported**. Fix needed.
- `monitor.py`: CLI entry point with `if __name__ == '__main__'`. Not a library module. Should not be in `__all__`.

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| Inline verification evidence in SUMMARY.md | Dedicated VERIFICATION.md with structured tables | Phases 5 and 8 used SUMMARY.md only — this phase adds the formal doc |
| snapshot.py imported via `from orchestration.snapshot import ...` | After fix: `from orchestration import capture_semantic_snapshot` | Both work; __all__ enables the cleaner form |

---

## Open Questions

1. **Does Phase 9 need to complete before Phase 10 can execute?**
   - What we know: Phase 10's 5 items are all independent of Phase 9's INT-01/INT-02/INT-03 changes. None of the Phase 10 items touch openclaw.json, spawn.py, docker.ts, or review_skill.
   - What's unclear: Whether the PLAN should note the dependency explicitly or treat them as safely parallelizable.
   - Recommendation: The planner should note the roadmap dependency but confirm that all Phase 10 tasks are independently executable. If Phase 9 is in progress, Phase 10 can be planned and executed concurrently without conflict.

2. **Should the pumplai_pm SOUL.md specialization description be updated beyond the path fix?**
   - What we know: SOUL.md describes PumplAI_PM as specialized for the pumplai project (Next.js 16 / FastAPI), but in openclaw, PumplAI_PM manages the openclaw workspace (Next.js dashboard + Python orchestration).
   - What's unclear: Whether the locked decision ("audit all agent configs for stale or incorrect path references") includes semantic content or only filesystem path strings.
   - Recommendation: Treat as out of scope per the locked decision language. The locked decision specifies "path references" — fix the one path (line 6 of SOUL.md), leave the domain description intact. Log the semantic mismatch as a new tech debt item if it seems significant.

---

## Validation Architecture

*(nyquist_validation is not set in .planning/config.json — this section is omitted per the research instructions.)*

---

## Sources

### Primary (HIGH confidence)

- `/home/ollie/.openclaw/orchestration/__init__.py` — Current export state verified by direct file inspection
- `/home/ollie/.openclaw/orchestration/snapshot.py` — All public symbols catalogued by file inspection
- `/home/ollie/.openclaw/workspace/occc/src/lib/redaction.ts` — `redactWithReport` location and `RedactionResult` interface confirmed
- `/home/ollie/.openclaw/agents/pumplai_pm/agent/SOUL.md` — Stale path confirmed at line 6
- `/home/ollie/.openclaw/.planning/v1.0-MILESTONE-AUDIT.md` — Tech debt items and evidence source confirmed
- `/home/ollie/.openclaw/.planning/phases/05-wiring-fixes/05-01-SUMMARY.md` — Phase 5 plan 1 verification output
- `/home/ollie/.openclaw/.planning/phases/05-wiring-fixes/05-02-SUMMARY.md` — Phase 5 plan 2 verification output
- `/home/ollie/.openclaw/.planning/phases/05-wiring-fixes/05-03-SUMMARY.md` — Phase 5 plan 3 verification output
- `/home/ollie/.openclaw/.planning/phases/08-final-gap-closure/08-01-SUMMARY.md` — Phase 8 verification output
- All existing VERIFICATION.md files — Format template reference

### Secondary (MEDIUM confidence)

- `git log --oneline` output — Confirms Phase 8 commit hashes (`8bca125`, `a7826bc`)
- Codebase grep for `redactWithReport` consumers — Confirms zero imports

---

## Metadata

**Confidence breakdown:**
- Item identification: HIGH — all 5 items confirmed by direct inspection, not inference
- Evidence availability: HIGH — SUMMARY files exist for Phases 5 and 8 with captured output
- Removal safety (redactWithReport): HIGH — grep confirms zero consumers
- Path fix location: HIGH — SOUL.md line 6 confirmed; config.json has no path fields
- Export fix scope: HIGH — snapshot.py public API confirmed; monitor.py correctly excluded

**Research date:** 2026-02-23
**Valid until:** Stable — these are fixed code states, not evolving APIs. Valid until files are edited.
