# Project Research Summary

**Project:** OpenClaw v1.1 — Project Agnostic Multi-Project Framework
**Domain:** AI Swarm Orchestration — Multi-Project Support
**Researched:** 2026-02-23
**Confidence:** HIGH

## Executive Summary

OpenClaw v1.0 is a fully operational single-project AI swarm orchestration system with a proven 3-tier architecture (L1 → L2 → L3), Docker-based container execution, and a Next.js monitoring dashboard. The v1.1 milestone transforms this from a single-project tool into a multi-project framework. The core challenge is not architectural reinvention — the v1.0 architecture is sound — but surgical decoupling of hardcoded single-project assumptions embedded throughout the codebase: a global state file path, a shared container pool semaphore, a hardcoded dashboard SSE endpoint, and a SOUL.md file with burned-in PumplAI-specific identity.

The recommended approach is to build in strict dependency order: first decouple all config from project-specific constants (`project_config.py` extensions, per-project state file paths, agent source-of-truth migration to project manifests), then wire that decoupled config through the runtime layer (spawn.py, pool.py, monitor.py, snapshot.py), then add the user-facing CLI subcommands and SOUL templating, and finally update the dashboard. All new capabilities are achievable exclusively with Python stdlib and already-installed frontend packages — no new dependencies are required. The infrastructure for per-project JSON manifests, pool configuration, and SWR polling already exists from v1.0 pre-work.

The primary risk is data corruption from cross-project state file contamination, which can occur if any part of the v1.1 work ships without the config decoupling foundation in place. A secondary risk is breaking the existing PumplAI workflow when implementing SOUL templating — the rendered output must be semantically identical to the v1.0 hardcoded SOUL.md. Both risks are avoidable with a Phase 1 that completes config decoupling and establishes golden-baseline tests before any runtime or UI work begins.

---

## Key Findings

### Recommended Stack

v1.1 requires zero new dependencies. All Python additions use stdlib (`argparse`, `string.Template`, `pathlib`, `json`, `asyncio.Semaphore`). All frontend additions use already-installed packages (`swr@2.4.0`, `zod@4.3.6`, Next.js `fs` API routes). The key technology decisions are about which stdlib approach to use: `string.Template.safe_substitute()` over Jinja2 (not installed, overkill for markdown key substitution where `$` shell vars must pass through unchanged), and `argparse` over Click/Typer (consistent with existing `spawn.py` CLI pattern, no new dep for 4 subcommands).

**Core technologies:**
- `argparse` (stdlib): Project CLI subcommands (`init/switch/list/remove`) — consistent with existing monitor.py/spawn.py CLI pattern, zero new dependency
- `string.Template.safe_substitute()` (stdlib): SOUL/IDENTITY markdown templating — `safe_substitute()` is critical because SOUL files contain `$VARIABLE` shell examples that must not be consumed by the template engine
- `pathlib.Path` + `json` (stdlib): Project directory scaffolding and per-project state file management — same pattern as existing `project_config.py`
- `asyncio.Semaphore` dict (stdlib): Per-project pool isolation — extends existing `pool.py` with a `_project_semaphores` module-level registry, no new library
- `swr` + `zod` (already installed): Dashboard project switcher API polling and response validation — reuse exact existing patterns from swarm status

**See STACK.md for full version compatibility table and alternatives considered.**

### Expected Features

v1.1 has a clear P1/P2/P3 split. The P1 set is the minimum to make multi-project work at all.

**Must have (P1 — table stakes for multi-project):**
- `openclaw project init/list/switch/remove` CLI — without this, adding a project requires manual JSON editing
- Per-project state file isolation — prevents task log contamination between projects; the most critical data integrity requirement
- SOUL.md template rendering — new projects need a coherent L2 agent identity at `init`; projects without a rendered SOUL are broken at first message
- Project-labeled Docker containers (`openclaw.project` label) — required for dashboard filtering and safe management operation scoping
- Dashboard project switcher — without it, the occc UI becomes unusable with 2+ projects active

**Should have (P2 — add when P1 stable, triggered by real use):**
- Project init templates (`--template fullstack|backend|ml-pipeline`) — saves ~10 min config per project; trigger: user creates 3+ projects manually
- Configurable pool isolation (`"pool_isolation": "isolated"` per project) — trigger: two concurrent projects interfere with each other's L3 concurrency slots

