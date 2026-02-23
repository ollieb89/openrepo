# Feature Research

**Domain:** Multi-project AI Swarm Orchestration Framework
**Researched:** 2026-02-23
**Confidence:** HIGH (core patterns), MEDIUM (dashboard switcher specifics)

---

## Context: What Already Exists

v1.0 shipped a fully operational system with a single project hardcoded (pumplai).
A quick-win project context layer already landed pre-v1.1:

- `projects/pumplai/project.json` manifest (workspace, tech_stack, agents, l3_overrides)
- `orchestration/project_config.py` resolver (get_workspace_path, get_tech_stack, get_agent_mapping)
- `openclaw.json` `active_project` field
- `spawn.py` and `pool.py` already read from project config

The v1.1 milestone adds: project CLI subcommands, SOUL templating, per-project state isolation,
configurable pool isolation, and a dashboard project switcher.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that a multi-project framework must have. Missing these = tool feels prototype-grade.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `openclaw project init` command | Standard pattern: every multi-project tool (dbt, terraform workspace, kubectl config) has an init/create flow. Without it, users must manually create JSON files. | LOW | Writes `projects/<id>/project.json` from prompted inputs. Updates `openclaw.json` `active_project`. |
| `openclaw project list` command | Users need to see what projects exist at a glance. Table output with ID, name, workspace path, active marker. | LOW | Reads `projects/*/project.json`. Marks the active one. |
| `openclaw project switch <id>` command | Changing the active project is the core UX. Must be fast (no Docker ops). | LOW | Writes `active_project` in `openclaw.json`. Validates the project exists. |
| `openclaw project remove <id>` command | Cleanup. Users expect CRUD to be complete. | LOW | Removes `projects/<id>/`. Guards against removing the active project. |
| Per-project state isolation | State from Project A must not contaminate Project B's task log. Each project gets its own `workspace-state.json`. | MEDIUM | Already partially true via env var overrides. Needs per-project path convention: `workspace/.openclaw/<project_id>/workspace-state.json` or equivalent. |
| SOUL.md template system | Every new L2 agent created for a project must start from a coherent base prompt, not be written from scratch. Without templates, multi-project onboarding is high-friction. | MEDIUM | Jinja2-style `{{ project.name }}`, `{{ project.tech_stack.frontend }}` substitution into a base SOUL template. Produces a rendered SOUL.md per project. |
| Project-labeled Docker containers | When multiple projects have active L3 containers, the dashboard and CLI need to distinguish which container belongs to which project. | LOW | Add `openclaw.project` Docker label to containers spawned by a given project. Already done for `openclaw.managed`, `openclaw.task_id`. |
| Dashboard project filter | The occc dashboard currently shows all tasks from all agents in a single unified view. With N projects, users need to filter to the project they care about. | MEDIUM | Project selector component in the header or left panel. Filters task list, agent hierarchy, and metrics by `project_id`. |

### Differentiators (Competitive Advantage)

Features that go beyond "works" to "feels intentional."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Project templates (`--template fullstack\|backend\|ml-pipeline`) | Init not just a blank project.json, but a pre-wired config for a known stack type. Saves ~10 minutes of config wrangling per project. | MEDIUM | Three template presets with sensible l3_overrides (ML gets GPU quota, fullstack gets higher mem). Stored as `projects/_templates/`. |
| Convention-over-configuration SOUL rendering | Instead of requiring users to understand Jinja2, the template variables are documented and predictable. `{{ project.name }}` always works. No surprise undefined errors. | LOW | Implement strict template variable whitelist. Raise clear errors for unknown substitution keys. |
| Configurable pool isolation (shared default, isolated opt-in) | By default all projects share the 3-container pool. Opt-in per-project isolation means Project A's ML workload cannot starve Project B. | HIGH | `l3_pool` field in `project.json`: `"shared"` (default) or `"isolated"`. Isolated projects get their own `L3ContainerPool` instance with their own semaphore. The pool registry must be managed at the orchestration level, not per-spawn call. |
| Dashboard project switcher with live state | The project selector in the dashboard doesn't just filter locally — it triggers a state re-fetch scoped to the new project's state file. Real-time SSE stays connected per project. | MEDIUM | Requires dashboard API routes to accept `?project=<id>` query param. SSE stream route also needs project scoping. |
| Agent hierarchy shown per-project | The left panel of occc currently shows all agents from `openclaw.json`. With multi-project, only the agents relevant to the selected project should appear in hierarchy context. | LOW | Filter `openclaw.json` `agents.list` by `reports_to` chain relevant to the project's `l2_pm` agent. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Global shared workspace-state.json for all projects | Simpler conceptually — one file, one truth. | Concurrent projects writing to the same file under fcntl.flock means lock contention. A slow ML task writing state blocks a frontend task's state update. Also, project A's task history clutters project B's view. | Per-project state files at `workspace/.openclaw/<project_id>/workspace-state.json`. Each project has its own Jarvis instance with its own lock. |
| Fully dynamic SOUL generation via LLM at init time | Seems powerful — let an LLM craft the perfect SOUL for each new project. | Introduces a network dependency and non-determinism into a CLI init operation. `openclaw project init` would sometimes fail or produce garbage. | Template-based substitution with human-readable templates. Users can manually edit the SOUL after init. |
| Kubernetes/Swarm for multi-project pool management | Multi-project orchestration sounds like a job for Kubernetes namespaces. | Massive operational overhead for a single-host system. Requires Docker Swarm mode or K8s cluster. Incompatible with the current Docker SDK approach. | Semaphore-per-project pool isolation within a single Python process. Each project gets its own `L3ContainerPool(max_concurrent=N)` instance. This is the hashicorp-nomad-style "bin packing" approach without the cluster overhead. |
| Per-project Docker networks for isolation | Strong isolation — containers for Project A cannot reach containers for Project B at the network layer. | Current L3 containers don't need inter-container networking. Adding Docker networks per project increases spawn complexity and latency with no functional benefit (L3s are ephemeral, they only write to bind-mounted volumes). | Project isolation via volume mounts (already in place) + Docker labels. Network isolation is not needed for the current threat model. |
| Real-time project auto-detection from CWD | Like `git` detecting the repo from the current directory — `openclaw` reads the active project from the CWD's nearest `project.json`. | CWD detection works for single-project monorepos. For OpenClaw's use case, the active project is managed centrally in `openclaw.json`. CWD-based detection conflicts with scripts that call `openclaw` from arbitrary directories. | Explicit `--project <id>` flag and `active_project` in `openclaw.json`. Env var `OPENCLAW_PROJECT` already supported. |

