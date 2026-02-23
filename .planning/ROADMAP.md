# Roadmap: OpenClaw (Grand Architect Protocol)

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- 🚧 **v1.1 Project Agnostic** — Phases 11-17 (in progress)

## Phases

<details>
<summary>✅ v1.0 Grand Architect Protocol Foundation (Phases 1-10) — SHIPPED 2026-02-23</summary>

- [x] Phase 1: Environment Substrate (2/2 plans) — completed 2026-02-17
- [x] Phase 2: Core Orchestration (2/2 plans) — completed 2026-02-17
- [x] Phase 3: Specialist Execution (4/4 plans) — completed 2026-02-18
- [x] Phase 4: Monitoring Uplink (4/4 plans) — completed 2026-02-18
- [x] Phase 5: Wiring Fixes & Initialization (3/3 plans) — completed 2026-02-23
- [x] Phase 6: Phase 3 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 7: Phase 4 Formal Verification (2/3 plans, 1 skipped) — completed 2026-02-23
- [x] Phase 8: Final Gap Closure (1/1 plan) — completed 2026-02-23
- [x] Phase 9: Integration Wiring Cleanup (2/2 plans) — completed 2026-02-23
- [x] Phase 10: Housekeeping & Documentation (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.1 Project Agnostic (In Progress)

**Milestone Goal:** Transform OpenClaw from a PumplAI-specific tool into a general-purpose AI swarm framework that manages N projects simultaneously with per-project configuration, isolation, and CLI tooling.

- [ ] **Phase 11: Config Decoupling Foundation** - Decouple all state/snapshot paths from hardcoded single-project constants; establish per-project path resolution as the canonical pattern
- [ ] **Phase 12: SOUL Templating** - Default SOUL template with substitution points and per-project override mechanism; renders coherent L2 agent identity at project init time
- [x] **Phase 13: Multi-Project Runtime** - Wire per-project context through spawn, pool, and monitor; project-labeled containers with namespaced naming and env injection (completed 2026-02-23)
- [ ] **Phase 14: Project CLI** - `openclaw project init/list/switch/remove` subcommand group with template scaffolding for fullstack, backend, and ml-pipeline stacks
- [ ] **Phase 15: Dashboard Project Switcher** - Project selector in occc header; all API routes and SSE stream accept project scope; task/metrics views filter by selected project

## Phase Details

### Phase 11: Config Decoupling Foundation
**Goal**: Per-project state file and snapshot paths resolve correctly from project_config; the live PumplAI system is migrated without data loss; all downstream components have stable path APIs to consume
**Depends on**: Phase 10 (v1.0 complete)
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-06, CFG-07
**Success Criteria** (what must be TRUE):
  1. Two different project IDs passed to `get_state_path()` return two distinct, non-overlapping file paths on disk
  2. `get_snapshot_dir()` returns a project-scoped directory path; snapshots written by the PumplAI project land under its own subdirectory without touching other project directories
  3. `snapshot.py` generates a non-empty diff for a repository whose default branch is not `main` (dynamic branch detection working)
  4. Agent config.json hierarchy references load from the project manifest rather than hardcoded strings — verified by pointing a test project at a custom agent ID and confirming it resolves
  5. The existing `workspace/.openclaw/workspace-state.json` is migrated to the new path convention with no task data lost and a guard preventing migration while tasks are in-flight
**Plans:** 3 plans
Plans:
- [ ] 11-01-PLAN.md — Path API foundation (get_state_path, get_snapshot_dir, _detect_default_branch)
- [ ] 11-02-PLAN.md — Update all hardcoded call sites across orchestration and spawn layers
- [ ] 11-03-PLAN.md — Migration CLI script for PumplAI state file cutover

### Phase 12: SOUL Templating
**Goal**: New projects get a coherent L2 agent identity from a default template at init time; existing PumplAI SOUL.md is reproducible from template + override with semantically identical output to the v1.0 hardcoded file
**Depends on**: Phase 11
**Requirements**: CFG-04, CFG-05
**Success Criteria** (what must be TRUE):
  1. Running the SOUL renderer against the PumplAI project produces a file that diffs empty against the v1.0 hardcoded `agents/pumplai_pm/agent/SOUL.md` (golden baseline passes)
  2. A new project created without a soul-override.md receives a SOUL.md rendered entirely from the default template with `$project_name` and `$tech_stack_*` substitution points filled correctly
  3. A project that supplies a `projects/<id>/soul-override.md` gets a merged SOUL.md where the override sections replace their corresponding default sections without corrupting the rest of the file
**Plans:** 2 plans
Plans:
- [ ] 12-01-PLAN.md — Core renderer module, default template, and PumplAI override
- [ ] 12-02-PLAN.md — CLI entry point and golden baseline verification script

### Phase 13: Multi-Project Runtime
**Goal**: L3 containers carry their project identity as a Docker label and env var; container names are namespaced per project preventing name collisions; the pool and monitor operate correctly in a multi-project environment
**Depends on**: Phase 11
**Requirements**: MPR-01, MPR-02, MPR-03, MPR-04, MPR-05, MPR-06
**Success Criteria** (what must be TRUE):
  1. `docker ps` output for two concurrently active projects shows container names prefixed with their respective project IDs — no name collision errors occur when both spawn L3 tasks simultaneously
  2. `docker inspect <container>` shows `openclaw.project` label set to the correct project ID for every L3 container
  3. `monitor.py --project pumplai` displays only PumplAI tasks; `monitor.py --project <other>` displays only that project's tasks — no cross-project bleed in output
  4. Changing `active_project` in `openclaw.json` mid-execution does not redirect an in-flight L3 task to the wrong state file — the task completes in the project's state file it was spawned under
**Plans:** 2/2 plans complete
Plans:
- [ ] 13-01-PLAN.md — Container identity threading (spawn, pool, entrypoint)
- [ ] 13-02-PLAN.md — Multi-project monitoring and verification

### Phase 14: Project CLI
**Goal**: Users can create, list, switch between, and remove projects using `openclaw project` subcommands without manually editing JSON files; template presets pre-populate sensible defaults for common stack types
**Depends on**: Phase 11, Phase 12
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, CLI-06
**Success Criteria** (what must be TRUE):
  1. `openclaw project init --id myproject --name "My Project"` creates a `projects/myproject/project.json` with correct defaults and a rendered SOUL.md — the project appears in subsequent `list` output
  2. `openclaw project list` displays all projects in a table showing ID, name, workspace path, and which project is currently active
  3. `openclaw project switch <id>` updates `active_project` in `openclaw.json`; running `list` immediately after confirms the active marker moved; attempting to switch while L3 tasks are in-flight prints a warning and aborts
  4. `openclaw project remove <id>` deletes the project directory; attempting to remove the currently active project prints an error and exits without deleting anything
  5. `openclaw project init --template fullstack` scaffolds a project.json pre-populated with fullstack defaults; `--template backend` and `--template ml-pipeline` produce their respective presets from `projects/_templates/`
**Plans**: TBD

### Phase 15: Dashboard Project Switcher
**Goal**: The occc dashboard is usable with multiple projects; users can switch the active project from the UI; all data panels (tasks, agents, metrics) reflect only the selected project's state
**Depends on**: Phase 11, Phase 13
**Requirements**: DSH-05, DSH-06, DSH-07, DSH-08
**Success Criteria** (what must be TRUE):
  1. A project selector dropdown appears in the occc header showing all available projects; selecting a different project updates the active view without a full page reload
  2. `GET /api/swarm?project=pumplai` returns only PumplAI state; `GET /api/swarm?project=<other>` returns only that project's state — the two responses contain distinct task lists
  3. The SSE stream at `/api/swarm/stream?project=<id>` emits only events for the specified project; switching projects in the UI reconnects to the correct stream within one SSE cycle
  4. The task list, agent hierarchy panel, and metrics widgets all display data filtered to the selected project — no cross-project task bleed visible in any panel
**Plans**: TBD

### Phase 16: Phase 11/12 Integration Fixes
**Goal**: Fix the 3 cross-phase wiring issues identified by the v1.1 milestone audit — snapshot project_id threading, soul template variable consumption, and staging branch detection — plus remove deprecated constants
**Depends on**: Phase 11, Phase 12
**Requirements**: CFG-02, CFG-04, CFG-06
**Gap Closure:** Closes integration and flow gaps from v1.1-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. `get_snapshot_dir()` callers pass explicit `project_id` — no ambient config resolution
  2. `soul-default.md` template body contains and renders `$project_name` correctly
  3. `create_staging_branch()` delegates to `_detect_default_branch()` instead of duplicate inline detection
  4. Deprecated `STATE_FILE` and `SNAPSHOT_DIR` constants removed from `config.py`; `monitor.py` no longer imports them
**Plans:** 2/2 plans complete
Plans:
- [ ] 16-01-PLAN.md — Fix snapshot project_id threading, branch detection delegation, soul template variable, deprecated constant removal
- [x] 16-02-PLAN.md — Phase 16 verification script (completed 2026-02-23)

### Phase 17: Phase 11/12 Formal Verification
**Goal**: Create VERIFICATION.md for Phases 11 and 12 with evidence-based checks confirming all 7 CFG requirements are satisfied after integration fixes
**Depends on**: Phase 16
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04, CFG-05, CFG-06, CFG-07
**Gap Closure:** Closes verification gaps from v1.1-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. `phases/11-config-decoupling-foundation/VERIFICATION.md` exists with pass/fail evidence for CFG-01, CFG-02, CFG-03, CFG-06, CFG-07
  2. `phases/12-soul-templating/VERIFICATION.md` exists with pass/fail evidence for CFG-04, CFG-05
  3. All 7 CFG requirements have concrete code evidence (file:line references) confirming satisfaction
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Environment Substrate | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 2. Core Orchestration | v1.0 | 2/2 | ✓ Complete | 2026-02-17 |
| 3. Specialist Execution | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 4. Monitoring Uplink | v1.0 | 4/4 | ✓ Complete | 2026-02-18 |
| 5. Wiring Fixes | v1.0 | 3/3 | ✓ Complete | 2026-02-23 |
| 6. Phase 3 Verification | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 7. Phase 4 Verification | v1.0 | 2/3 | ✓ Complete | 2026-02-23 |
| 8. Final Gap Closure | v1.0 | 1/1 | ✓ Complete | 2026-02-23 |
| 9. Integration Wiring | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 10. Housekeeping & Docs | v1.0 | 2/2 | ✓ Complete | 2026-02-23 |
| 11. Config Decoupling Foundation | v1.1 | 0/3 | Planned | - |
| 12. SOUL Templating | v1.1 | 0/2 | Planned | - |
| 13. Multi-Project Runtime | 2/2 | Complete    | 2026-02-23 | - |
| 14. Project CLI | v1.1 | 0/TBD | Not started | - |
| 15. Dashboard Project Switcher | v1.1 | 0/TBD | Not started | - |
| 16. Phase 11/12 Integration Fixes | 2/2 | Complete    | 2026-02-23 | - |
| 17. Phase 11/12 Formal Verification | v1.1 | 0/TBD | Not started | - |
