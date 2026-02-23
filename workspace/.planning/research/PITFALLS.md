# Pitfalls Research

**Domain:** Multi-project support added to existing single-project AI swarm orchestration (OpenClaw v1.1)
**Researched:** 2026-02-23
**Confidence:** HIGH — pitfalls derived directly from codebase inspection of v1.0 implementation plus multi-tenant orchestration patterns

---

## Critical Pitfalls

### Pitfall 1: Single Global State File Becomes Cross-Project Data Corruption Vector

**What goes wrong:**
`workspace/.openclaw/workspace-state.json` is the single source of truth for the Jarvis Protocol. When two projects run simultaneously, their L3 tasks write to the same file. `task_id` values like `task-abc123` carry no project namespace. Project A's tasks appear in Project B's dashboard view. Worse, `JarvisState.update_task()` does a read-modify-write under LOCK_EX — the read picks up tasks from both projects, so a reject or status mutation from one project can silently overwrite a status from another.

**Why it happens:**
The state file path is compiled from a constant in `orchestration/config.py` pointing at `workspace/.openclaw/workspace-state.json` — a path that bakes in the single-project workspace. The env var override (`OPENCLAW_STATE_FILE`) exists but is not wired through `project_config.py`, so switching `active_project` in `openclaw.json` does not change the state file path. Both projects resolve to the same physical file.

**How to avoid:**
Each project must get its own state file. The resolver chain must be: `project_config.get_state_file(project_id)` returning `{project.workspace}/.openclaw/workspace-state.json`. The pool and spawn modules must accept and thread a `state_file` argument resolved from the active project, not from a module-level constant. Never allow the state file path to be a module-global default once multi-project is live.

**Warning signs:**
- `list_all_tasks()` returns tasks whose `skill_hint` or `metadata.staging_branch` reference paths outside the active project's workspace
- Dashboard shows tasks for an inactive project
- Task `completed` events arrive for tasks not spawned in this session

**Phase to address:** Phase 1 (Config Decoupling) — must ship before any multi-project runtime work begins

---

### Pitfall 2: Container Names Collide Across Projects

**What goes wrong:**
`spawn.py` builds container names as `openclaw-l3-{task_id}`. If `task_id` generation is not project-scoped (e.g., it is a short timestamp or UUID fragment), two projects spawning simultaneously can produce `openclaw-l3-1708701234` from both. The second spawn hits Docker's "container name already in use" error and the pool's retry logic treats it as a task failure, triggering an automatic retry that will also collide.

A subtler variant: Docker labels currently use `openclaw.task_id` but not `openclaw.project_id`. The dashboard's Docker lib filters by `openclaw.managed=true` — with multiple projects, this returns containers from all projects, and the aggregated view is indistinguishable without a project label.

**Why it happens:**
Task IDs in v1.0 are caller-supplied strings — no enforced format. Container naming at line 104 of `spawn.py` (`f"openclaw-l3-{task_id}"`) is global-namespace. Labels carry tier and skill but not project identity.

**How to avoid:**
Prefix task IDs with the project slug at generation time: `{project_id}-{uuid4().hex[:8]}`. Alternatively, prefix the container name: `openclaw-{project_id}-l3-{task_id}`. Add `openclaw.project_id` to the Docker label set in spawn. The dashboard Docker query must support filtering by project label when a project is selected.

**Warning signs:**
- Docker `APIError: 409 Conflict` in pool logs during multi-project runs
- `docker ps --filter label=openclaw.managed=true` returns containers from projects you are not actively monitoring
- Orphaned containers with duplicate name patterns after a crash

**Phase to address:** Phase 1 (Config Decoupling) for label schema change, Phase 2 (Multi-Project Runtime) for naming convention enforcement

---

### Pitfall 3: Shared L3 Pool Semaphore Enforces Wrong Concurrency Boundary

**What goes wrong:**
`L3ContainerPool` uses `asyncio.Semaphore(max_concurrent=3)` as a pool-level concurrency gate. This semaphore is per-Python-process, not per-project. If PumplAI_PM and a second project's L2 both call `pool.spawn_and_monitor()`, they compete for the same 3 slots. A slow 600-second code task from Project A starves Project B entirely.

