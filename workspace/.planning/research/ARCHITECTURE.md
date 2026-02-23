# Architecture Research

**Domain:** Multi-project AI Swarm Orchestration Framework (v1.1)
**Researched:** 2026-02-23
**Confidence:** HIGH — based on direct analysis of existing codebase

---

## Context: What Already Exists (v1.0)

The v1.0 foundation is operational. This document focuses exclusively on how v1.1 features
integrate with the existing architecture, what components need modification, and what is new.

### Existing Components (Do Not Rewrite)

| Component | File | v1.1 Status |
|-----------|------|-------------|
| JarvisState | `orchestration/state_engine.py` | Unchanged — accepts any path via constructor |
| Snapshot system | `orchestration/snapshot.py` | Unchanged — workspace-agnostic |
| CLI monitor | `orchestration/monitor.py` | Modify: add `--project` flag, derive state-file from project |
| project_config.py | `orchestration/project_config.py` | Extend: add `list_projects()`, `create_project()`, `remove_project()` |
| config.py | `orchestration/config.py` | Unchanged — env var overrides already support per-project injection |
| spawn.py | `skills/spawn_specialist/spawn.py` | Modify: add `pool_isolated` label, pass project_id env to container |
| pool.py | `skills/spawn_specialist/pool.py` | Modify: accept `pool_mode` param; use per-project semaphore when isolated |
| swarm API | `workspace/occc/src/app/api/swarm/route.ts` | Modify: accept `?project=<id>` query param |
| SSE stream | `workspace/occc/src/app/api/swarm/stream/route.ts` | Modify: scope state-file path to active project |
| jarvis.ts | `workspace/occc/src/lib/jarvis.ts` | Unchanged — schema is valid regardless of which state file is read |
| openclaw.json | Root config | Modify: `active_project` already exists; no schema changes needed |
| projects/pumplai/project.json | Project manifest | Reference — new projects follow this schema |

---

## System Overview: v1.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        User / Telegram / occc                            │
├─────────────────────────────────────────────────────────────────────────┤
│                     openclaw project CLI (NEW)                           │
│         init / switch / list / remove  +  templates                      │
├─────────────────────────────────────────────────────────────────────────┤
│               Project Registry Layer (EXTENDED)                          │
│  openclaw.json: active_project  ←→  projects/<id>/project.json          │
│  orchestration/project_config.py: resolver + CRUD                        │
├────────────────────┬────────────────────────────────────────────────────┤
│  Per-Project State │  Per-Project Snapshots  │  Per-Project Pool         │
│  workspace/.openclaw/            │  (isolated opt-in)                    │
│   <project-id>-state.json (NEW)  │  asyncio.Semaphore per project (MOD)  │
├────────────────────┴────────────────────────────────────────────────────┤
│              SOUL Templating Layer (NEW)                                 │
│  agents/templates/soul-defaults.md  +  projects/<id>/soul-override.md   │
│  Rendered at agent startup → final SOUL injected as CLAUDE.md           │
├─────────────────────────────────────────────────────────────────────────┤
│              L3 Container Pool (MODIFIED)                                │
│  spawn.py — passes OPENCLAW_PROJECT env var into container               │
│  pool.py  — shared (default) or per-project semaphore (isolated mode)   │
├─────────────────────────────────────────────────────────────────────────┤
│              occc Dashboard (MODIFIED)                                   │
│  Project switcher dropdown → writes active_project → SSE re-scopes      │
│  /api/swarm?project=<id>  /api/swarm/stream?project=<id>                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities: New vs Modified

### New Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Project CLI | `orchestration/cli/project.py` | `openclaw project init/switch/list/remove` subcommands |
| CLI entry point | `orchestration/cli/__init__.py` or update existing openclaw entry | Wire `project` subcommand group |
| SOUL template engine | `orchestration/soul_template.py` | Merge `soul-defaults.md` with per-project override; output rendered SOUL |
| Default SOUL template | `agents/templates/soul-defaults.md` | Canonical defaults: hierarchy, quality gate, escalation rules |
| Project switch API | `workspace/occc/src/app/api/projects/route.ts` | GET list of projects; PATCH to switch active project |

### Modified Components

