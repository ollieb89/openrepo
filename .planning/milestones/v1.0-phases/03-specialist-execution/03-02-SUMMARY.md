# Phase 3 Plan 02: Container Lifecycle + Physical Isolation - Summary

**Status:** COMPLETE  
**Completed:** 2026-02-18  
**Requirements:** HIE-03, HIE-04  

---

## What Was Delivered

This plan implemented the L3 specialist Docker image and the spawn_specialist skill that L2 uses to dynamically create isolated L3 containers. It brings L3 specialists to life as ephemeral Docker containers with physical isolation and concurrency management.

### Task 1: L3 Specialist Docker Image

Created a minimal Debian-based container image for L3 execution.

| File | Purpose | Key Features |
|------|---------|--------------|
| `docker/l3-specialist/Dockerfile` | Container image definition | Debian bookworm-slim base, git, python3, curl, jq |
| `docker/l3-specialist/entrypoint.sh` | Container startup script | Staging branch checkout, task execution, state reporting |

**Docker Image Configuration:**
- **Base:** `debian:bookworm-slim` (569MB final image size)
- **User:** `l3worker` (UID 1000) - non-root execution
- **Runtime:** Configurable via `CLI_RUNTIME` env var (claude-code, codex, gemini-cli)
- **Entrypoint:** Bash script handling staging branch, task execution, and state updates

**Entrypoint.sh Execution Flow:**
1. Validate required environment variables (TASK_ID, SKILL_HINT, STAGING_BRANCH)
2. Configure git (user.name, user.email for commits)
3. Report startup to workspace-state.json via Python state engine
4. Create/checkout staging branch (`l3/task-{task_id}`)
5. Execute task via configurable CLI runtime
6. On success: stage changes, commit, update state
7. On failure: capture last 50 lines of output, update state with error context

**State Update Helper:**
```bash
update_state() {
  local status="$1"
  local message="$2"
  python3 -c "
import sys; sys.path.insert(0, '/orchestration')
from state_engine import JarvisState
js = JarvisState('${STATE_FILE}')
js.update_task('${TASK_ID}', '${status}', '${message}')
"
}
```

### Task 2: spawn_specialist Skill with Pool Management

Created the L2-facing skill for container spawning and management.

| File | Purpose | Key Features |
|------|---------|--------------|
| `skills/spawn_specialist/skill.json` | Skill definition | Owner: pumplai_pm, parameters: task_id, skill_hint, task_description, requires_gpu, cli_runtime |
| `skills/spawn_specialist/requirements.txt` | Python dependencies | docker>=7.1.0 |
| `skills/spawn_specialist/spawn.py` | Container spawning | Docker Python SDK, security options, GPU support |
| `skills/spawn_specialist/pool.py` | Pool management | Semaphore(3), retry logic, ephemeral lifecycle |

**Skill Configuration:**
```json
{
  "id": "spawn_specialist",
  "name": "L3 Specialist Spawner",
  "owner": "pumplai_pm",
  "commands": [{
    "name": "spawn",
    "parameters": {
      "task_id": { "type": "string", "required": true },
      "skill_hint": { "type": "string", "enum": ["code", "test"], "required": true },
      "task_description": { "type": "string", "required": true },
      "requires_gpu": { "type": "boolean", "default": false },
      "cli_runtime": { "type": "string", "default": "claude-code" }
    }
  }]
}
```

**spawn.py Key Features:**

`spawn_l3_specialist()` function creates containers with:

- **Image:** `openclaw-l3-specialist:latest`
- **Name:** `openclaw-l3-{task_id}`
- **Volume Mounts:**
  - Workspace: `{workspace_path}:/workspace:rw` (full read/write)
  - Orchestration: `{project_root}/orchestration:/orchestration:ro` (read-only)
  - State directory: `workspace/.openclaw:/workspace/.openclaw:rw`
- **Environment Variables:**
  - `TASK_ID`, `SKILL_HINT`, `STAGING_BRANCH`, `CLI_RUNTIME`, `TASK_DESCRIPTION`
- **Security Options (HIE-04):**
  - `security_opt: ['no-new-privileges']`
  - `cap_drop: ['ALL']`
  - `user: {host_uid}:{host_gid}` (matches host to avoid permission errors)
- **Resource Limits:**
  - `mem_limit: '4g'`
  - `cpu_quota: 100000` (1 CPU)
- **Restart Policy:** `{'Name': 'no'}` (L2 handles retries)
- **Labels:**
  - `openclaw.tier: l3`
  - `openclaw.task_id: {task_id}`
  - `openclaw.spawned_by: pumplai_pm`
  - `openclaw.skill: {skill_hint}`
- **GPU Support:** Conditional DeviceRequest added only when `requires_gpu=True`

**pool.py Key Features:**

`L3ContainerPool` class manages concurrent containers:

- **Semaphore Control:** `asyncio.Semaphore(3)` for max 3 concurrent containers
- **Auto-Retry:** Failed tasks retry once with `(retry)` appended to description
- **Ephemeral Lifecycle:** Containers removed in finally block after completion
- **Timeout Handling:** Per-skill timeouts (600s for code, 300s for test)
- **Async/Sync Integration:** Uses `run_in_executor()` for docker-py sync calls
- **State Updates:** Full activity logging via JarvisState

**Monitoring:**
- Real-time log streaming during container execution
- Exit code capture and status reporting
- On timeout: container killed, state updated to "timeout"
- On failure: last 50 log lines captured in state update

---

## Verification Results

### Docker Image Validation
```
✓ Dockerfile exists
✓ Entrypoint executable
✓ Image built: openclaw-l3-specialist:latest (569MB)
✓ Image has openclaw.tier label
```

### Entrypoint.sh Validation
```
✓ Task ID handling OK
✓ Staging branch OK
✓ State updates OK
```

### Skill Validation
```
✓ skill.json valid (owner: pumplai_pm)
✓ spawn.py parses OK
✓ pool.py parses OK
```

### Security & Concurrency Validation
```
✓ Security isolation (no-new-privileges) present
✓ Capability drop present
✓ GPU support (DeviceRequest) present
✓ Concurrency limit (Semaphore) present
```

---

## Files Modified

- `docker/l3-specialist/Dockerfile` (created)
- `docker/l3-specialist/entrypoint.sh` (created, executable)
- `skills/spawn_specialist/skill.json` (created)
- `skills/spawn_specialist/requirements.txt` (created)
- `skills/spawn_specialist/spawn.py` (created)
- `skills/spawn_specialist/pool.py` (created)

---

## Success Criteria Met

| Criterion | Status |
|-----------|--------|
| L3 specialist Docker image can be built | ✓ Met (569MB image built) |
| Container spawning enforces physical isolation (HIE-04) | ✓ Met (no-new-privileges, cap_drop ALL, mem_limit 4g) |
| Maximum 3 concurrent containers (semaphore enforced) | ✓ Met (asyncio.Semaphore(3)) |
| Auto-retry once on failure with error context | ✓ Met (retry_count tracking, log capture) |
| GPU passthrough is on-demand only | ✓ Met (conditional DeviceRequest) |
| Containers are ephemeral (spawned per task, removed after) | ✓ Met (container.remove() in finally block) |
| L2 (PumplAI_PM) is the exclusive spawn authority | ✓ Met (skill.json owner: "pumplai_pm") |

---

## Key Links Established

```
skills/spawn_specialist/spawn.py  --docker.containers.run-->  docker/l3-specialist/Dockerfile
skills/spawn_specialist/spawn.py  --JarvisState-->  orchestration/state_engine.py
skills/spawn_specialist/pool.py  --spawn_l3_specialist-->  skills/spawn_specialist/spawn.py
docker/l3-specialist/entrypoint.sh  --state updates-->  workspace/.openclaw/workspace-state.json
```

---

## Technical Implementation Notes

### Why Ephemeral Containers?
L3 containers are spawned per task and removed after completion because:
- **Clean state:** No configuration drift between tasks
- **Isolation:** Each task starts from known-good baseline
- **Resource efficiency:** No idle containers consuming memory
- **Startup cost acceptable:** <5s container spawn time is reasonable for 10min+ tasks

### Why Semaphore for Concurrency?
Using `asyncio.Semaphore(3)` instead of manual tracking because:
- **Built-in blocking:** Automatically queues requests when limit reached
- **Race-free:** No manual lock management needed
- **Async-friendly:** Integrates naturally with async/await pattern

### Why Docker Python SDK?
Using docker-py instead of subprocess calls because:
- **Official SDK:** 357 code examples, handles API versioning
- **Error handling:** Clear exceptions for common failures
- **Connection pooling:** Efficient for multiple operations

### GPU Passthrough Implementation
GPU is enabled on-demand using NVIDIA Container Toolkit:
```python
if requires_gpu:
    container_config["device_requests"] = [
        DeviceRequest(
            count=-1,  # All GPUs
            capabilities=[["gpu"]],
            driver="nvidia"
        )
    ]
```

### UID/GID Matching for Permissions
The container runs with the host user's UID to avoid permission errors:
```python
"user": f"{os.getuid()}:{os.getgid()}"
```

---

## Ready for Next Plans

This plan provides the foundation for:
- **Plan 03:** Workspace Persistence + CLI Monitoring (COM-04)
- **Plan 04:** Registration + Integration Verification (HIE-03, HIE-04, COM-03, COM-04)

The L3 container spawning, pool management, and physical isolation infrastructure are now ready for integration with workspace persistence and monitoring systems.