The `spawn_task()` convenience function in `pool.py` creates a new pool each time (so a new semaphore each time), which defeats the concurrency limit entirely for isolated callers and masks the real pooling problem.

**Why it happens:**
`L3ContainerPool.__init__` takes `max_concurrent=3` as a default and builds the semaphore immediately with no project context. The convenience function's "create a fresh pool per call" pattern looks correct in single-project use because there is always only one caller.

**How to avoid:**
Decide the pool isolation model before writing code: per-project pools are simpler and safer for v1.1. The pool must be instantiated per project ID and the semaphore limit read from `project.json:l3_overrides.max_concurrent`. Remove the `spawn_task()` convenience function or require callers to supply a pool reference.

**Warning signs:**
- Tasks from one project queue indefinitely while another project's tasks are executing
- `pool.get_active_count()` returns 3 even though only one project is actively spawning
- `spawn_task()` called without a pool reference (bypasses the semaphore, no concurrency control)

**Phase to address:** Phase 2 (Multi-Project Runtime)

---

### Pitfall 4: `active_project` in `openclaw.json` Is a Mutable Global — Concurrent Sessions Corrupt Each Other

**What goes wrong:**
`get_active_project_id()` reads `openclaw.json:active_project` on every call. `openclaw project switch <id>` will write to this field. If a developer runs `openclaw project switch projectB` in one terminal while an L3 task spawned for Project A is mid-execution, any subsequent call to `get_active_project_id()` (state file resolution, workspace path lookup, snapshot path) returns `projectB`. The in-flight L3 container writes its state update to the wrong state file. The v1.0 env var override (`OPENCLAW_PROJECT`) partially mitigates this but is not documented as the required pattern for concurrent use.

**Why it happens:**
Single global config file with a mutable `active_project` field — a pattern that works for single-session single-project use, and breaks under any concurrency. The `openclaw project switch` command, if implemented as a simple JSON patch, is not atomic and has no awareness of in-flight operations.

**How to avoid:**
Do not implement `switch` as a global mutation. The CLI resolves project context via `--project <id>` flag first, then `OPENCLAW_PROJECT` env var, then `active_project` fallback in that priority order. L3 spawns must capture the project ID at spawn time and embed it into the container environment as `OPENCLAW_PROJECT` so the entrypoint never reads from the shared config file during execution.

**Warning signs:**
- State file accumulates tasks from multiple projects without project namespacing
- Two terminal sessions with different `active_project` values produce unpredictable behavior
- Snapshot paths in `workspace/.openclaw/snapshots/` contain `.diff` files from a different project's workspace

**Phase to address:** Phase 1 (Config Decoupling) — the env-var-first lookup pattern must be established before any `switch` command is built

---

### Pitfall 5: SOUL Files Contain Hardcoded Project-Specific Identity — Templating Breaks Existing PumplAI Workflow

**What goes wrong:**
`agents/pumplai_pm/agent/SOUL.md` contains hardcoded paths (`/home/ollie/.openclaw/workspace`), hardcoded tech stack (Next.js 16, FastAPI, PostgreSQL), and hardcoded agent names (nextjs_pm, python_backend_worker). When the SOUL templating system replaces these with `{{workspace_path}}`, `{{tech_stack}}`, `{{subordinates}}` tokens, the rendered SOUL for PumplAI must produce output semantically identical to the current hardcoded file — otherwise ClawdiaPrime's existing memory about PumplAI_PM's identity is invalidated.

The subtler risk: if `{{subordinates}}` is resolved from `project.json:agents` and PumplAI's manifest only maps `l2_pm` and `l3_executor`, the agents `nextjs_pm` and `python_backend_worker` vanish from the rendered SOUL. The L2 PM agent loses authority over its actual workers.

**Why it happens:**
Templating systems are designed around the template, not around preserving output fidelity with legacy hardcoded files. The migration is treated as "just string replacement" when it requires careful mapping of every hardcoded value to a project manifest field, plus a validation step confirming the rendered output matches the v1.0 baseline.