| Component | File | What Changes |
|-----------|------|-------------|
| `project_config.py` | `orchestration/project_config.py` | Add `list_projects()`, `create_project(id, template)`, `remove_project(id)`, `switch_active_project(id)` |
| `spawn.py` | `skills/spawn_specialist/spawn.py` | Inject `OPENCLAW_PROJECT` env var into container environment; add `openclaw.project` Docker label |
| `pool.py` | `skills/spawn_specialist/pool.py` | Accept `pool_mode: str = "shared"` param on `L3ContainerPool`; if `"isolated"`, create per-project semaphore key |
| `monitor.py` | `orchestration/monitor.py` | Add `--project <id>` flag; resolve `state_file` from `project_config.get_state_file(project_id)` |
| Swarm API route | `workspace/occc/src/app/api/swarm/route.ts` | Read `project` query param; resolve correct state-file path per project |
| SSE stream route | `workspace/occc/src/app/api/swarm/stream/route.ts` | Watch correct state-file path based on `project` query param |
| `openclaw.json` | Root config | No schema change; `active_project` field already present |
| SOUL files (per agent) | `agents/<id>/agent/SOUL.md` | Long-term: replace project-specific content with template references; keep format |

---

## State File Isolation Pattern

The current architecture has one global state file at `workspace/.openclaw/workspace-state.json`.
v1.1 needs per-project state so tasks from different projects do not intermingle.

**Approach: per-project state file under OpenClaw root `.openclaw/` directory**

```
.openclaw/                         ← OpenClaw root-level hidden dir (new)
  pumplai-state.json               ← per-project Jarvis state
  myapp-state.json                 ← per-project Jarvis state
  snapshots/
    pumplai/                       ← per-project snapshots
    myapp/
```

The existing `workspace/.openclaw/workspace-state.json` path was workspace-scoped.
v1.1 moves state files to the OpenClaw root scope so multiple projects with different
workspaces can all be tracked by one running system.

**Resolution function to add to `project_config.py`:**

```python
def get_state_file(project_id: Optional[str] = None) -> Path:
    """Return per-project state file path under OpenClaw root .openclaw/."""
    if project_id is None:
        project_id = get_active_project_id()
    root = _find_project_root()
    state_dir = root / ".openclaw"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{project_id}-state.json"


def get_snapshot_dir(project_id: Optional[str] = None) -> Path:
    """Return per-project snapshot directory."""
    if project_id is None:
        project_id = get_active_project_id()
    root = _find_project_root()
    snap_dir = root / ".openclaw" / "snapshots" / project_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    return snap_dir
```

**Migration:** The existing `workspace/.openclaw/workspace-state.json` becomes legacy.
Rename/copy to `.openclaw/pumplai-state.json` in a migration step during `openclaw project init pumplai`.

---

## SOUL Templating Pattern

The problem: `agents/pumplai_pm/agent/SOUL.md` hardcodes PumplAI-specific tech stack and workspace paths.
Adding a second project would require duplicating and maintaining a separate agent directory.

**Approach: Default template + project override merging**

```
agents/
  templates/
    soul-defaults.md          ← canonical tier behaviors, quality gates, escalation
    l2-soul-template.md       ← L2-specific defaults (hierarchy section, delegate rules)
    l1-soul-template.md       ← L1-specific defaults
projects/
  pumplai/
    soul-override.md          ← project-specific overrides (tech stack, workspace path)
  myapp/
    soul-override.md
```

**`soul_template.py` merging rules:**

```python
def render_soul(agent_tier: str, project_id: str) -> str:
    """
    Merge tier-level default template with project-specific overrides.
    Sections marked ##OVERRIDE in defaults are replaced by project overrides.
    Missing override sections fall back to defaults.
    Returns rendered SOUL as markdown string.
    """
```

The merge is section-based: the override file replaces named sections
(e.g., `## TECH STACK`, `## WORKSPACE`) while inheriting all other sections from the template.
This avoids full-file duplication while letting each project define what's different.

**Rendered output:** Written to `agents/<id>/agent/SOUL.md` at `openclaw project init` time,
and re-renderable with `openclaw project sync-souls <id>`. Not auto-rendered at runtime — avoids
agent startup latency and keeps SOUL files inspectable.

---

## Pool Isolation Pattern

Current `pool.py` uses one global `asyncio.Semaphore(max_concurrent=3)` shared across all tasks.
With multiple projects, a slow project's tasks could block another project's containers.

**Approach: configurable pool mode per project**

```
project.json:
{
  "pool_isolation": "shared"   // default: all projects share the 3-slot semaphore
                               // "isolated": project gets its own semaphore with its own max_concurrent
}
```

**`pool.py` modification — per-project semaphore registry:**