---

## Feature Dependencies

```
[project init CLI]
    └──writes──> [projects/<id>/project.json]
                     └──requires──> [project list / switch / remove CLI]
                     └──requires──> [SOUL template rendering]
                                        └──produces──> [agents/<l2_id>/agent/SOUL.md]

[per-project state isolation]
    └──requires──> [per-project state file path convention]
                       └──requires──> [project_config.py get_state_path()]
                       └──requires──> [JarvisState per-project instantiation in pool.py]
                       └──requires──> [dashboard API accepts ?project= param]

[configurable pool isolation]
    └──requires──> [project.json l3_pool field]
    └──requires──> [pool registry at orchestration level]
                       └──conflicts──> [current single-global-pool design in pool.py]

[dashboard project switcher]
    └──requires──> [dashboard API ?project= param support]
    └──enhances──> [per-project state isolation]
    └──requires──> [project-labeled Docker containers (openclaw.project label)]

[project templates (--template)]
    └──enhances──> [project init CLI]
    └──depends──> [projects/_templates/ directory with preset project.json files]
```

### Dependency Notes

- **Per-project state isolation requires project_config.py extension**: `get_state_path(project_id)` must be added. Currently `orchestration/config.py` has a static `STATE_FILE` path. This needs to become project-aware.
- **Pool isolation conflicts with current pool.py design**: `L3ContainerPool` is currently instantiated per-call in `spawn_task()`. A pool registry (dict of project_id -> L3ContainerPool) must be introduced so the same pool instance persists across multiple `spawn_task` calls for the same project.
- **Dashboard project switcher depends on state isolation**: The dashboard's `/api/swarm` route currently reads a hardcoded state file path. It must accept `?project=<id>` and resolve the correct state file via project_config.
- **SOUL templating is independent**: It only runs at `project init` time. It does not affect runtime. Low risk.

---

## MVP Definition

### Launch With (v1.1)

Minimum viable multi-project capability — what's needed to use OpenClaw on a second project.

- [x] `openclaw project init` — creates project.json from prompts or flags
- [x] `openclaw project list` — shows all projects with active marker
- [x] `openclaw project switch <id>` — changes active_project in openclaw.json
- [x] `openclaw project remove <id>` — removes project directory with guard
- [x] Per-project state file isolation — `get_state_path(project_id)` in project_config.py, wired into pool.py and dashboard API
- [x] SOUL.md template rendering — base template + Jinja2 substitution at init time
- [x] Project-labeled Docker containers — `openclaw.project` label in spawn.py
- [x] Dashboard project switcher — selector component, ?project= API param, filtered task/agent view

### Add After Validation (v1.x)

- [ ] Project templates (`--template fullstack|backend|ml-pipeline`) — trigger: user creates 3+ projects manually and complains about repetition
- [ ] Configurable pool isolation (`l3_pool: "isolated"`) — trigger: two concurrent projects interfere with each other's L3 concurrency budget
- [ ] Agent hierarchy filtered per-project in dashboard — trigger: `openclaw.json` grows to 10+ agents and the hierarchy panel becomes unreadable

### Future Consideration (v2+)

