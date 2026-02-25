# Roadmap: OpenClaw (Grand Architect Protocol)

## Milestones

- ✅ **v1.0 Grand Architect Protocol Foundation** — Phases 1-10 (shipped 2026-02-23)
- ✅ **v1.1 Project Agnostic** — Phases 11-18 (shipped 2026-02-23)
- ✅ **v1.2 Orchestration Hardening** — Phases 19-25 (shipped 2026-02-24)
- ✅ **v1.3 Agent Memory** — Phases 26-38 (shipped 2026-02-24)
- ✅ **v1.4 Operational Maturity** — Phases 39-44 (shipped 2026-02-25)
- 🚧 **v1.5 Config Consolidation** — Phases 45-49 (in progress)
- 🚧 **v2.0 Notion Kanban Sync** — Phase 50 (planned)

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

<details>
<summary>✅ v1.1 Project Agnostic (Phases 11-18) — SHIPPED 2026-02-23</summary>

- [x] Phase 11: Config Decoupling Foundation (3/3 plans) — completed 2026-02-23
- [x] Phase 12: SOUL Templating (2/2 plans) — completed 2026-02-23
- [x] Phase 13: Multi-Project Runtime (2/2 plans) — completed 2026-02-23
- [x] Phase 14: Project CLI (2/2 plans) — completed 2026-02-23
- [x] Phase 15: Dashboard Project Switcher (2/2 plans) — completed 2026-02-23
- [x] Phase 16: Phase 11/12 Integration Fixes (2/2 plans) — completed 2026-02-23
- [x] Phase 17: Phase 11/12 Formal Verification (2/2 plans) — completed 2026-02-23
- [x] Phase 18: Integration Hardening (2/2 plans) — completed 2026-02-23

See: `.planning/milestones/v1.1-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.2 Orchestration Hardening (Phases 19-25) — SHIPPED 2026-02-24</summary>

- [x] Phase 19: Structured Logging (2/2 plans) — completed 2026-02-24
- [x] Phase 20: Reliability Hardening (2/2 plans) — completed 2026-02-24
- [x] Phase 21: State Engine Performance (3/3 plans) — completed 2026-02-24
- [x] Phase 22: Observability Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 23: Per-Project Pool Config (2/2 plans) — completed 2026-02-24
- [x] Phase 24: Dashboard Metrics (2/2 plans) — completed 2026-02-24
- [x] Phase 25: Monitor Cache Fix (1/1 plan) — completed 2026-02-24

See: `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.3 Agent Memory (Phases 26-38) — SHIPPED 2026-02-24</summary>

- [x] Phase 26: memU Infrastructure (2/2 plans) — completed 2026-02-24
- [x] Phase 27: Memory Client + Scoping (1/1 plan) — completed 2026-02-24
- [x] Phase 28: L3 Auto-Memorization (2/2 plans) — completed 2026-02-24
- [x] Phase 29: Pre-Spawn Retrieval + SOUL Injection (2/2 plans) — completed 2026-02-24
- [x] Phase 30: L2 Review Decision Memorization (2/2 plans) — completed 2026-02-24
- [x] Phase 33: Integration Gap Closure (2/2 plans) — completed 2026-02-24
- [x] Phase 34: Review Decision Category Fix (1/1 plan) — completed 2026-02-24
- [x] Phase 35: L3 In-Execution Memory Queries (1/1 plan) — completed 2026-02-24
- [x] Phase 36: Dashboard Memory Panel (3/3 plans) — completed 2026-02-24
- [x] Phase 37: Category Field E2E Fix (2/2 plans) — completed 2026-02-24
- [x] Phase 38: Phase 28 Verification + Cleanup (1/1 plan) — completed 2026-02-24

Phases 31 and 32 were superseded by Phases 35 and 36 respectively.