```python
_project_semaphores: Dict[str, asyncio.Semaphore] = {}

def get_project_semaphore(project_id: str, max_concurrent: int) -> asyncio.Semaphore:
    key = project_id
    if key not in _project_semaphores:
        _project_semaphores[key] = asyncio.Semaphore(max_concurrent)
    return _project_semaphores[key]
```

`L3ContainerPool.__init__` gains a `project_id` param. When `pool_isolation == "isolated"`,
it uses `get_project_semaphore(project_id, max_concurrent)` instead of the shared semaphore.

The `openclaw.project` Docker label already exists in `spawn.py` labels — extend it to include
the project ID so Docker filters can scope container listing per project.

---

## Project CLI Integration Pattern

The CLI entry point is the `openclaw` command. The new `project` subcommand group routes to
`orchestration/cli/project.py`. This matches the existing pattern in `orchestration/monitor.py`
which has its own argparse `main()`.

**Command structure:**

```
openclaw project init <id> [--template fullstack|backend|ml-pipeline] [--workspace <path>]
openclaw project switch <id>
openclaw project list
openclaw project remove <id> [--force]
```

**`init` creates:**
- `projects/<id>/project.json` from template
- `projects/<id>/soul-override.md` from template
- `.openclaw/<id>-state.json` (empty Jarvis state scaffold)
- Optional: renders SOUL files into `agents/` if agent identity files don't exist

**Templates live at:** `projects/templates/fullstack/`, `projects/templates/backend/`, `projects/templates/ml-pipeline/`
Each template is a directory with `project.json` and `soul-override.md` with placeholder values.

**`switch` modifies:** `openclaw.json` `active_project` field (atomic JSON write).

---

## Dashboard Project Switcher Integration

The existing `workspace/occc/src/app/api/swarm/route.ts` hardcodes state file paths.
The SSE stream route also hardcodes the same path.

**Approach: query param scoping + new projects API**

```
GET /api/projects          → list all projects (reads projects/ dir)
PATCH /api/projects/active → { project_id: "myapp" } → writes openclaw.json active_project
GET /api/swarm?project=<id>          → scoped swarm state
GET /api/swarm/stream?project=<id>   → scoped SSE stream
```

The `readStateFile()` function in `route.ts` needs to resolve path from project_id:

```typescript
function getStateFilePath(projectId?: string): string {
  if (projectId) {
    return path.join(OPENCLAW_ROOT, '.openclaw', `${projectId}-state.json`);
  }
  // fallback to env var or active project
  return process.env.STATE_FILE || resolveActiveProjectStatePath();
}
```

The dashboard UI adds a `<ProjectSwitcher>` dropdown component to the top nav that:
1. Calls `GET /api/projects` on mount (or SWR polling)
2. Shows current `active_project` as selected
3. On selection change: calls `PATCH /api/projects/active` then re-fetches swarm state

The SSE stream URL changes from `/api/swarm/stream` to `/api/swarm/stream?project=<id>`.
The `useSwarmState` hook needs to include the active project in the query.

---

## Data Flow Changes

### Before (v1.0)

```
openclaw project init (does not exist)
spawn.py → workspace/.openclaw/workspace-state.json
pool.py  → single semaphore (global)
swarm API → hardcoded state file path
SSE stream → hardcoded state file path
monitor.py → config.STATE_FILE (global)
```

### After (v1.1)

```
openclaw project init <id>
  → writes projects/<id>/project.json
  → creates .openclaw/<id>-state.json
  → renders SOUL from template + override

openclaw project switch <id>
  → updates openclaw.json active_project

spawn.py
  → gets project_id (from arg or active project)
  → sets OPENCLAW_PROJECT env var in container
  → sets openclaw.project label on container
  → JarvisState path = .openclaw/<id>-state.json

pool.py
  → if pool_isolation=="isolated": per-project semaphore
  → else: shared semaphore (existing behavior)

swarm API (?project=pumplai)
  → reads .openclaw/pumplai-state.json
  → reads openclaw.json agents list (unchanged)

SSE stream (?project=pumplai)
  → watches .openclaw/pumplai-state.json

monitor.py --project pumplai
  → reads .openclaw/pumplai-state.json

occc dashboard
  → ProjectSwitcher → PATCH /api/projects/active
  → SSE re-connects with new project query param
```

---

## File Structure Changes

