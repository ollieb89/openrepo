# Development Workflow Findings: Adaptability Audit

> **Date:** 2026-02-23
> **Scope:** Full analysis of OpenClaw's workflow portability across projects
> **Verdict:** 80% generic, 20% hardcoded to PumplAI — fixable with a project-context layer

---

## 1. Executive Summary

The OpenClaw orchestration system (state engine, container spawning, monitoring, snapshots) is **project-agnostic by design**. However, the **configuration layer** binds the entire system to a single project ("PumplAI") through hardcoded paths, agent IDs, and tech-stack assumptions in SOUL files.

To support multiple projects (or even switch projects), you'd need to change **6 files** and **~15 lines**. That's the gap. Below is what's coupled, what's already generic, and a concrete decoupling plan.

---

## 2. What's Already Generic (No Changes Needed)

| Component | Files | Why It's Portable |
|-----------|-------|-------------------|
| State Engine | `orchestration/state_engine.py` | Uses `JarvisState` class — no project references, just JSON + flock |
| Snapshot System | `orchestration/snapshot.py` | Generic git diff/merge operations |
| CLI Monitor | `orchestration/monitor.py` | Reads state.json, project-agnostic |
| Container Runtime | `docker/l3-specialist/Dockerfile`, `entrypoint.sh` | Uses env vars, no project-specific tools |
| Pool Manager | `skills/spawn_specialist/pool.py` (logic) | Asyncio semaphore, generic concurrency |
| Router Skill | `skills/router_skill/index.js` | CLI delegation via `openclaw agent` — generic |
| Dashboard | `workspace/occc/` | Reads state.json, not hardcoded to any project |

**These components will work for any project without modification.**

---

## 3. What's Hardcoded (Must Change for Multi-Project)

### 3.1 Workspace Paths — `openclaw.json` (4 occurrences)

```json
// Lines 73, 83, 93, 103 — ALL point to same hardcoded path
"workspace": "/home/ollie/Development/Projects/pumplai"
```

**Impact:** Every agent is locked to one project directory. Switching projects means manually editing 4 lines.

### 3.2 Agent Hierarchy — Foreign Key Strings

| File | Line | Hardcoded Value |
|------|------|-----------------|
| `agents/l3_specialist/config.json` | 5-6 | `"reports_to": "pumplai_pm"`, `"spawned_by": "pumplai_pm"` |
| `agents/pumplai_pm/agent/config.json` | 6 | `"delegates_to": "l3_specialist"` |
| `agents/clawdia_prime/agent/config.json` | 19 | `"subordinates": ["pumplai_pm"]` |

**Impact:** The L1→L2→L3 chain is hardwired. You can't plug in a different L2 PM for a different project.

### 3.3 Tech Stack in SOUL.md

```markdown
# agents/pumplai_pm/agent/SOUL.md line 10-13
2. **STRICT TECH STACK:**
   - **Frontend:** Next.js 16, React 19, Tailwind v4, NextAuth.js v5.
   - **Backend:** Python 3.12, FastAPI.
   - **Infrastructure:** Docker-based isolation, PostgreSQL.
```

**Impact:** PumplAI_PM will enforce this tech stack on *any* project it manages. A Go/Rust/Django project would get Next.js recommendations.

### 3.4 L3 Config Path — `spawn.py` Line 25

```python
config_path = Path(__file__).parent.parent.parent / "agents" / "l3_specialist" / "config.json"
```

**Impact:** Only one L3 config can exist. Can't have project-specific L3 configurations (e.g., different runtimes or resource limits per project).

### 3.5 State/Snapshot Paths — `orchestration/config.py`

```python
STATE_FILE = Path('workspace/.openclaw/workspace-state.json')
SNAPSHOT_DIR = Path('workspace/.openclaw/snapshots/')
```

**Impact:** State is always stored in `workspace/.openclaw/`. Can't point to a different project's state without modifying this file.

### 3.6 Container Labels & Image Name — `spawn.py`

```python
client.images.get("openclaw-l3-specialist:latest")  # Line 76
"openclaw.managed": "true"                           # Line 131
```