See: `.planning/milestones/v1.3-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.4 Operational Maturity (Phases 39-44) — SHIPPED 2026-02-25</summary>

- [x] Phase 39: Graceful Sentinel (4/4 plans) — completed 2026-02-24
- [x] Phase 40: Memory Health Monitor (4/4 plans) — completed 2026-02-24
- [x] Phase 41: L1 Strategic Suggestions (3/3 plans) — completed 2026-02-24
- [x] Phase 42: Delta Snapshots (3/3 plans) — completed 2026-02-24
- [x] Phase 43: v1.4 Gap Closure (1/1 plan) — completed 2026-02-25
- [x] Phase 44: v1.4 Tech Debt Cleanup (1/1 plan) — completed 2026-02-25

See: `.planning/milestones/v1.4-ROADMAP.md` for full phase details.

</details>

### v1.5 Config Consolidation (In Progress)

**Milestone Goal:** Unify the config layer — single source of truth for paths, strict schema validation, consolidated constants, and migration tooling — plus three deferred reliability/quality/observability items.

- [x] **Phase 45: Path Resolver + Constants Foundation** - Eliminate the workspace path divergence and consolidate all magic values into config.py (completed 2026-02-25)
- [x] **Phase 46: Schema Validation + Fail-Fast Startup** - Add a documented openclaw.json schema and enforce it at process startup (completed 2026-02-25)
- [x] **Phase 47: Env Var Precedence + Migration CLI** - Document and enforce env var resolution order; give operators a migration command to upgrade existing configs (completed 2026-02-25)
- [ ] **Phase 48: Config Integration Tests** - Test suite verifying path resolution, validation, env precedence, and pool config fallback runs clean under pytest
- [ ] **Phase 49: Deferred Reliability, Quality, and Observability** - Docker health checks for L3 containers, calibrated cosine similarity threshold, and adaptive monitor polling

## Phase Details

### Phase 45: Path Resolver + Constants Foundation
**Goal**: All components resolve workspace state paths through one authoritative function, and all shared constants/defaults live in a single location with no duplicated magic values
**Depends on**: Phase 44 (v1.4 complete)
**Requirements**: CONF-01, CONF-05
**Success Criteria** (what must be TRUE):
  1. Operator can call `get_state_path()` and `get_snapshot_dir()` and the returned paths match where L3 containers actually write — no divergence between runtime and code-resolved paths
  2. `grep`-ing the codebase for pool defaults, lock timeouts, cache TTL, log levels, and memory budget cap returns only `config.py` as the source — no duplicated literals across modules
  3. All call sites (state_engine, spawn, pool, monitor, snapshot) import constants from `config.py` rather than defining their own
**Plans:** 2/2 plans complete

Plans:
- [ ] 45-01-PLAN.md — Add path resolver functions + consolidated constants to config.py
- [ ] 45-02-PLAN.md — Migrate all call sites to import from config.py, remove duplicates

### Phase 46: Schema Validation + Fail-Fast Startup
**Goal**: `openclaw.json` has a documented, machine-validated schema, and OpenClaw refuses to start with a clear actionable error if either config file is malformed or missing required fields
**Depends on**: Phase 45
**Requirements**: CONF-02, CONF-06
**Success Criteria** (what must be TRUE):
  1. Adding an unknown field to `openclaw.json` causes startup to print a specific warning identifying the unknown field by name
  2. Removing a required field from `openclaw.json` or `project.json` causes the process to exit before doing any work, with an error message naming the missing field and the config file
  3. The schema for `openclaw.json`'s OpenClaw runtime section is written down in a human-readable form that operators can consult
  4. Existing valid configs continue to load without error after the validation change
**Plans:** 3/3 plans complete

Plans:
- [ ] 46-01-PLAN.md — Write failing schema validation test suite (TDD RED state)
- [ ] 46-02-PLAN.md — Implement OPENCLAW_JSON_SCHEMA + validators + wiring into load paths
- [ ] 46-03-PLAN.md — Add openclaw-config show CLI and openclaw.json.example schema doc

### Phase 47: Env Var Precedence + Migration CLI
**Goal**: Operators know exactly which env vars override which config values and in what order, enforced uniformly across all callers; operators can run one command to upgrade an existing config to the current schema
**Depends on**: Phase 46
**Requirements**: CONF-03, CONF-04
**Success Criteria** (what must be TRUE):
  1. Setting `OPENCLAW_ROOT`, `OPENCLAW_PROJECT`, `OPENCLAW_LOG_LEVEL`, or `OPENCLAW_ACTIVITY_LOG_MAX` consistently overrides the corresponding config value in every component that reads it — no component ignores the env var while another respects it
  2. Running `openclaw config migrate --dry-run` on an older config file prints a human-readable diff of what would change without modifying the file
  3. Running `openclaw config migrate` on an older config file produces a valid config that passes Phase 46's schema validation
  4. The resolution order (`OPENCLAW_ROOT` → `OPENCLAW_PROJECT` → `OPENCLAW_LOG_LEVEL` → `OPENCLAW_ACTIVITY_LOG_MAX`) is documented in the config file itself via comments or an adjacent README
**Plans:** 3/3 plans complete

Plans:
- [ ] 47-01-PLAN.md — Env var uniformity: get_active_project_env() in config.py, _find_project_root() auto-create, precedence comment block, openclaw.json.example + cli/config.py epilog
- [ ] 47-02-PLAN.md — Migration CLI: cmd_migrate() + migrate subparser in cli/config.py (dry-run, backup, unknown-field removal, project.json scope)
- [ ] 47-03-PLAN.md — Tests: extend test_config_validator.py with CONF-03 and CONF-04 test cases

### Phase 48: Config Integration Tests
**Goal**: An automated test suite verifies path resolution, schema validation, env var precedence, and pool config fallback — giving the operator confidence the config layer is correct and will stay correct
**Depends on**: Phase 47
**Requirements**: CONF-07
**Success Criteria** (what must be TRUE):
  1. Running `uv run pytest` includes config integration tests and they all pass on a clean checkout
  2. Tests cover path resolution (state path and snapshot dir match expected locations under different OPENCLAW_ROOT values)
  3. Tests cover fail-fast validation (invalid and missing-field configs trigger the expected errors)
  4. Tests cover env var precedence (env var values override config file values for all four variables)
  5. Tests cover pool config fallback (missing pool config in project.json falls back to defaults from config.py)
**Plans**: TBD

### Phase 49: Deferred Reliability, Quality, and Observability
**Goal**: Three items deferred from earlier milestones are delivered — L3 containers report health status, the cosine similarity conflict threshold is evidence-based and configurable, and the monitor adapts its poll rate to swarm activity
**Depends on**: Phase 45
**Requirements**: REL-09, QUAL-07, OBS-05
**Success Criteria** (what must be TRUE):
  1. Running `docker ps` shows `healthy`, `unhealthy`, or `starting` health status for L3 containers rather than no health information
  2. The cosine similarity threshold for conflict detection is set in `openclaw.json` (not hardcoded) and defaults to a value chosen based on observed data — the rationale for the chosen value is noted in a comment or decision log
  3. The monitor poll interval shortens when L3 tasks are actively running and lengthens when the swarm is idle — CPU usage during quiet periods is measurably lower than with a fixed interval
**Plans**: TBD

### v2.0 Notion Kanban Sync (Planned)

**Milestone Goal:** A reactive L2-level skill that maintains a Notion kanban board as a read-only visibility mirror of OpenClaw state, covering both dev projects and life areas — with event bus infrastructure, Notion DB bootstrap, event sync, conversational capture, reconciliation, and hardening.

- [ ] **Phase 50: Notion Kanban Sync** — Full end-to-end delivery: event bus, Notion client, schema bootstrap, event sync, conversational capture, reconcile, and hardening

## Phase Details

### Phase 50: Notion Kanban Sync
**Goal**: OpenClaw events (phase lifecycle, container lifecycle, project registration) automatically mirror to a Notion kanban board; conversational capture routes life tasks to the same board; reconcile detects and corrects drift — all idempotent, field-ownership-respecting, and observable
**Depends on**: None (independent of v1.5)
**Requirements**: NOTION-01, NOTION-02, NOTION-03, NOTION-04, NOTION-05, NOTION-06, NOTION-07, NOTION-08, NOTION-09, NOTION-10, NOTION-11
**Success Criteria** (what must be TRUE):
  1. Phase lifecycle events (started/completed/blocked) create/update Notion cards with correct status transitions
  2. Replay of the same event produces no duplicates (idempotent via dedupe keys)
  3. New project registration creates Projects DB row + triage card
  4. Conversational capture creates cards with correct area inference and dedupe
  5. Container events append to activity log without spamming new cards (meaningful rule enforced)
  6. Unlinked cards have Notion-owned Status — OpenClaw never overwrites
  7. Reconcile detects drift, applies only allowed corrections, never deletes
  8. DB discovery works on first run; cached IDs used on subsequent runs
  9. Field ownership respected — every write checks ownership before touching a field
  10. Structured result returned for every invocation with created/updated/skipped/errors
  11. 429/5xx errors handled with retry + backoff; failures recorded in Sync Error
**Plans**: 6 plans

Plans:
- [ ] 50-01-PLAN.md — Event bus infrastructure + hook sites in state_engine, pool, project_cli
- [ ] 50-02-PLAN.md — Skill skeleton + Notion client wrapper + bootstrap/discovery
- [ ] 50-03-PLAN.md — Event sync handlers for project + phase lifecycle events
- [ ] 50-04-PLAN.md — Container event handlers + field ownership carve-out
- [ ] 50-05-PLAN.md — Conversational capture with area inference + batch parsing
- [ ] 50-06-PLAN.md — Reconcile handler + unit tests for event bus and sync logic

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-10 | v1.0 | 25/25 | ✓ Complete | 2026-02-23 |
| 11-18 | v1.1 | 17/17 | ✓ Complete | 2026-02-23 |
| 19-25 | v1.2 | 14/14 | ✓ Complete | 2026-02-24 |
| 26-38 | v1.3 | 19/19 | ✓ Complete | 2026-02-24 |
| 39-44 | v1.4 | 16/16 | ✓ Complete | 2026-02-25 |
| 45. Path Resolver + Constants Foundation | 2/2 | Complete    | 2026-02-25 | - |
| 46. Schema Validation + Fail-Fast Startup | 3/3 | Complete    | 2026-02-25 | - |
| 47. Env Var Precedence + Migration CLI | 3/3 | Complete    | 2026-02-25 | - |
| 48. Config Integration Tests | v1.5 | 0/? | Not started | - |
| 49. Deferred Reliability, Quality, and Observability | v1.5 | 0/? | Not started | - |
| 50. Notion Kanban Sync | 5/6 | In Progress|  | - |