```
.openclaw/                         ← NEW: root-level state directory
  pumplai-state.json               ← migrated from workspace/.openclaw/workspace-state.json
  <project-id>-state.json          ← new projects
  snapshots/
    pumplai/                       ← migrated from workspace/.openclaw/snapshots/
    <project-id>/

projects/
  pumplai/
    project.json                   ← existing (no change)
    soul-override.md               ← NEW: project-specific SOUL overrides
  templates/                       ← NEW: project scaffold templates
    fullstack/
      project.json
      soul-override.md
    backend/
      project.json
      soul-override.md
    ml-pipeline/
      project.json
      soul-override.md

agents/
  templates/                       ← NEW: canonical SOUL templates
    soul-defaults.md
    l1-soul-template.md
    l2-soul-template.md

orchestration/
  project_config.py                ← EXTEND: add CRUD + get_state_file() + get_snapshot_dir()
  soul_template.py                 ← NEW: SOUL merge logic
  cli/                             ← NEW: CLI subcommand modules
    __init__.py
    project.py                     ← project init/switch/list/remove

workspace/occc/src/
  app/api/
    projects/
      route.ts                     ← NEW: list projects + switch active project
    swarm/
      route.ts                     ← MODIFY: accept ?project= query param
      stream/
        route.ts                   ← MODIFY: accept ?project= query param
  components/
    ProjectSwitcher.tsx            ← NEW: dropdown UI component
  hooks/
    useSwarmState.ts               ← MODIFY: include active project in query
```

---

## Architectural Patterns

### Pattern 1: Convention-Over-Configuration SOUL Inheritance

**What:** A default template provides canonical behaviors for each tier. Project overrides replace only named sections.
**When to use:** Any time a new project-specific agent identity needs to be created.
**Trade-offs:** Merging complexity is low (section-based replace), but requires templates to use stable section headings. Projects that need fully custom SOUL can still write complete override files.

### Pattern 2: Path-Scoped JarvisState

**What:** `JarvisState` already accepts any path. Per-project state is achieved by passing `.openclaw/<id>-state.json` instead of the legacy path.
**When to use:** Always, for all state reads/writes in v1.1.
**Trade-offs:** No code change needed in `state_engine.py`. Path resolution is centralized in `project_config.py`. Legacy state files in `workspace/.openclaw/` need a one-time migration.

### Pattern 3: Opt-In Pool Isolation

**What:** Default pool is shared (max 3 containers globally). Projects that set `"pool_isolation": "isolated"` in `project.json` get their own semaphore with their own `max_concurrent` value.
**When to use:** High-priority or resource-intensive projects that should not queue behind other projects' containers.
**Trade-offs:** Isolated mode can exceed the physical 3-container limit if multiple projects each get their own semaphore. Document this as expected behavior — `max_concurrent` in `project.json` becomes the ceiling per project when isolated.

---

## Anti-Patterns

### Anti-Pattern 1: Agent Directories Per Project

**What people might do:** Create `agents/myapp_pm/` with full identity, SOUL, config, skills for each new project.
**Why it's wrong:** Duplicates 80% of identical content. Configuration drift between projects. Scaling to 10 projects means 10 near-identical directories.
**Do this instead:** One `agents/l2_pm/` directory with SOUL templating. Project identity lives in `projects/<id>/soul-override.md`. Only fork the full agent directory if an agent truly has different skills (different skill_registry).

### Anti-Pattern 2: Global State File with Project Tags

**What people might do:** Keep one `workspace-state.json` and add a `project_id` field to each task.
**Why it's wrong:** Shared state file becomes a cross-project lock contention point. Dashboard cannot scope SSE stream to one project without filtering on the client. State file grows unboundedly.
**Do this instead:** Per-project state files at `.openclaw/<id>-state.json`. Each project's Jarvis state is completely independent. State file sizes stay bounded per project.

### Anti-Pattern 3: Dashboard Re-Architecting for Multi-Project

**What people might do:** Redesign the entire dashboard data model to support multiple projects in parallel.
**Why it's wrong:** Over-engineering for a switcher use case. The user looks at one project at a time.
**Do this instead:** Project switcher changes `active_project` and the dashboard re-fetches. One active project at a time is the mental model. The API accepts `?project=<id>` but the UI only ever passes the active project.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `project_config.py` ↔ `spawn.py` | Direct import | `get_state_file(project_id)` replaces hardcoded path in spawn.py |
| `project_config.py` ↔ `pool.py` | Direct import | `load_project_config(project_id).get("pool_isolation")` determines semaphore mode |
| `project_config.py` ↔ `monitor.py` | Direct import | `get_state_file(project_id)` replaces `STATE_FILE` global |
| `project_config.py` ↔ `cli/project.py` | Direct import | CRUD operations, template scaffolding |
| `soul_template.py` ↔ `cli/project.py` | Direct import | Called during `openclaw project init` to render SOUL files |
| `projects/ dir` ↔ `occc /api/projects/route.ts` | Filesystem read | API reads `projects/` directory to list available projects |
| `openclaw.json` ↔ `occc /api/projects/route.ts` | Filesystem read/write | API reads/writes `active_project` field |
| `occc ProjectSwitcher` ↔ `/api/projects` | HTTP REST | GET list, PATCH active |
| `occc useSwarmState` ↔ `/api/swarm/stream` | SSE | Query param carries active project ID |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Docker | Existing via `docker-py` | Add `openclaw.project` label to containers in spawn.py |
| Git | Existing via subprocess | No change — snapshot.py operates on workspace path, not state path |