**How to avoid:**
Before building the templating engine, generate a "golden baseline" from the current PumplAI SOUL.md. After implementing templating, render PumplAI's SOUL and diff against the baseline. Zero semantic diff required for green light. Add all referenced agents (not just the primary L3 executor) to `project.json:agents` as an explicit list. Treat the SOUL template as append-only for v1.1 — do not remove any field that exists in the v1.0 SOUL.

**Warning signs:**
- Rendered SOUL references `{{` tokens that were not substituted (template variable leak)
- `project.json:agents` only maps `l2_pm` and `l3_executor` but the SOUL references `nextjs_pm` and `python_backend_worker`
- SOUL rendering tests assert that template tokens were replaced, but not that the output content is semantically correct

**Phase to address:** Phase 1 (Config Decoupling) — SOUL template baseline test must be a Phase 1 exit criterion

---

### Pitfall 6: Dashboard SSE Stream and Cache Are Tied to a Single State File Path

**What goes wrong:**
`workspace/occc/src/app/api/swarm/route.ts` has `DEFAULT_STATE_FILE` hardcoded to `/home/ollie/.openclaw/workspace/.openclaw/workspace-state.json`. The `cachedState` variable is a module-level singleton with a single `mtime` key. When multi-project support arrives and the dashboard needs to display Project A and Project B, the cache cannot hold two states — switching projects invalidates the entire cache, causing a cold-read on every project switch. The SSE stream route (`/api/swarm/stream`) has no project parameter, so it always streams the single hardcoded state file regardless of what project the user has selected in the UI.

**Why it happens:**
Single-project assumption was baked into the route handler at implementation time. The `process.env.STATE_FILE` override is a server-level env var that cannot be changed per-request by the client. The cache key is implicit (the single `cachedState` variable) rather than a map from project ID to cached state.

**How to avoid:**
The SSE stream route must accept a `?project=<id>` query parameter and resolve the state file path from a server-side project registry. The cache must be a `Map<projectId, CachedState>`. The `DEFAULT_STATE_FILE` constant must be replaced with a `resolveStateFile(projectId)` function. Both the REST and SSE routes must be updated in the same phase — updating one without the other creates a split-brain state.

**Warning signs:**
- Dashboard displays correct data for Project A but shows stale or empty data after switching to Project B
- SSE stream does not update after `openclaw project switch`
- `cachedState` is never invalidated after project switch because mtime comparison is against the old project's file

**Phase to address:** Phase 4 (Dashboard Project Switcher)

---

### Pitfall 7: Snapshot System Hardcodes `main` Branch — Multi-Project Repos May Use Different Default Branches

**What goes wrong:**
`snapshot.py:capture_semantic_snapshot()` generates its diff with `git diff main...HEAD`. `l2_review_diff()` and `l2_merge_staging()` also reference `main` explicitly in subprocess calls. If a new project's repository uses `master`, `trunk`, or `develop` as its default branch, every snapshot produces an empty diff (HEAD is already ahead of `main` which doesn't exist) and every merge fails with "branch main not found".

The branch detection logic in `create_staging_branch()` detects the default branch via `symbolic-ref refs/remotes/origin/HEAD` but this value is only stored in a local variable during branch creation. It is never threaded through to `capture_semantic_snapshot()` or `l2_merge_staging()`.

**Why it happens:**
`create_staging_branch()` was written first and had the fallback detection. The diff and merge functions were written later assuming the workspace is the known PumplAI workspace whose default branch is `main`. No test exercises a non-`main` workspace.

**How to avoid:**
Extract `detect_default_branch(workspace_path)` as a shared utility function. Call it in `capture_semantic_snapshot()`, `l2_review_diff()`, and `l2_merge_staging()` instead of the hardcoded string `"main"`. Store the detected default branch in `project.json` as an optional `git.default_branch` override to avoid repeated subprocess calls.

**Warning signs:**
- `git diff main...HEAD` returns empty output for a new project
- Snapshots are created but show zero files changed and zero insertions
- `l2_merge_staging()` returns `GitOperationError: Failed to checkout main` for a project using `master`

**Phase to address:** Phase 2 (Multi-Project Runtime) — must be caught during first non-PumplAI project integration test

---

### Pitfall 8: `openclaw.json` Agent List Is Project-Unaware — New Projects Contaminate PumplAI Hierarchy View

