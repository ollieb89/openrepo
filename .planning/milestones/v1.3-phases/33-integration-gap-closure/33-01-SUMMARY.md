---
phase: 33-integration-gap-closure
plan: "01"
subsystem: spawn-specialist / l3-container
tags: [memory, soul-injection, docker-networking, url-rewrite, entrypoint]
dependency_graph:
  requires: [29-01, 28-01]
  provides: [MEM-04, RET-02]
  affects: [spawn_l3_specialist, entrypoint.sh, pre-spawn-soul-flow]
tech_stack:
  added: []
  patterns:
    - Docker DNS rewrite via regex substitution on localhost/127.0.0.1
    - Bash array expansion for safe multiline argument passing (SOUL_ARGS)
    - Persistent per-task files in project state dir instead of /tmp tempfiles
    - PIPESTATUS[0] for capturing pipe exit code accurately
key_files:
  created: []
  modified:
    - skills/spawn_specialist/spawn.py
    - docker/l3-specialist/entrypoint.sh
    - tests/test_spawn_memory.py
decisions:
  - "Docker DNS hostname 'openclaw-memory' used for MEMU_API_URL rewrite — matches container service name convention"
  - "SOUL_ARGS bash array chosen over string interpolation for safe multiline --system-prompt quoting"
  - "Persistent SOUL path workspace/.openclaw/<proj>/soul-<task>.md survives container exit for debug inspection"
  - "PIPESTATUS[0] replaces $? to correctly capture CLI exit code from piped tee invocation"
  - "Empty SOUL_ARGS array expands to nothing — safe no-op when no SOUL file mounted"
metrics:
  duration_seconds: 156
  tasks_completed: 3
  files_modified: 3
  completed_date: "2026-02-24"
---

# Phase 33 Plan 01: Integration Gap Closure — SOUL Injection and Container Networking Summary

**One-liner:** Fixed two dead integration seams: Docker DNS URL rewrite for memU connectivity and entrypoint SOUL_FILE reading for augmented SOUL delivery to L3 agents.

## What Was Built

### Task 1: spawn.py — URL rewrite, network join, persistent SOUL file

Three new functions added and wired into `spawn_l3_specialist()`:

**`_rewrite_memu_url_for_container(url, dns_hostname="openclaw-memory")`**
- Regex replaces `localhost` or `127.0.0.1` with `openclaw-memory` Docker DNS hostname
- Port and path preserved; non-localhost URLs pass through unchanged
- Called on `MEMU_API_URL` in container environment block

**`_ensure_openclaw_network(client, network_name="openclaw-net")`**
- Idempotent bridge network creation — `NotFound` → create, `APIError` → warning (non-blocking)
- Called immediately after `get_docker_client()` on every spawn

**`_write_soul_file(content, project_id, task_id, workspace_root)`**
- Writes to `workspace/.openclaw/<project_id>/soul-<task_id>.md`
- Creates parent dirs; file persists after container exit for debugging
- Replaces `_write_soul_tempfile` + `finally: unlink()` pattern on the spawn path

Container config additions:
- `"network": "openclaw-net"` — joins container to Docker bridge network
- `MEMU_API_URL` wrapped with `_rewrite_memu_url_for_container()`
- Variable renamed `soul_tempfile` → `soul_file` for clarity

`_write_soul_tempfile` retained with deprecation notice (existing tests import it).

### Task 2: entrypoint.sh — SOUL_FILE reading and runtime dispatch

Inserted between staging branch checkout (step 2) and CLI invocation (step 3):

```bash
SOUL_ARGS=()
if [[ -n "${SOUL_FILE:-}" && -f "${SOUL_FILE}" ]]; then
  SOUL_CONTENT=$(cat "${SOUL_FILE}")
  if [[ -n "${SOUL_CONTENT}" ]]; then
    case "${CLI_RUNTIME}" in
      claude-code|codex) SOUL_ARGS=(--system-prompt "$SOUL_CONTENT") ;;
      gemini-cli) echo "$SOUL_CONTENT" > /workspace/GEMINI.md ;;
      *) # WARNING: unknown runtime ;;
    esac
  fi
fi
```

CLI invocation updated:
- `"${CLI_RUNTIME}" "${SOUL_ARGS[@]}"` — array expansion, safe for multiline content
- `EXIT_CODE=${PIPESTATUS[0]}` — captures CLI exit code, not `tee` exit code
- Graceful degradation: missing/empty SOUL_FILE logs WARNING and continues

### Task 3: Unit tests for URL rewrite and persistent SOUL file

10 new tests in `tests/test_spawn_memory.py`:

**7 URL rewrite tests (MEM-04):**
- `test_rewrite_memu_url_localhost_to_docker_dns` — `http://localhost:18791` → `http://openclaw-memory:18791`
- `test_rewrite_memu_url_127_to_docker_dns` — `127.0.0.1` variant
- `test_rewrite_memu_url_preserves_path` — port and `/api/v1` path preserved
- `test_rewrite_memu_url_non_localhost_unchanged` — external hostname passes through
- `test_rewrite_memu_url_https_unchanged` — HTTPS external URL passes through
- `test_rewrite_memu_url_empty_returns_empty` — empty string → empty string
- `test_rewrite_memu_url_custom_hostname` — `dns_hostname="custom-host"` parameter

**3 persistent SOUL file tests (RET-02):**
- `test_write_soul_file_creates_at_project_state_dir` — exact path assertion
- `test_write_soul_file_creates_parent_dirs` — parent dir creation
- `test_write_soul_file_overwrites_existing` — idempotent write behavior

**Result:** 29/29 tests pass (19 existing + 10 new)

## Verification

All plan checks passed:

1. `python3 -m pytest tests/test_spawn_memory.py -v` — 29 passed
2. `bash -n docker/l3-specialist/entrypoint.sh` — syntax OK
3. `_rewrite_memu_url_for_container` exists in spawn.py and called in container_config environment
4. `"network": "openclaw-net"` present in container_config
5. `SOUL_FILE` handling present in entrypoint.sh
6. `SOUL_ARGS` runtime dispatch present in entrypoint.sh
7. No `soul_tempfile.unlink` in spawn.py — cleanup removed

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit  | Description                                           |
|------|---------|-------------------------------------------------------|
| 1    | 14843aa | feat(33-01): URL rewrite, network join, persistent SOUL file in spawn.py |
| 2    | 9968ed7 | feat(33-01): SOUL_FILE reading and runtime-specific CLI dispatch in entrypoint.sh |
| 3    | 77cdefe | test(33-01): add URL rewrite and persistent SOUL file unit tests |

## Self-Check: PASSED

Files verified:
- `skills/spawn_specialist/spawn.py` — FOUND (contains all required functions and wiring)
- `docker/l3-specialist/entrypoint.sh` — FOUND (SOUL_ARGS, case dispatch, PIPESTATUS)
- `tests/test_spawn_memory.py` — FOUND (29 tests pass)

Commits verified:
- 14843aa — FOUND
- 9968ed7 — FOUND
- 77cdefe — FOUND