---

## Build Order

Build order is determined by dependency direction. Nothing in the dashboard or pool can be tested
until the state file path resolution works. The CLI is a delivery mechanism, not a dependency.

```
1. project_config.py extensions
   (get_state_file, get_snapshot_dir, list_projects, create_project, remove_project, switch_active_project)
   → Zero dependencies on new code. Everything else depends on this.

2. SOUL template engine
   (soul_template.py + agents/templates/ + projects/<id>/soul-override.md)
   → Depends only on filesystem layout. No runtime dependencies.
   → Can be built in parallel with step 1 after templates exist.

3. spawn.py + pool.py modifications
   (inject OPENCLAW_PROJECT, per-project semaphore, openclaw.project label)
   → Depends on project_config.py get_state_file().

4. monitor.py modification
   (--project flag, derive state-file from project_config)
   → Depends on project_config.py get_state_file().
   → Can be built in parallel with step 3.

5. Project CLI (orchestration/cli/project.py)
   (init, switch, list, remove + template scaffolding)
   → Depends on project_config.py CRUD + soul_template.py.
   → Depends on steps 1 and 2 being complete.

6. Migration: .openclaw/ root dir, migrate pumplai state
   (create .openclaw/, copy workspace/.openclaw/workspace-state.json → .openclaw/pumplai-state.json)
   → Run as part of step 5 init, or as standalone migration step.

7. occc dashboard changes
   (projects API route, ProjectSwitcher component, swarm route ?project= scoping)
   → Depends on project_config.py layout being stable (step 1).
   → Can be built in parallel with steps 3-5 once step 1 is done.

8. End-to-end verification
   (create a second project, spawn L3 tasks, confirm state isolation, confirm dashboard switching)
   → Depends on all above steps.
```

**Critical path:** steps 1 → 3 → 8. Steps 2, 4, 5, 6, 7 can proceed in parallel once step 1 is done.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Existing code analysis | HIGH | Read all relevant files directly |
| State file scoping approach | HIGH | JarvisState path-agnostic; pattern is clean |
| SOUL template merging | MEDIUM | Section-based merge is straightforward; edge cases in malformed overrides need defensive coding |
| Pool isolation semaphore | HIGH | asyncio.Semaphore pattern is straightforward; per-project dict is standard |
| CLI subcommand pattern | HIGH | Python argparse subparsers pattern matches existing monitor.py |
| Dashboard query param scoping | HIGH | Next.js route handler URL params are trivial; SWR re-fetch on project change is standard |
| Migration from legacy state path | MEDIUM | Existing workspace may have in-flight tasks; migration needs to be idempotent |

---

## Sources

- Direct analysis: `/home/ollie/.openclaw/orchestration/state_engine.py`
- Direct analysis: `/home/ollie/.openclaw/orchestration/project_config.py`
- Direct analysis: `/home/ollie/.openclaw/orchestration/config.py`
- Direct analysis: `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py`
- Direct analysis: `/home/ollie/.openclaw/skills/spawn_specialist/pool.py`
- Direct analysis: `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/route.ts`
- Direct analysis: `/home/ollie/.openclaw/workspace/occc/src/app/api/swarm/stream/route.ts`
- Direct analysis: `/home/ollie/.openclaw/projects/pumplai/project.json`
- Direct analysis: `/home/ollie/.openclaw/openclaw.json`
- Direct analysis: `/home/ollie/.openclaw/agents/pumplai_pm/agent/SOUL.md`
- Direct analysis: `/home/ollie/.openclaw/.planning/PROJECT.md`
- Direct analysis: `/home/ollie/.openclaw/.planning/STATE.md`

---

*Architecture research for: OpenClaw v1.1 — Project Agnostic Multi-Project Support*
*Researched: 2026-02-23*