**Defer (v2+):**
- Project archiving (pause without deletion)
- Cross-project agent sharing (conflicts with current 1:1 L2-to-project assumption)
- Per-project agent hierarchy filtering in dashboard (cosmetic, schedule v1.2)
- Project usage metrics (tokens, container time, cost — requires billing integration)

**Anti-features to avoid:**
- Global shared `workspace-state.json` for all projects — lock contention and cross-project data contamination
- LLM-generated SOUL at init time — network dependency in a CLI operation, non-deterministic output
- Kubernetes/per-project Docker networks — massive overhead with no functional benefit over semaphore isolation

**See FEATURES.md for dependency graph, user workflow scenarios, and full prioritization matrix.**

### Architecture Approach

The v1.1 architecture extends v1.0 by adding a Project Registry Layer and Project CLI, then threading per-project context through every existing component that currently hardcodes single-project paths or global singletons. The `JarvisState` engine itself requires no changes (it already accepts any path via constructor). The change is in path resolution: all state file, snapshot directory, and workspace path resolution must flow through `project_config.get_state_file(project_id)` rather than module-level constants.

**Major components and their v1.1 status:**
1. `orchestration/project_config.py` (EXTEND) — add `list_projects()`, `create_project()`, `remove_project()`, `switch_active_project()`, `get_state_file(project_id)`, `get_snapshot_dir(project_id)` — the foundation everything else depends on
2. `orchestration/cli/project.py` (NEW) — `openclaw project init/switch/list/remove` using argparse subparsers
3. `orchestration/soul_template.py` (NEW) — section-based merge of `agents/templates/soul-defaults.md` with `projects/<id>/soul-override.md`; output written to `agents/<id>/agent/SOUL.md` at init time only
4. `skills/spawn_specialist/spawn.py` (MODIFY) — inject `OPENCLAW_PROJECT` env var into container, add `openclaw.project` Docker label
5. `skills/spawn_specialist/pool.py` (MODIFY) — per-project semaphore registry; `L3ContainerPool` gains `project_id` param; shared semaphore remains default
6. `workspace/occc/src/app/api/projects/route.ts` (NEW) — `GET /api/projects` list, `PATCH /api/projects/active` switch
7. `workspace/occc/src/app/api/swarm/route.ts` + `stream/route.ts` (MODIFY) — accept `?project=<id>` query param; cache becomes `Map<projectId, CachedState>`
8. `workspace/occc/src/components/ProjectSwitcher.tsx` (NEW) — dropdown in top nav; SWR polling for project list

**State file layout after v1.1:**
```
.openclaw/                    # root-level state dir (migrated from workspace/.openclaw/)
  pumplai-state.json
  <project-id>-state.json
  snapshots/pumplai/
  snapshots/<project-id>/
```

**Critical path:** `project_config.py` extensions → `spawn.py` + `pool.py` + `monitor.py` + `snapshot.py` modifications → CLI + SOUL templating + migration → dashboard.

**See ARCHITECTURE.md for full data flow diagrams, build order, and anti-patterns.**

### Critical Pitfalls

8 pitfalls identified from direct codebase inspection — these are specific broken code paths, not hypothetical scenarios.

1. **Single global state file becomes cross-project data corruption vector** — `update_task()` read-modify-write under LOCK_EX silently overwrites cross-project state when both projects use the same JSON file. Prevention: `get_state_file(project_id)` returning distinct paths; pass as argument never as module global. Must be Phase 1.

2. **`active_project` in `openclaw.json` is a mutable global** — `openclaw project switch` mid-flight changes state file resolution for in-flight L3 containers. Prevention: resolve lookup as `--project flag > OPENCLAW_PROJECT env var > active_project fallback`; embed project ID in container env at spawn time. Must be Phase 1.

3. **SOUL templates break existing PumplAI workflow if rendering is not semantically identical** — Template substitution that drops any agent reference invalidates ClawdiaPrime's L2 memory. Prevention: generate golden baseline from v1.0 SOUL.md; assert rendered output matches before shipping; template is append-only for v1.1. Phase 1 exit criterion.

4. **Container names collide across projects** — `openclaw-l3-{task_id}` produces Docker `409 Conflict` under concurrent multi-project use; retry logic masks the root cause. Prevention: `openclaw-{project_id}-l3-{task_id}` naming; add `openclaw.project_id` Docker label. Phase 1 (label schema) + Phase 2 (naming enforcement).