**What goes wrong:**
`openclaw.json:agents.list` is a flat array containing all agents. The dashboard's `buildAgentHierarchy()` processes the entire list without filtering by project. Adding a new project's agents to `openclaw.json` immediately makes them appear in PumplAI's hierarchy view, inflating the tree and breaking the `reports_to` chain. Simultaneously, the `workspace` field on each agent entry in `openclaw.json` is hardcoded to the PumplAI path — this duplicates data that already lives in `projects/pumplai/project.json:workspace` and becomes a maintenance hazard.

**Why it happens:**
`openclaw.json` was designed as a system-wide config before per-project manifests existed. It conflates gateway config, auth, agent definitions, and Telegram settings in one file. The agent list was the authoritative source for the dashboard in v1.0 because there was no other source.

**How to avoid:**
In v1.1, the dashboard must build the agent list from the active project's `project.json:agents` mapping, not from `openclaw.json`. Do not add new project agents to `openclaw.json`. Agent definitions needed for routing (gateway dispatch) remain in `openclaw.json`, but the dashboard hierarchy is driven by project manifests. Remove the `workspace` field from `openclaw.json` agent entries — the authoritative source is `project.json`.

**Warning signs:**
- Dashboard shows agents from an inactive project in the hierarchy tree
- `reports_to` tree has orphaned nodes whose parent no longer exists in the active project
- Two agents with the same `id` but different `workspace` values exist across `openclaw.json` and `project.json`

**Phase to address:** Phase 1 (Config Decoupling) — agent source-of-truth must be resolved before dashboard work begins

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep `active_project` as mutable global in `openclaw.json` | No schema change required | Concurrent sessions corrupt each other; any automation pipeline calling two project commands in sequence breaks | Never once multi-project runtime is live |
| Generate task IDs without project prefix | Simpler caller API | Container name collisions, cross-project state pollution, impossible to trace task origin in logs | Never for v1.1 and beyond |
| Use module-level `cachedState` singleton in dashboard route | Zero refactor needed | Project switching produces stale cache reads; multi-project dashboard is impossible | Acceptable during Phase 4 development only if project switcher is gated behind a feature flag |
| Hardcode `"main"` in snapshot diff/merge calls | Passes all existing tests (PumplAI uses `main`) | First non-main-branch project breaks silently with empty diffs | Never — fix in Phase 2 |
| Add new project agents to `openclaw.json:agents.list` | Works with existing dashboard code | PumplAI hierarchy view polluted; `workspace` paths diverge and must be updated in two places | Never |
| Share the single L3 pool semaphore across projects | No pool management code needed | Project starvation; one slow project's 600s tasks block all other projects | Acceptable for v1.1 only if documented as a known limitation and isolated in v1.2 |

---

## Integration Gotchas

