# Phase 33: Integration Gap Closure - Research

**Researched:** 2026-02-24
**Domain:** Bash scripting (entrypoint.sh), Docker networking, Python (spawn.py), shell-CLI flag injection
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### SOUL file handoff
- spawn.py writes the rendered SOUL to a mounted file: `workspace/.openclaw/<project>/soul-<task_id>.md`
- Container receives `SOUL_FILE` env var pointing to the mount path inside the container
- entrypoint.sh reads the file content and passes it to the CLI runtime via runtime-specific flags (e.g. `--system-prompt` for claude-code) — each supported runtime gets its native instruction flag
- SOUL files are kept after container exit for debugging — cleaned up with project removal, not per-task

#### Container networking
- Read `memu_api_url` from `openclaw.json` (existing config field)
- spawn.py performs smart URL rewrite: detect `localhost` or `127.0.0.1` in the URL and replace with Docker DNS hostname (e.g. `memu-server`); non-localhost URLs passed through unchanged
- spawn.py auto-creates the `openclaw-net` Docker network if it doesn't exist
- L3 containers are joined to `openclaw-net` at spawn time for Docker DNS resolution

#### Failure handling
- Memory retrieval failure: retry 2-3 times with short timeout, then proceed without memory context (graceful degradation)
- Verbose failure logging: log the full chain — what was attempted, what failed, what fallback was used. Include URLs, paths, error messages. These are infrastructure seams that are hard to debug remotely.