5. **Snapshot system hardcodes `"main"` branch** — Non-main-branch projects produce empty diffs and failed merges silently. Prevention: `detect_default_branch(workspace_path)` utility replacing all hardcoded `"main"` references in `snapshot.py`. Phase 2.

6. **Dashboard SSE stream has no project context** — Always streams one hardcoded state file path; module-level singleton cache cannot hold two projects. Prevention: `?project=<id>` on both REST and SSE routes; `Map<projectId, CachedState>` cache. Phase 4.

7. **`openclaw.json` agent list contamination** — Adding new project agents to the global list pollutes PumplAI hierarchy view. Prevention: dashboard hierarchy driven by `project.json:agents` for active project; never modify `openclaw.json:agents.list` when adding new projects. Phase 1.

8. **Shared L3 pool semaphore enforces wrong concurrency boundary** — One project's 600s tasks starve all other projects. Prevention: per-project semaphore opt-in via `"pool_isolation": "isolated"` in `project.json`. Acceptable as documented limitation in v1.1 if shipped as P2 feature.

**See PITFALLS.md for warning signs, recovery strategies, and a "looks done but isn't" verification checklist.**

---

## Implications for Roadmap

The research establishes a clear dependency graph that maps directly to phases. The critical constraint is that all state/config decoupling must complete before any multi-project runtime work begins — anything else creates data corruption risk for the live PumplAI v1.0 system.

### Phase 1: Config Decoupling and Foundation

**Rationale:** Everything else depends on `project_config.py` extensions and state file path resolution. This phase has zero dependencies on new code. Five of the eight critical pitfalls have a "Phase 1" prevention tag — they cannot be addressed later without risking data corruption in production. The SOUL template golden baseline test is a non-negotiable exit criterion.

**Delivers:**
- `project_config.py`: `get_state_file()`, `get_snapshot_dir()`, `list_projects()`, `create_project()`, `remove_project()`, `switch_active_project()`
- State file path convention: `.openclaw/<project_id>-state.json`
- `openclaw.json` agent list decoupled from dashboard hierarchy (`project.json` becomes source of truth)
- `OPENCLAW_PROJECT` env-var-first lookup pattern established as canonical across all callers
- Golden baseline test: rendered PumplAI SOUL.md == v1.0 hardcoded SOUL.md (diff must be empty)
- State file migration: `workspace/.openclaw/workspace-state.json` → `.openclaw/pumplai-state.json`

**Avoids:** Pitfalls 1 (global state contamination), 4 (active_project mutable global), 5 (SOUL fidelity break), 8 (agent list contamination)

**Research flag:** Standard patterns — no additional research needed. All changes are direct extensions of existing code with full codebase analysis as evidence base.

---

### Phase 2: Multi-Project Runtime

**Rationale:** Can only begin after Phase 1 delivers stable path resolution. Modifies the Docker layer and container pool. The snapshot `"main"` branch fix is a Phase 2 hard requirement — it will silently break the first non-PumplAI project otherwise.

**Delivers:**
- `spawn.py`: `OPENCLAW_PROJECT` env var injection, `openclaw.project` + `openclaw.project_id` Docker labels, `openclaw-{project_id}-l3-{task_id}` container naming
- `pool.py`: per-project semaphore registry, `L3ContainerPool(project_id, pool_mode)` refactor, `spawn_task()` convenience function fixed or removed
- `monitor.py`: `--project <id>` flag, state-file resolved from `project_config`
- `snapshot.py`: `detect_default_branch(workspace_path)` utility replacing all hardcoded `"main"` references
- `project.json` schema additions: `pool_isolation: "shared"|"isolated"`, `git.default_branch` optional field

**Avoids:** Pitfalls 2 (container name collision), 3 (pool semaphore starvation), 7 (snapshot branch failure)

**Research flag:** Standard patterns — asyncio.Semaphore dict and Docker label patterns are well-documented. Note: catalogue all `spawn_task()` call sites before Phase 2 begins (see Gaps section).

---

### Phase 3: Project CLI and SOUL Templating

**Rationale:** The CLI and SOUL engine depend on Phase 1 CRUD but are independent of Phase 2 runtime. These two sub-tracks can be built in parallel within this phase. SOUL templating only runs at `init` time — no runtime dependency.