Common mistakes when connecting multi-project support to existing subsystems.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Docker container spawning | Using `openclaw-l3-{task_id}` name without project prefix — collides under concurrent multi-project use | `openclaw-{project_id}-l3-{task_id}` or enforce that `task_id` is globally unique via `{project_id}-{uuid}` generation |
| Jarvis Protocol state file | Threading the same `Path("workspace/.openclaw/workspace-state.json")` constant across all callers | Resolve state file path from `project_config.get_state_file(project_id)` at call site; pass as argument, not module global |
| Dashboard SSE stream | SSE endpoint has no project context — always streams one hardcoded file | Accept `?project=<id>` query param; resolve file path server-side from project registry |
| Git snapshot diff | Hardcoded `main` in subprocess calls inside `capture_semantic_snapshot()` and `l2_merge_staging()` | Call `detect_default_branch(workspace_path)` or read `project.json:git.default_branch` |
| `openclaw.json` agent list | Appending new project agents to the global list | Dashboard reads hierarchy from `project.json:agents`; `openclaw.json` keeps only routing-layer agents |
| SOUL template rendering | Assuming string substitution preserves semantic meaning | Generate golden baseline from v1.0 SOUL, assert rendered output matches baseline before shipping |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Single fcntl-locked state file for all projects | Lock contention spikes; 5s timeout exceeded when multiple projects run heavy L3 loads simultaneously | Per-project state files eliminate cross-project lock contention entirely | 2+ active projects with 3 concurrent L3 tasks each |
| Dashboard cache as module-level singleton reads entire state file on every miss | Cache invalidation on project switch reads the entire state file twice (old and new project) | `Map<projectId, CachedState>` with per-project TTL; only invalidate the switched project's entry | Immediately on first project switch |
| `spawn_task()` convenience function creates a new pool per call with no shared semaphore | More than 3 containers spawn simultaneously despite `max_concurrent=3` in config | Remove the convenience function or require callers to supply a pool reference; enforce pool-per-project singleton | First caller that invokes `spawn_task()` in a loop |
| `get_active_project_id()` reads `openclaw.json` from disk on every call | Disk I/O accumulates when project ID is queried in tight loops during state updates | Cache project ID in memory per process lifetime; only re-read on explicit switch | Not a practical concern at v1.1 scale, but costs mount above 10 tasks/second |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| L3 container resolves workspace and state file from `active_project` at spawn time, but `active_project` can change mid-flight | State writes from an in-flight container land in the wrong project's state file; one project's audit trail is contaminated with another's task data | Embed project ID into container env at spawn (`OPENCLAW_PROJECT={project_id}`); entrypoint resolves state file from this env var, never from the host config file |
| Docker labels without `openclaw.project_id` allow any management operation filtering by `openclaw.managed=true` to match containers from all projects | A cleanup or reject operation targeting Project B could match and kill Project A's running containers if task_id suffixes collide | Add `openclaw.project_id` label to every spawned container; all management operations must filter by both `openclaw.managed=true` AND `openclaw.project_id={active_project}` |
| `openclaw.json` contains a plaintext Telegram bot token — multi-project config increases surface area if project manifests are templated from `openclaw.json` | Bot token exposure in project manifests if templating naively copies the full `openclaw.json` structure | Project manifests (`project.json`) must never inherit from or copy `openclaw.json`; they are separate config files with no inheritance relationship |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `openclaw project switch <id>` mutates global state without warning about in-flight tasks | Developer switches project context while L3 tasks are running for the previous project; spawns from the current pool now resolve the wrong workspace | Before switching, check for active tasks in the current project's state file; warn if any are in-flight; require `--force` to override |
| Dashboard project switcher shows all projects but does not clearly indicate which project owns which task | Developer cannot tell which L3 container belongs to which project when both are running simultaneously | Per-project color coding or badge on every task and container card; filter defaults to active project, with an explicit "all projects" toggle |
| `openclaw project init` generates a `project.json` that mirrors the PumplAI template including PumplAI-specific agent IDs | New project inadvertently routes L3 tasks to `pumplai_pm` instead of a project-specific agent | `init` templates must prompt for agent IDs and validate they exist in `openclaw.json:agents.list` before writing |
| No confirmation when removing a project with `openclaw project remove` | Accidental deletion of project state file, snapshots directory, and staging branches with no recovery path | Require explicit `--confirm` flag; print the list of files and branches that will be deleted before executing; do not auto-delete workspace data |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Per-project state files:** `project_config.get_state_file(project_id)` returns distinct paths — verify two active projects do not share the same JSON file path
- [ ] **Container naming:** `openclaw project list` followed by `docker ps` shows no naming pattern overlap between any two project's container name prefixes
- [ ] **SOUL template fidelity:** Rendered PumplAI SOUL.md is semantically identical to the v1.0 hardcoded SOUL.md — failing this means existing PumplAI workflow is broken
- [ ] **Snapshot default branch:** Initialize a test project with a `master`-default repo; run `capture_semantic_snapshot()` and verify the diff is non-empty and references `master`, not `main`
- [ ] **Dashboard project switch:** Switch projects in the occc UI; verify the task list, container list, and metrics all update to reflect only the selected project within one SSE polling cycle
- [ ] **L3 pool isolation:** Start tasks for two projects simultaneously; verify Project B's tasks do not queue behind Project A's 600-second code task if pools are configured per-project
- [ ] **`openclaw.json` agent list not polluted:** After `openclaw project init` for a new project, verify `openclaw.json:agents.list` has not been modified
- [ ] **No in-flight task corruption:** Run `openclaw project switch` while an L3 task is executing; verify the running task completes and writes to the correct original project's state file

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Cross-project state file contamination (tasks from both projects in one JSON) | MEDIUM | Stop all L3 containers; partition `tasks` dict by workspace path in task metadata; write two separate state files; restart monitoring |
| Container name collision mid-flight | LOW | `docker rm -f openclaw-l3-{colliding_id}`; fix task ID generation to include project prefix; the pool's retry logic will re-spawn under a new unique name |
| `active_project` switched while L3 tasks in flight | LOW-MEDIUM | Set `OPENCLAW_PROJECT` env var to the original project ID; re-run affected state updates manually via `JarvisState.update_task()`; review snapshots directory for misrouted diff files |
| SOUL template breaks PumplAI identity | HIGH | Revert template render to hardcoded SOUL.md; treat templating as non-functional until golden baseline test passes; do not ship templating until PumplAI E2E workflow validates cleanly |
| Dashboard cache stale after project switch | LOW | Restart Next.js dev server; in production, add project ID to cache key — this requires a code fix, not an operational fix |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Single global state file | Phase 1: Config Decoupling | Two simultaneous projects produce two distinct state file paths; no task ID appears in both files |
| Container name collision | Phase 1 (label schema) + Phase 2 (name prefix) | `docker ps` shows distinct name prefixes per project; no 409 Conflict errors in spawn logs during concurrent test |
| Shared pool semaphore starvation | Phase 2: Multi-Project Runtime | Project B tasks start within 5 seconds of spawn call even while Project A has 3 active tasks running |
| `active_project` global mutation | Phase 1: Config Decoupling | `openclaw project switch` in one terminal does not affect in-flight tasks spawned by another terminal |
| SOUL template fidelity break | Phase 1: Config Decoupling | Golden baseline diff is empty for PumplAI SOUL render; no unsubstituted `{{` tokens in output |
| Dashboard SSE single-file binding | Phase 4: Dashboard Project Switcher | Switching projects in UI updates all three panels (tasks, containers, metrics) within one polling cycle |
| Snapshot hardcoded `main` | Phase 2: Multi-Project Runtime | Non-main-branch project generates a non-empty diff snapshot with correct branch references |
| Agent list contamination in `openclaw.json` | Phase 1: Config Decoupling | New project init does not modify `openclaw.json`; dashboard hierarchy driven by `project.json` for active project |

