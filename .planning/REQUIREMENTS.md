# Requirements: OpenClaw

**Defined:** 2026-02-23
**Core Value:** Hierarchical AI orchestration with physical isolation — enabling autonomous, secure, multi-agent task execution at scale.

## v1.1 Requirements

Requirements for milestone v1.1 Project Agnostic. Each maps to roadmap phases.

### Config Decoupling

- [ ] **CFG-01**: Per-project state file at `workspace/.openclaw/<project_id>/workspace-state.json`
- [ ] **CFG-02**: Per-project snapshot directory at `workspace/.openclaw/<project_id>/snapshots/`
- [ ] **CFG-03**: `project_config.py` exposes `get_state_path(project_id)` and `get_snapshot_dir(project_id)`
- [ ] **CFG-04**: SOUL.md default template with `$project_name` and `$tech_stack_*` substitution points
- [ ] **CFG-05**: Projects can override SOUL.md with a custom file in `projects/<id>/SOUL.md`
- [ ] **CFG-06**: `snapshot.py` detects default branch dynamically instead of hardcoding `"main"`
- [ ] **CFG-07**: Agent `config.json` hierarchy references resolve from project config, not hardcoded strings

### Multi-Project Runtime

- [ ] **MPR-01**: `spawn.py` adds `openclaw.project` label to all L3 containers
- [ ] **MPR-02**: Container names prefixed with project ID: `openclaw-<project>-l3-<task_id>`
- [ ] **MPR-03**: `pool.py` resolves state file path per-project via `get_state_path()`
- [ ] **MPR-04**: `monitor.py` accepts `--project` flag to filter output by project
- [ ] **MPR-05**: `spawn.py` injects `OPENCLAW_PROJECT` env var into L3 containers
- [ ] **MPR-06**: `active_project` resolution is env-var-first to prevent mid-execution mutation

### Project CLI

- [ ] **CLI-01**: `openclaw project init` creates `projects/<id>/project.json` from prompts or flags
- [ ] **CLI-02**: `openclaw project list` shows all projects with ID, name, workspace, active marker
- [ ] **CLI-03**: `openclaw project switch <id>` updates `active_project` in `openclaw.json`
- [ ] **CLI-04**: `openclaw project remove <id>` deletes project directory with guard against removing active project
- [ ] **CLI-05**: `openclaw project init --template fullstack|backend|ml-pipeline` scaffolds from preset templates
- [ ] **CLI-06**: Template presets stored in `projects/_templates/` with sensible defaults per stack type

### Dashboard

- [ ] **DSH-05**: Project selector dropdown in occc header showing all available projects
- [ ] **DSH-06**: `/api/swarm` route accepts `?project=<id>` and returns project-scoped state
- [ ] **DSH-07**: SSE stream route `/api/swarm/stream` accepts `?project=<id>` and streams project-scoped events
- [ ] **DSH-08**: Task list, agent hierarchy, and metrics filter by selected project

## v1.2 Requirements

Deferred to next milestone. Tracked but not in current roadmap.

### Pool Isolation

- **POOL-01**: `project.json` supports `l3_pool: "shared"|"isolated"` field
- **POOL-02**: Isolated projects get their own `L3ContainerPool` instance with separate semaphore
- **POOL-03**: Pool registry at orchestration level manages per-project pool lifecycle

### Dashboard Enhancements

- **DSH-09**: Per-project agent hierarchy filtering in left panel
- **DSH-10**: Project usage metrics (container time, task counts per project)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-host swarm | Single-host only — v2.0 consideration |
| Persistent L3 agents | Ephemeral containers by design |
| LLM-generated SOULs at init time | Non-determinism in CLI init operations |
| Per-project Docker networks | No inter-container networking needed; volume mount isolation sufficient |
| CWD-based project auto-detection | Conflicts with scripts calling openclaw from arbitrary directories |
| Cross-project agent sharing | Conflicts with current 1:1 L2-to-project assumption |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CFG-01 | — | Pending |
| CFG-02 | — | Pending |
| CFG-03 | — | Pending |
| CFG-04 | — | Pending |
| CFG-05 | — | Pending |
| CFG-06 | — | Pending |
| CFG-07 | — | Pending |
| MPR-01 | — | Pending |
| MPR-02 | — | Pending |
| MPR-03 | — | Pending |
| MPR-04 | — | Pending |
| MPR-05 | — | Pending |
| MPR-06 | — | Pending |
| CLI-01 | — | Pending |
| CLI-02 | — | Pending |
| CLI-03 | — | Pending |
| CLI-04 | — | Pending |
| CLI-05 | — | Pending |
| CLI-06 | — | Pending |
| DSH-05 | — | Pending |
| DSH-06 | — | Pending |
| DSH-07 | — | Pending |
| DSH-08 | — | Pending |

**Coverage:**
- v1.1 requirements: 23 total
- Mapped to phases: 0
- Unmapped: 23

---
*Requirements defined: 2026-02-23*
*Last updated: 2026-02-23 after initial definition*