**Delivers:**
- `orchestration/cli/project.py`: `openclaw project init/switch/list/remove` with argparse subparsers
- `orchestration/soul_template.py`: section-based merge of default + project override; written to `agents/<id>/agent/SOUL.md` at init time
- `agents/templates/`: `soul-defaults.md`, `l1-soul-template.md`, `l2-soul-template.md`
- `projects/pumplai/soul-override.md`: retroactive project-specific overrides for the existing project
- `projects/templates/fullstack/`, `backend/`, `ml-pipeline/` scaffold directories
- UX guards: `--confirm` on `remove`, in-flight task check before `switch`, agent ID validation on `init`

**Avoids:** Pitfall 5 (SOUL fidelity break), UX pitfalls (accidental deletion, init using wrong agent IDs)

**Research flag:** SOUL section-based merge edge cases need a brief implementation spike before committing to the approach — specifically: what happens when the override adds a section absent from the default template? Resolve this before writing the full merge engine.

---

### Phase 4: Dashboard Project Switcher

**Rationale:** Depends on Phase 1 (stable project_config layout) but can be developed in parallel with Phases 2 and 3 once Phase 1 is complete. Dashboard changes are isolated to the occc Next.js layer. REST and SSE routes must be updated in the same deploy — updating one without the other creates split-brain state.

**Delivers:**
- `workspace/occc/src/app/api/projects/route.ts`: `GET /api/projects`, `PATCH /api/projects/active`
- `workspace/occc/src/app/api/swarm/route.ts`: `?project=<id>` query param, `Map<projectId, CachedState>` cache
- `workspace/occc/src/app/api/swarm/stream/route.ts`: `?project=<id>` query param
- `workspace/occc/src/components/ProjectSwitcher.tsx`: dropdown in top nav, SWR polling
- `workspace/occc/src/hooks/useSwarmState.ts`: active project included in all query params

**Avoids:** Pitfall 6 (dashboard SSE single-file binding and stale cache)

**Research flag:** Standard Next.js API route + SWR patterns. No additional research needed. `useSWRMutation` for the switch POST is well-documented.

---

### Phase 5: End-to-End Verification and P2 Features

**Rationale:** Verify the complete multi-project workflow with a real second project before adding P2 features. Treat Phase 5 as a quality gate — P2 features only land once the P1 system is stable under real multi-project conditions.

**Delivers:**
- Second project created and operated via `openclaw project init` (non-PumplAI)
- L3 tasks spawned for both projects simultaneously; state isolation verified
- Dashboard project switch verified (all panels update within one SSE cycle)
- `--template fullstack|backend|ml-pipeline` project init templates (P2)
- `"pool_isolation": "isolated"` configurable per project (P2)

**Verification checklist (from PITFALLS.md "looks done but isn't"):**
- Two active projects produce two distinct state file paths; no task ID appears in both files
- `docker ps` shows distinct name prefixes per project; no 409 Conflict errors during concurrent spawning
- Rendered PumplAI SOUL.md semantically identical to v1.0 hardcoded file (golden baseline diff empty)
- Non-main-branch project generates non-empty diff referencing the correct branch
- `openclaw project switch` while L3 task executing: task completes in original project's state file

**Research flag:** Pool isolation behavior under concurrent load may benefit from a brief load test setup before marking P2 complete.

---

### Phase Ordering Rationale

- Phase 1 is mandatory first: 5 of 8 pitfalls are Phase 1 blockers; all other phases depend on `project_config.py` CRUD and path resolution; running Phase 2+ without Phase 1 corrupts the live PumplAI system
- Phases 2, 3, and 4 can proceed in parallel once Phase 1 is complete — they have no cross-dependencies
- Phase 3 CLI is a delivery mechanism, not a runtime dependency — it does not need to complete before Phase 2 runtime works (developers can call underlying functions directly)
- Phase 5 is integration verification — intentionally last to catch cross-phase issues with a real second project before shipping

---

### Research Flags