---

## Sources

- Direct codebase inspection: `orchestration/state_engine.py`, `orchestration/project_config.py`, `orchestration/config.py`, `orchestration/snapshot.py`, `skills/spawn_specialist/spawn.py`, `skills/spawn_specialist/pool.py`, `workspace/occc/src/app/api/swarm/route.ts`, `workspace/occc/src/lib/jarvis.ts`, `agents/pumplai_pm/agent/SOUL.md`, `projects/pumplai/project.json`, `openclaw.json` — HIGH confidence
- Docker Compose container naming conflicts: [orbstack/orbstack Issue #1488](https://github.com/orbstack/orbstack/issues/1488), [docker/compose Issue #5104 — container naming conflict on identical project folder names](https://github.com/docker/compose/issues/5104) — MEDIUM confidence
- Multi-tenant state isolation patterns: [Tenant Data Isolation: Patterns and Anti-Patterns](https://propelius.ai/blogs/tenant-data-isolation-patterns-and-anti-patterns) — MEDIUM confidence
- CLI global config mutation under concurrent sessions: [Claude Code Issue #23597 — per-project organization switching](https://github.com/anthropics/claude-code/issues/23597), [Gemini CLI Issue #4935 — workspace command for multi-project context switching](https://github.com/google-gemini/gemini-cli/issues/4935) — MEDIUM confidence (pattern is universal)
- fcntl advisory locking pitfalls under concurrent processes: [File locking — Wikipedia](https://en.wikipedia.org/wiki/File_locking), [Distributed Locking: A Practical Guide](https://www.architecture-weekly.com/p/distributed-locking-a-practical-guide) — HIGH confidence

---
*Pitfalls research for: Adding multi-project support to OpenClaw v1.1*
*Researched: 2026-02-23*