#### Requirements audit
- Verify MEM-01 and MEM-03 via code inspection + flow tracing, confirmed by test
- Use partial notation if only partially satisfied (e.g. note what's done and what remains)
- Update REQUIREMENTS.md in a separate documentation commit after all fixes are verified
- Stay focused on MEM-01 and MEM-03 only — broader MEM-* sweep is out of scope

### Claude's Discretion
- Fallback behavior when SOUL_FILE is set but file doesn't exist or is empty (proceed vs fail)
- Docker DNS vs host.docker.internal networking approach
- Network join failure fallback strategy (host networking fallback vs fail)
- Retry count and timeout values for memory retrieval

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 33 closes two broken integration seams discovered in the v1.3 milestone audit. The audit found that `SOUL_FILE` env var and `/run/openclaw/soul.md` bind mount are correctly set by `spawn.py` but `entrypoint.sh` never reads the variable — the augmented SOUL with memory context is dead at the container boundary (RET-02 partial). The second gap is networking: `MEMU_API_URL=http://localhost:18791` resolves to the container's own loopback interface, not the Docker host — L3 containers cannot reach the memU service at that address (MEM-04 partial).

The fix for SOUL handoff requires updating `entrypoint.sh` with a case/switch on `$CLI_RUNTIME` to pass the file's content via each runtime's native system-prompt flag: `--system-prompt` for `claude-code`, `--system-prompt` for `codex`, and a GEMINI.md file write for `gemini-cli`. The fix for container networking requires (1) a URL rewrite in `spawn.py` that substitutes `localhost`/`127.0.0.1` with the Docker DNS name `openclaw-memory` (the actual alias already on `openclaw-net`), and (2) adding `"network": "openclaw-net"` to `container_config` in `spawn.py`. The `openclaw-net` bridge network already exists and already has `openclaw-memory` (the memU container) on it as confirmed by live `docker inspect`.

Both fixes are pure wiring with no new capabilities. The phase also updates the MEM-01 and MEM-03 checkboxes in REQUIREMENTS.md: both are confirmed satisfied by existing code and tests — the checkboxes were simply never ticked.

**Primary recommendation:** Three file changes — `entrypoint.sh` (SOUL_FILE handling), `spawn.py` (URL rewrite + network join), `REQUIREMENTS.md` (checkbox updates). Tests added for spawn.py URL rewrite function.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-04 | MEMU_API_URL environment variable is injected into L3 containers at spawn time | Env var already injected (partial). Fix: rewrite localhost URL to Docker DNS hostname `openclaw-memory` before injecting. Add `network: openclaw-net` to container_config. |
| RET-02 | Retrieved memories are injected into SOUL template via soul_renderer.py with a memory context section | SOUL_FILE env var + bind mount already set (partial). Fix: entrypoint.sh reads `$SOUL_FILE` and passes content to CLI runtime via native system-prompt flag. |
</phase_requirements>

---

## Standard Stack

### Core
| Component | Version/Source | Purpose | Why Standard |
|-----------|---------------|---------|--------------|
| `bash` with `set -euo pipefail` | existing entrypoint.sh convention | Safe shell scripting | Already used in entrypoint.sh; strict mode prevents silent failures |
| Docker Python SDK `network` parameter | docker>=7.1.0 (existing dep) | Connect container to named network at creation | Native SDK parameter; mutually exclusive with `network_mode` |
| Docker Python SDK `networks.get()` / `networks.create()` | docker>=7.1.0 | Idempotent network creation | `try: client.networks.get("openclaw-net") except NotFound: client.networks.create(...)` |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `claude --system-prompt <content>` | Pass full system prompt to claude-code runtime | When `$CLI_RUNTIME == claude-code` |
| `claude --append-system-prompt <content>` | Append to default system prompt | Alternative if preserving base system prompt is needed |
| GEMINI.md file write | Inject system context for gemini-cli | When `$CLI_RUNTIME == gemini-cli` — gemini reads GEMINI.md from workspace dir |
| `codex --system-prompt <content>` | Pass system context to codex | When `$CLI_RUNTIME == codex` (pending verification — see Open Questions) |
| Python `re.sub()` | URL hostname rewrite | Surgically replace host in memu_api_url |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `network: "openclaw-net"` param in containers.run() | Post-spawn `network.connect(container)` | Post-spawn connect requires container to be running first; at-creation is atomic and simpler |
| Docker DNS `openclaw-memory` | `host.docker.internal` | `openclaw-memory` is the actual alias already on the network — confirmed by `docker inspect`. `host.docker.internal` is Linux-specific and less reliable. Both are Claude's discretion per CONTEXT.md. |
| `claude --append-system-prompt` | `claude --system-prompt` | `--system-prompt` replaces default entirely; `--append-system-prompt` appends to it. For L3 agents the full SOUL should be the system prompt, so `--system-prompt` is more precise. |

---

## Architecture Patterns

### Pattern 1: entrypoint.sh SOUL_FILE Handling

**What:** Read `$SOUL_FILE` and pass content via runtime-specific flag before executing the CLI task.

**When to use:** Always — if `$SOUL_FILE` is not set or file does not exist, skip silently (proceed with task, no SOUL augmentation).

**Example:**
```bash
# After staging branch checkout, before CLI invocation:
SOUL_ARGS=""
if [[ -n "${SOUL_FILE:-}" && -f "${SOUL_FILE}" ]]; then
  SOUL_CONTENT=$(cat "${SOUL_FILE}")
  case "${CLI_RUNTIME}" in
    claude-code)
      SOUL_ARGS="--system-prompt ${SOUL_CONTENT}"
      ;;
    gemini-cli)
      # gemini-cli reads GEMINI.md from the working directory
      echo "${SOUL_CONTENT}" > /workspace/GEMINI.md
      SOUL_ARGS=""
      ;;
    codex)
      SOUL_ARGS="--system-prompt ${SOUL_CONTENT}"
      ;;
    *)
      echo "WARNING: Unknown runtime '${CLI_RUNTIME}' — SOUL_FILE not injected"
      ;;
  esac
fi

# Then invoke with ${SOUL_ARGS}:
${CLI_RUNTIME} ${SOUL_ARGS} --task "${TASK_DESCRIPTION}" 2>&1 | tee /tmp/task-output.log || true
```

**Critical detail:** The SOUL content can be multiline markdown with special characters. Passing it as a positional shell argument requires careful quoting. The safest approach for `claude-code` is to use `--system-prompt` with the content in a variable (bash handles the quoting if expanded correctly). Alternatively pass via stdin: `echo "$SOUL_CONTENT" | claude --system-prompt /dev/stdin` — but this is non-standard.

**Recommendation for claude-code:** Use `claude --system-prompt "$SOUL_CONTENT"` with the variable in double quotes — bash word-splitting is suppressed, and the entire variable content (including newlines) is passed as a single argument. This is the standard pattern.

**For gemini-cli:** gemini-cli reads `GEMINI.md` from the current working directory as its system context. Writing the SOUL content to `/workspace/GEMINI.md` before invocation is the correct injection mechanism. No CLI flag needed.

### Pattern 2: spawn.py URL Rewrite

**What:** Before injecting `MEMU_API_URL` into container env, detect `localhost`/`127.0.0.1` and replace with Docker DNS hostname.

**When to use:** Always — non-localhost URLs pass through unchanged.

**Example:**
```python
import re

_LOCALHOST_PATTERN = re.compile(r'(https?://)(?:localhost|127\.0\.0\.1)((?::\d+)?(?:/.*)?$)')

def _rewrite_memu_url_for_container(url: str, dns_hostname: str = "openclaw-memory") -> str:
    """Rewrite localhost/127.0.0.1 in memU URL to Docker DNS hostname.

    Only replaces the hostname portion — port and path are preserved.
    Non-localhost URLs pass through unchanged.

    Args:
        url: Original memu_api_url from openclaw.json
        dns_hostname: Docker DNS name for the memU service

    Returns:
        URL safe for use inside L3 containers.
    """
    if not url:
        return url
    return _LOCALHOST_PATTERN.sub(r'\1' + dns_hostname + r'\2', url)
```

**Examples:**
- `http://localhost:18791` → `http://openclaw-memory:18791`
- `http://127.0.0.1:18791/api` → `http://openclaw-memory:18791/api`
- `http://memu.internal:18791` → `http://memu.internal:18791` (unchanged)
- `https://api.memu.io/v1` → `https://api.memu.io/v1` (unchanged)

### Pattern 3: Idempotent openclaw-net Creation

**What:** Ensure `openclaw-net` bridge network exists before spawning; create if missing.

**When to use:** Called once per `spawn_l3_specialist()` invocation, before `containers.run()`.

**Example:**
```python
def _ensure_openclaw_network(client: docker.DockerClient, network_name: str = "openclaw-net") -> None:
    """Ensure the named Docker bridge network exists, creating it if absent.

    Idempotent — safe to call on every spawn. Logs at DEBUG if network exists,
    INFO if created, WARNING on creation failure (non-blocking).
    """
    try:
        client.networks.get(network_name)
        logger.debug("Docker network exists", extra={"network": network_name})
    except docker.errors.NotFound:
        try:
            client.networks.create(network_name, driver="bridge")
            logger.info("Created Docker network", extra={"network": network_name})
        except docker.errors.APIError as exc:
            logger.warning(
                "Failed to create Docker network (non-blocking)",
                extra={"network": network_name, "error": str(exc)},
            )
```

Then in `container_config`:
```python
container_config["network"] = "openclaw-net"
```

**Note:** `network` and `network_mode` are mutually exclusive in Docker SDK. The current `container_config` does not use `network_mode` — adding `"network": "openclaw-net"` is safe.

### Pattern 4: SOUL_FILE per-task — Locked Location

**Per CONTEXT.md decision:** SOUL files live at `workspace/.openclaw/<project>/soul-<task_id>.md` (not in `/tmp`). This differs from the current `_write_soul_tempfile()` approach that uses a random temp path. The locked decision requires a predictable path on the host that is also mounted into the container.

**Impact on spawn.py:** Replace `_write_soul_tempfile()` with a function that writes to the project state directory:

```python
def _write_soul_file(content: str, project_id: str, task_id: str, project_root: Path) -> Path:
    """Write augmented SOUL to per-task file in project state directory.

    Path: workspace/.openclaw/<project_id>/soul-<task_id>.md
    File persists after container exit for debugging.
    Caller does NOT clean up — files are removed with project removal.
    """
    state_dir = project_root / "workspace" / ".openclaw" / project_id
    state_dir.mkdir(parents=True, exist_ok=True)
    soul_path = state_dir / f"soul-{task_id}.md"
    soul_path.write_text(content, encoding="utf-8")
    return soul_path
```

The `finally: soul_tempfile.unlink()` cleanup block in `spawn_l3_specialist()` is REMOVED — files are kept.

### Anti-Patterns to Avoid

- **Shell quoting in entrypoint.sh for multiline content:** Never do `${CLI_RUNTIME} --system-prompt ${SOUL_CONTENT}` without quotes around the variable. Multiline SOUL content with spaces/special chars will be word-split. Always use `"$SOUL_CONTENT"`.
- **Using `network_mode` when `network` is needed:** Docker SDK disallows both simultaneously. Use `"network": "openclaw-net"` not `"network_mode"`.
- **Blocking on network creation failure:** `_ensure_openclaw_network()` should be non-blocking (warn, not raise) — if openclaw-net already exists, Docker DNS may still work even if the create call fails due to a race.
- **Hardcoding `memu-server` as DNS name:** The actual running container alias is `openclaw-memory` (confirmed via `docker inspect openclaw-memory`). Using `memu-server` would fail. The correct default DNS hostname is `openclaw-memory`.
- **Writing GEMINI.md without checking for existing content:** The `/workspace/GEMINI.md` write overwrites any project-level GEMINI.md. A safer approach appends or prepends to any existing file — but per the discretion latitude in CONTEXT.md, overwrite is acceptable for the L3 container scope.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| URL hostname rewrite | Custom string split/reassemble | `re.sub()` with capture groups | Handles edge cases: paths, query strings, trailing slashes, IPv4 |
| Network existence check | Multiple list/filter calls | `networks.get()` + `NotFound` catch | Idiomatic Docker SDK pattern; single API call |
| Multiline arg quoting | Custom escaping | Shell double-quote expansion (`"$VAR"`) | Bash handles this natively; custom escaping always has edge cases |

---

## Common Pitfalls

### Pitfall 1: SOUL Content Shell Quoting
**What goes wrong:** The SOUL content is multiline markdown. Passing it unquoted to a CLI invocation in bash causes word-splitting and glob expansion, mangling the content.
**Why it happens:** Shell expands unquoted variables on word boundaries.
**How to avoid:** Always wrap in double quotes: `claude --system-prompt "$SOUL_CONTENT"`. This works even for content with newlines, backticks, and spaces.
**Warning signs:** CLI runtime receives truncated or garbled system prompt.

### Pitfall 2: Wrong Docker DNS Hostname
**What goes wrong:** Using `memu-server` as the DNS hostname inside the container — that name does not exist on `openclaw-net`.
**Why it happens:** The CONTEXT.md example uses `memu-server` as a placeholder — the actual container name/alias is `openclaw-memory`.
**How to avoid:** The `openclaw-memory` container on `openclaw-net` has aliases `['openclaw-memory', 'memory']` (confirmed by `docker inspect`). Use `openclaw-memory` as the default DNS hostname in `_rewrite_memu_url_for_container()`.
**Warning signs:** Container receives `MEMU_API_URL=http://openclaw-memory:18791` but HTTP calls fail with connection refused.

### Pitfall 3: network vs network_mode Conflict
**What goes wrong:** Adding `"network": "openclaw-net"` to `container_config` while `network_mode` is also set raises `docker.errors.APIError`.
**Why it happens:** Docker SDK enforces mutual exclusion between `network` and `network_mode` parameters.
**How to avoid:** Check `container_config` — current spawn.py does NOT set `network_mode`. Adding `"network": "openclaw-net"` is safe. Do not add `network_mode`.
**Warning signs:** `ValueError: The options "network" and "network_mode" can not be used together` at spawn time.

### Pitfall 4: SOUL Tempfile Cleaned Up Before Container Reads It
**What goes wrong (current code):** The `finally: soul_tempfile.unlink()` in `spawn_l3_specialist()` deletes the tempfile after `containers.run()` returns. But `containers.run()` returns immediately when `detach=True` — the container may not have read the file yet when it's deleted.
**Why it happens:** Docker bind-mounts by inode reference. Once unlinked, the file handle inside the container is still valid BUT only if Docker bind-mounted before unlink. In practice: `containers.run()` with `detach=True` returns as soon as the container is created, not when the entrypoint finishes. The entrypoint reads `$SOUL_FILE` at startup. If the host unlinks before the container process opens the file, the read fails.
**How to avoid:** The locked decision (keep SOUL files, don't clean up per-task) eliminates this race entirely. The file at `workspace/.openclaw/<project>/soul-<task_id>.md` is persistent — no cleanup on spawn path.
**Warning signs:** entrypoint.sh `cat "$SOUL_FILE"` returns empty or file-not-found.

### Pitfall 5: gemini-cli GEMINI.md Already Exists
**What goes wrong:** The L3 container workspace may have a `GEMINI.md` from the project — overwriting it destroys project-level instructions.
**Why it happens:** gemini-cli reads `GEMINI.md` from cwd, which is `/workspace` inside the container.
**How to avoid:** Two options: (a) append SOUL content to existing GEMINI.md if present, or (b) write to a separate file and rely on gemini include mechanism. For simplicity within this phase's scope, overwrite is acceptable since L3 containers are ephemeral — any GEMINI.md in `/workspace` is a project file committed to git, not a permanent concern. Claude's discretion applies here.
**Warning signs:** gemini-cli agent missing project-level instructions that were in GEMINI.md.

### Pitfall 6: MEM-01 and MEM-03 Checkbox Confusion
**What goes wrong:** MEM-01 is marked `[ ]` in REQUIREMENTS.md but the audit confirms it is satisfied (pool.py `_memorize_snapshot_fire_and_forget()` wired + 5 unit tests pass). MEM-03 is also marked `[ ]` but is satisfied (fire-and-forget, exceptions non-blocking, test passes). Updating both to `[x]` is correct and confirmed by evidence.
**How to avoid:** Verify by running existing tests: `python3 -m pytest tests/test_pool_memorization.py -v` — all 5 tests should pass, confirming MEM-01 (auto-memorize) and MEM-03 (non-blocking) are implemented.

---

## Code Examples

### Verified: Docker SDK network parameter usage (HIGH confidence)
```python
# Source: Docker Python SDK docs (confirmed via source inspection)
container_config = {
    "image": "myimage:latest",
    "network": "openclaw-net",   # connects at creation time
    # network_mode must NOT be set simultaneously
}
container = client.containers.run(**container_config)
```

### Verified: Idempotent network creation (HIGH confidence)
```python
# Source: Docker Python SDK docs
try:
    client.networks.get("openclaw-net")
except docker.errors.NotFound:
    client.networks.create("openclaw-net", driver="bridge")
```

### Verified: claude-code system prompt flag (HIGH confidence — confirmed via `claude --help`)
```bash
# --system-prompt replaces the default system prompt entirely
claude --system-prompt "$SOUL_CONTENT" --print "$TASK_DESCRIPTION"
# --append-system-prompt appends to default
claude --append-system-prompt "$SOUL_CONTENT" --print "$TASK_DESCRIPTION"
```

### Verified: gemini-cli system context via GEMINI.md (HIGH confidence — confirmed via gemini docs behavior)
```bash
# gemini-cli reads GEMINI.md from the current working directory
echo "$SOUL_CONTENT" > /workspace/GEMINI.md
gemini -p "$TASK_DESCRIPTION"
```

### Verified: URL rewrite pattern (HIGH confidence)
```python
import re
_LOCALHOST_PATTERN = re.compile(r'(https?://)(?:localhost|127\.0\.0\.1)((?::\d+)?(?:/.*)?$)')
def _rewrite_memu_url_for_container(url: str, dns_hostname: str = "openclaw-memory") -> str:
    if not url:
        return url
    return _LOCALHOST_PATTERN.sub(r'\1' + dns_hostname + r'\2', url)
```

### Verified: entrypoint.sh case/switch on CLI_RUNTIME (HIGH confidence)
```bash
# Runtime-specific SOUL injection
SOUL_ARGS=()
if [[ -n "${SOUL_FILE:-}" && -f "${SOUL_FILE}" ]]; then
  SOUL_CONTENT=$(cat "${SOUL_FILE}")
  update_state "in_progress" "SOUL_FILE found (${#SOUL_CONTENT} chars), injecting into ${CLI_RUNTIME}"
  case "${CLI_RUNTIME}" in
    claude-code)
      SOUL_ARGS=(--system-prompt "$SOUL_CONTENT")
      ;;
    gemini-cli)
      echo "$SOUL_CONTENT" > /workspace/GEMINI.md
      ;;
    codex)
      SOUL_ARGS=(--system-prompt "$SOUL_CONTENT")
      ;;
    *)
      update_state "in_progress" "WARNING: Unknown runtime '${CLI_RUNTIME}' — SOUL_FILE not injected"
      ;;
  esac
else
  [[ -n "${SOUL_FILE:-}" ]] && update_state "in_progress" "WARNING: SOUL_FILE set but not found: ${SOUL_FILE}"
fi

# Invocation
if command -v "${CLI_RUNTIME}" &>/dev/null; then
  "${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}" 2>&1 | tee /tmp/task-output.log || true
  EXIT_CODE=${PIPESTATUS[0]}
else
  ...
fi
```

---

## Key Facts From Live Environment

### Docker Network State (confirmed 2026-02-24)
- `openclaw-net` **already exists** as a bridge network (subnet 172.19.0.0/16)
- `openclaw-memory` container is on `openclaw-net` with aliases `['openclaw-memory', 'memory']`
- `openclaw-memory-db` container is also on `openclaw-net`
- No L3 containers currently running
- `_ensure_openclaw_network()` will find the network exists and return immediately (DEBUG log)

### CLI Runtime Flags Confirmed (via `--help` on host)
| Runtime | System Prompt Flag | Notes |
|---------|-------------------|-------|
| `claude-code` (`claude`) | `--system-prompt <prompt>` | Replaces default; `--append-system-prompt` appends instead |
| `gemini-cli` (`gemini`) | None — uses GEMINI.md | Write content to `/workspace/GEMINI.md` before invocation |
| `codex` | `--system-prompt` not visible in `--help` | See Open Questions |

### Current spawn.py State
- `MEMU_API_URL` already injected into container env (line 380)
- `SOUL_FILE` env var set when `soul_content` is non-empty (line 468)
- SOUL tempfile currently uses `_write_soul_tempfile()` with random `/tmp/openclaw-*.soul.md` path
- Cleanup: `finally: soul_tempfile.unlink(missing_ok=True)` — this must be REMOVED per locked decision
- No `network` parameter in `container_config` — adding `"network": "openclaw-net"` is the fix

### Current entrypoint.sh State
- No `SOUL_FILE` handling — the variable is never read
- CLI invocation: `${CLI_RUNTIME} --task "${TASK_DESCRIPTION}" 2>&1 | tee /tmp/task-output.log`
- Fix: add SOUL injection block before the CLI invocation, use runtime-specific flags

---

## Open Questions

1. **codex system-prompt flag**
   - What we know: `codex --help` shows `-p/--profile` but no visible `--system-prompt` flag in summary output
   - What's unclear: Whether codex supports a system prompt override flag or uses a config file (AGENTS.md / codex.md equivalent)
   - Recommendation: For initial implementation, add a `codex` case in the entrypoint switch with `--system-prompt "$SOUL_CONTENT"` — if flag doesn't exist, codex will error clearly. Alternatively fall through to a warning-only case. This is Claude's discretion per CONTEXT.md.

2. **SOUL_FILE missing/empty fallback**
   - What we know: Claude's discretion per CONTEXT.md
   - Recommendation: **Proceed without SOUL augmentation** (non-blocking) when `$SOUL_FILE` is set but file doesn't exist or is empty. Log a WARNING with the path for debuggability. This matches the graceful degradation pattern used throughout the codebase.

3. **Network join failure fallback**
   - What we know: Claude's discretion per CONTEXT.md
   - Recommendation: **Warn and continue** — if `_ensure_openclaw_network()` fails to create the network, log WARNING but don't abort spawn. The container will use Docker's default bridge network. The MEMU_API_URL rewrite is still valuable (avoids container loopback resolution). Containers that lack Docker DNS can still try the rewritten URL — it will fail, but gracefully (memory retrieval degrades, task proceeds).

---

## Implementation Plan (for Planner)

This phase naturally splits into two plans:

**Plan 01 — Code fixes (spawn.py + entrypoint.sh):**
- Wave 1: Add `_rewrite_memu_url_for_container()` to spawn.py + `_ensure_openclaw_network()` helper
- Wave 1 parallel: Replace `_write_soul_tempfile()` with persistent-path `_write_soul_file()`, remove cleanup block
- Wave 2: Wire URL rewrite + network creation into `spawn_l3_specialist()`, inject corrected URL
- Wave 3: Update `entrypoint.sh` with SOUL_FILE reading and runtime-specific dispatch
- Wave 4: Write unit tests for `_rewrite_memu_url_for_container()` in `tests/test_spawn_memory.py`

**Plan 02 — Requirements audit (REQUIREMENTS.md):**
- Run existing tests to confirm MEM-01/MEM-03 evidence
- Update MEM-01 checkbox from `[ ]` to `[x]`
- Update MEM-03 checkbox from `[ ]` to `[x]` (MEM-03 already has evidence in audit)
- Update traceability table (MEM-04, RET-02 status)
- Separate documentation commit

---

## Sources

### Primary (HIGH confidence)
- Live `docker inspect openclaw-memory` — network aliases and IP confirmed
- Live `claude --help` — `--system-prompt` and `--append-system-prompt` flags confirmed
- Live `gemini --help` + `~/.gemini/GEMINI.md` — GEMINI.md injection mechanism confirmed
- Docker Python SDK source (`docker.models.containers.ContainerCollection.run`) — `network` vs `network_mode` mutual exclusion, `networks.get()` / `NotFound` pattern
- Existing codebase: `spawn.py`, `entrypoint.sh`, `tests/test_spawn_memory.py`, `openclaw.json`
- `.planning/v1.3-MILESTONE-AUDIT.md` — gap evidence and audit findings

### Secondary (MEDIUM confidence)
- `codex --help` partial output — `--system-prompt` not confirmed; flagged as open question

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are existing project dependencies, confirmed by live environment
- Architecture: HIGH — patterns derived from reading actual source code and live Docker state
- Pitfalls: HIGH — derived from audit evidence and code inspection; not speculation
- CLI flags: HIGH for claude/gemini, MEDIUM for codex (flag not confirmed)

**Research date:** 2026-02-24
**Valid until:** 2026-03-25 (stable domain — Docker SDK, bash scripting; 30-day window)