**Needs careful implementation (known complexity, not unknown territory):**
- **Phase 3 — SOUL section-based merge:** Edge cases in malformed or non-standard override files need defensive coding. Spike the merge function against the existing PumplAI SOUL.md before writing the full engine.
- **Phase 2 — `spawn_task()` convenience function:** Catalogue all call sites before removal/refactor. If callers exist outside the known `spawn.py` path (e.g., in Telegram command handlers), Phase 2 scope expands.
- **Phase 1 — State file migration:** Must be idempotent (safe to run twice). Must include a guard against migrating while tasks are in-flight.

**Standard patterns (can skip research-phase during planning):**
- Phase 1 — `project_config.py` CRUD: Direct extension of existing resolver; no novel patterns
- Phase 2 — asyncio.Semaphore per-project dict: Textbook asyncio; matches existing pool.py code style
- Phase 2 — Docker label schema addition: One-line change to existing labels dict
- Phase 4 — Next.js API route + SWR + useSWRMutation: Well-documented; follows exact existing pattern in `route.ts` and `useSwarmState.ts`

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All stdlib; Jinja2 absence verified on host; all frontend packages confirmed in occc package.json |
| Features | HIGH (core), MEDIUM (dashboard switcher specifics) | Core P1 features derive from direct codebase analysis; dashboard switcher implementation details are well-documented Next.js patterns not yet exercised |
| Architecture | HIGH | Based on direct file-by-file analysis of all relevant v1.0 source files; JarvisState path-agnostic property verified by reading constructor |
| Pitfalls | HIGH | Derived from reading the actual broken code paths with line-number-level citations, not hypothetical scenarios |

**Overall confidence: HIGH**

### Gaps to Address

- **SOUL merge edge cases:** Section-based merge is the right approach but merge rules for unexpected override content (new sections, missing markers) need a concrete implementation spike before finalizing. This is a known unknown, not a confidence gap.
- **`spawn_task()` call sites:** All callers of the convenience function in `pool.py` must be catalogued before Phase 2 begins. If callers exist outside the known code path, the refactor scope expands.
- **Migration timing:** The Phase 1 state file migration must be run with no active tasks. The guard check (verify no in-progress tasks before migrating) needs to be part of Phase 1 implementation, not an afterthought.
- **Project template agent IDs:** The `init` command must validate that the L2 agent ID specified during init exists in `openclaw.json:agents.list`. Template `project.json` files need a clear placeholder that triggers this validation — otherwise new projects reference non-existent agents silently.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase: `/home/ollie/.openclaw/orchestration/state_engine.py` — JarvisState path-agnostic constructor verified
- Direct codebase: `/home/ollie/.openclaw/orchestration/project_config.py` — existing resolver functions confirmed
- Direct codebase: `/home/ollie/.openclaw/orchestration/config.py` — `OPENCLAW_STATE_FILE` env var override confirmed
- Direct codebase: `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` — labels dict, container name pattern, pool call confirmed
- Direct codebase: `/home/ollie/.openclaw/skills/spawn_specialist/pool.py` — single global semaphore, `spawn_task()` convenience function confirmed
- Direct codebase: `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/route.ts` — hardcoded state file path, module-level cache singleton confirmed
- Direct codebase: `/home/ollie/.openclaw/workspace/occc/package.json` — swr@2.4.0, zod@4.3.6, next@16.1.6 confirmed
- Python stdlib: `string.Template.safe_substitute()` docs, `argparse.add_subparsers()` docs — verified against Python 3.14 behavior

### Secondary (MEDIUM confidence)
- Pattern: [dbt-switch CLI project switcher](https://github.com/jairus-m/dbt-switch) — noun-verb subcommand structure
- Pattern: [CLI design guidelines](https://clig.dev/) — `--flag > env var > config` priority order
- Pattern: [Multi-tenant Docker container isolation](https://dev.to/reeddev42/per-user-docker-container-isolation-a-pattern-for-multi-tenant-ai-agents-8eb) — per-project label filtering
- Pattern: [Tenant Data Isolation anti-patterns](https://propelius.ai/blogs/tenant-data-isolation-patterns-and-anti-patterns) — shared state file pitfalls

### Tertiary (LOW confidence — general patterns, not project-specific)
- [fcntl advisory locking pitfalls](https://en.wikipedia.org/wiki/File_locking) — cross-process lock contention at scale
- [Gemini CLI issue #4935](https://github.com/google-gemini/gemini-cli/issues/4935) — workspace switching patterns in AI CLI tools

---
*Research completed: 2026-02-23*
*Ready for roadmap: yes*