**Impact:** Minor — these are namespace labels. But if you ran two projects simultaneously, you couldn't distinguish their containers.

---

## 4. Proposed Fix: Project Context Layer

### Concept

Introduce a **project manifest** (`project.json`) that each project workspace contains. OpenClaw reads this at runtime instead of hardcoding values.

### 4.1 New File: `projects/<project-id>/project.json`

```json
{
  "id": "pumplai",
  "name": "PumplAI",
  "workspace": "/home/ollie/Development/Projects/pumplai",
  "tech_stack": {
    "frontend": "Next.js 16, React 19, Tailwind v4",
    "backend": "Python 3.12, FastAPI",
    "infra": "Docker, PostgreSQL"
  },
  "agent_overrides": {
    "l2_pm": "pumplai_pm",
    "l3_executor": "l3_specialist"
  },
  "l3_config": {
    "mem_limit": "4g",
    "cpu_quota": 100000,
    "runtimes": ["claude-code", "codex", "gemini-cli"]
  }
}
```

### 4.2 Changes Required

| File | Change | Effort |
|------|--------|--------|
| `openclaw.json` | Replace hardcoded workspace paths with `"workspace": "$PROJECT"` or remove them; add `"active_project": "pumplai"` | Small |
| `orchestration/config.py` | Read `STATE_FILE` and `SNAPSHOT_DIR` from env var or project config | Small |
| `spawn.py:load_l3_config()` | Accept project ID parameter, resolve config path dynamically | Small |
| `spawn.py:spawn_l3_specialist()` | Add `project_id` param to labels for multi-project container tracking | Small |
| `agents/pumplai_pm/agent/SOUL.md` | Move tech stack to `project.json`, SOUL references `${project.tech_stack}` | Medium |
| Agent `config.json` files | Replace hardcoded IDs with role-based references (`"reports_to": "$L1"`) or read from project config | Medium |

### 4.3 What This Enables

- **Switch projects:** `openclaw project switch <id>` reads the right `project.json`
- **Multiple simultaneous projects:** Different L2 PMs per project, each with their own tech stack
- **Project templates:** `openclaw project init --template fullstack` scaffolds a new project.json
- **No SOUL rewrites per project:** Tech stack comes from config, not hardcoded in SOUL.md

---

## 5. Quick Win vs. Full Refactor

### Quick Win (30 min, unblocks multi-project)

1. Add `"active_project"` field to `openclaw.json`
2. Move workspace path to a single source: `projects/<id>/project.json`
3. Update `orchestration/config.py` to accept env var overrides:
   ```python
   STATE_FILE = Path(os.environ.get('OPENCLAW_STATE_FILE', 'workspace/.openclaw/workspace-state.json'))
   ```
4. Update `spawn.py` to accept `--project` flag

### Full Refactor (Phase 5+ work)

1. Project context layer with `project.json` manifests
2. SOUL templating (inject tech stack from project config)
3. Dynamic agent hierarchy (project declares its own L2/L3 chain)
4. Multi-project dashboard (filter by `openclaw.project_id` label)
5. `openclaw project` CLI subcommand

---

## 6. File-by-File Impact Map

```
openclaw.json                           ← HIGH: 4 hardcoded workspace paths
agents/pumplai_pm/agent/SOUL.md         ← HIGH: tech stack hardcoded
agents/pumplai_pm/agent/config.json     ← MED:  delegates_to hardcoded
agents/l3_specialist/config.json        ← MED:  reports_to, spawned_by hardcoded
orchestration/config.py                 ← MED:  state/snapshot paths hardcoded
skills/spawn_specialist/spawn.py        ← MED:  L3 config path, image name, default workspace
skills/spawn_specialist/pool.py         ← LOW:  default workspace path
agents/clawdia_prime/agent/config.json  ← LOW:  subordinates list hardcoded
```

---

## 7. Recommendation

**Start with the Quick Win.** It unblocks project switching with minimal disruption and doesn't require restructuring the agent hierarchy. The full project-context layer is a natural Phase 5 or new milestone item that builds on this foundation.

The core orchestration is already clean — this is purely a configuration-layer problem, not an architecture problem.