- [ ] Project archiving (pause without deletion) — defer: no user request yet
- [ ] Cross-project agent sharing (L2 PM serving multiple projects) — defer: conflicts with current 1:1 L2-to-project assumption
- [ ] Project usage metrics (tokens, container time, cost per project) — defer: requires billing integration not in scope

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `openclaw project init/list/switch/remove` | HIGH — without CLI, multi-project requires manual JSON editing | LOW — Python Click subcommand group, ~150 LOC | P1 |
| Per-project state file isolation | HIGH — prevents task log contamination between projects | MEDIUM — extend project_config.py + update 3 callers | P1 |
| SOUL.md template rendering | HIGH — new project without a SOUL is broken at L2 agent init | MEDIUM — Jinja2 rendering, template design, ~100 LOC | P1 |
| Project-labeled Docker containers | MEDIUM — needed for dashboard filtering | LOW — one additional label in spawn.py, ~5 LOC | P1 |
| Dashboard project switcher | HIGH — without it, dashboard becomes unusable with 2+ projects | MEDIUM — new selector component, API param plumbing, ~200 LOC | P1 |
| Project init templates (`--template`) | MEDIUM — saves config time per project | MEDIUM — 3 preset project.json files + CLI flag | P2 |
| Configurable pool isolation | MEDIUM — only matters when 2 projects compete for L3 slots simultaneously | HIGH — pool registry, new project.json field, pool lifecycle management | P2 |
| Per-project agent hierarchy in dashboard | LOW — cosmetic improvement | LOW — filter existing agent list by project mapping | P3 |

**Priority key:**
- P1: Must have for v1.1 launch — enables multi-project at all
- P2: Should have, add when P1 is stable and tested
- P3: Nice to have, schedule for v1.2

---

## User Workflows (Concrete)

### Workflow 1: Adding a Second Project

```bash
openclaw project init \
  --id myapp \
  --name "MyApp" \
  --workspace /home/user/projects/myapp \
  --template fullstack

# Creates:
#   projects/myapp/project.json
#   agents/myapp_pm/agent/SOUL.md  (rendered from template)
# Sets active_project: "myapp" in openclaw.json
```

### Workflow 2: Switching Between Projects

```bash
openclaw project list
# ID        NAME        WORKSPACE                      ACTIVE
# pumplai   PumplAI     /home/ollie/Development/...    *
# myapp     MyApp       /home/user/projects/myapp

openclaw project switch myapp
# Updated active project: myapp
```

### Workflow 3: Dashboard Project Context

- User opens occc at http://localhost:6987
- Project selector dropdown in top bar shows "PumplAI" (current active)
- User clicks dropdown, selects "MyApp"
- Dashboard re-fetches `/api/swarm?project=myapp`
- Task list, agent hierarchy, and metrics update to show MyApp's state only
- SSE stream reconnects to `/api/swarm/stream?project=myapp`

### Workflow 4: L3 Spawn Stays Project-Scoped

- L2 PM for MyApp calls `spawn_task()` with project_id="myapp"
- Container spawned with `openclaw.project=myapp` Docker label
- Container writes state to `workspace/.openclaw/myapp/workspace-state.json`
- PumplAI's state file at `workspace/.openclaw/pumplai/workspace-state.json` is untouched

---

## Integration Points with Existing System

| New Feature | Existing Code Touched | Change Type |
|-------------|----------------------|-------------|
| project CLI subcommands | `openclaw.json` (active_project write), new `cli/project.py` | New file + config mutation |
| SOUL templating | `agents/<id>/agent/SOUL.md` generation, new `orchestration/soul_renderer.py` | New file + writes to agents/ |
| Per-project state isolation | `orchestration/project_config.py` (get_state_path), `skills/spawn_specialist/pool.py` (state_file arg), `workspace/occc/src/app/api/swarm/route.ts` (?project param) | Extend existing |
| Configurable pool isolation | `skills/spawn_specialist/pool.py` (pool registry), `projects/*/project.json` (l3_pool field) | Moderate refactor |
| Dashboard project switcher | `workspace/occc/src/app/page.tsx`, new `ProjectSelector` component, `useSwarmState` hook (?project param) | New component + hook change |
| Project-labeled containers | `skills/spawn_specialist/spawn.py` (container labels dict) | 1-line change |

---

## Sources

- Existing codebase: `/home/ollie/.openclaw/projects/pumplai/project.json`
- Existing codebase: `/home/ollie/.openclaw/orchestration/project_config.py`
- Existing codebase: `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py`
- Existing codebase: `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/route.ts`
- Existing codebase: `/home/ollie/.openclaw/workspace/occc/src/hooks/useSwarmState.ts`
- Pattern: [dbt-switch CLI project switcher pattern](https://github.com/jairus-m/dbt-switch)
- Pattern: [CLI design guidelines — noun-verb subcommand structure](https://clig.dev/)
- Pattern: [Per-user Docker container isolation for multi-tenant AI agents](https://dev.to/reeddev42/per-user-docker-container-isolation-a-pattern-for-multi-tenant-ai-agents-8eb)
- Pattern: [Jinja2 variable substitution for configuration templating](https://pypi.org/project/Jinja2/)
- Pattern: [Click context system for persistent config](https://betterstack.com/community/guides/scaling-python/click-explained/)

---
*Feature research for: OpenClaw v1.1 multi-project framework capabilities*
*Researched: 2026-02-23*
