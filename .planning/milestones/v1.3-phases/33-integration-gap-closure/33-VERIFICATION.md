---
phase: 33-integration-gap-closure
verified: 2026-02-24T00:00:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification: []
---

# Phase 33: Integration Gap Closure Verification Report

**Phase Goal:** Fix the two broken integration points from audit — entrypoint.sh SOUL_FILE handling and MEMU_API_URL container networking — so the pre-spawn SOUL injection flow works end-to-end and L3 containers can reach memU
**Verified:** 2026-02-24
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | MEMU_API_URL injected into L3 containers uses Docker DNS hostname (openclaw-memory) instead of localhost | VERIFIED | `_rewrite_memu_url_for_container()` called in `container_config["environment"]["MEMU_API_URL"]` at line 435 of spawn.py; 7 passing URL rewrite tests |
| 2 | L3 containers are joined to openclaw-net at spawn time, enabling Docker DNS resolution | VERIFIED | `"network": "openclaw-net"` in container_config at line 442; `_ensure_openclaw_network(client)` called before container creation at line 379 |
| 3 | entrypoint.sh reads $SOUL_FILE and passes its content to the CLI runtime via runtime-specific flags | VERIFIED | SOUL_ARGS bash array populated from SOUL_FILE, dispatched per CLI_RUNTIME (claude-code/codex: --system-prompt, gemini-cli: GEMINI.md write); CLI invocation uses `"${SOUL_ARGS[@]}"` at line 78 of entrypoint.sh |
| 4 | SOUL files are written to workspace/.openclaw/<project>/soul-<task_id>.md and persist after container exit | VERIFIED | `_write_soul_file()` creates path at `workspace_root / ".openclaw" / project_id / f"soul-{task_id}.md"`; no finally/unlink block; 3 passing persistent path tests |
| 5 | Pre-spawn SOUL injection flow works end-to-end: spawn.py retrieves → renders SOUL → mounts file → entrypoint reads → CLI receives augmented SOUL | VERIFIED | Full chain: `_retrieve_memories_sync()` → `_format_memory_context()` → `_build_augmented_soul()` → `_write_soul_file()` → volume mount at SOUL_CONTAINER_PATH → env var SOUL_FILE set → entrypoint.sh reads and dispatches |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/spawn_specialist/spawn.py` | URL rewrite, network join, persistent SOUL file path; contains `_rewrite_memu_url_for_container` | VERIFIED | All three functions present: `_rewrite_memu_url_for_container` (line 53), `_ensure_openclaw_network` (line 62), `_write_soul_file` (line 314); all wired into `spawn_l3_specialist()` |
| `docker/l3-specialist/entrypoint.sh` | SOUL_FILE reading and runtime-specific CLI dispatch; contains `SOUL_FILE` | VERIFIED | SOUL_ARGS array initialized line 45; case/switch on CLI_RUNTIME lines 50-64; `"${SOUL_ARGS[@]}"` in CLI invocation line 78; syntax check passes |
| `tests/test_spawn_memory.py` | Unit tests for URL rewrite function; contains `test_rewrite_memu_url` | VERIFIED | 7 URL rewrite tests + 3 persistent SOUL file tests present; all 29 tests in file pass (0.09s) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `skills/spawn_specialist/spawn.py` | `docker/l3-specialist/entrypoint.sh` | SOUL_FILE env var + bind mount + MEMU_API_URL env var | VERIFIED | `container_config["environment"]["SOUL_FILE"] = SOUL_CONTAINER_PATH` (line 526); bind mount added to volumes dict (lines 522-525); MEMU_API_URL set with rewritten URL (line 435) |
| `skills/spawn_specialist/spawn.py` | openclaw-net Docker network | `container_config["network"] = "openclaw-net"` | VERIFIED | `"network": "openclaw-net"` at line 442; `_ensure_openclaw_network(client)` called at line 379 before container creation |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| MEM-04 | 33-01-PLAN.md, 33-02-PLAN.md | MEMU_API_URL environment variable is injected into L3 containers at spawn time | SATISFIED | `_rewrite_memu_url_for_container()` rewrites localhost to `openclaw-memory` DNS; called in container environment block; `[x]` in REQUIREMENTS.md; `Complete` in traceability table |
| RET-02 | 33-01-PLAN.md, 33-02-PLAN.md | Retrieved memories injected into SOUL template with memory context section | SATISFIED | `_write_soul_file()` writes augmented SOUL to persistent path; entrypoint.sh reads and passes to CLI via --system-prompt; `[x]` in REQUIREMENTS.md; `Complete` in traceability table |

**Additional requirements updated (plan 02):**

| Requirement | Status in REQUIREMENTS.md | Evidence |
|-------------|--------------------------|---------|
| MEM-01 | `[x]` + Complete in traceability | Pre-existing implementation confirmed by `tests/test_pool_memorization.py` |
| MEM-03 | `[x]` + Complete in traceability | Pre-existing implementation confirmed by `tests/test_pool_memorization.py` |

No orphaned requirements — all four requirement IDs declared in plan frontmatter appear as `[x]` with `Complete` status in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `docker/l3-specialist/entrypoint.sh` | 75 | Comment "Placeholder: actual CLI invocation will depend on runtime" | Info | Comment is stale but harmless — the actual CLI invocation below it is fully implemented |

No blockers or warnings found.

### Human Verification Required

None. All success criteria are mechanically verifiable via code inspection, grep patterns, and test execution.

### Gaps Summary

No gaps. All five observable truths verified, all artifacts present and substantive, all key links wired.

**Test results:** 29/29 tests pass in `tests/test_spawn_memory.py` (0.09s). Bash syntax check on `entrypoint.sh` passes.

**End-to-end flow confirmed:**
1. `spawn_l3_specialist()` calls `_ensure_openclaw_network(client)` — network exists before container starts
2. `_rewrite_memu_url_for_container()` converts `http://localhost:18791` → `http://openclaw-memory:18791` in the container environment
3. `_write_soul_file()` writes augmented SOUL to `project_root/.openclaw/<project_id>/soul-<task_id>.md` (no tempfile, no cleanup)
4. The soul file is bind-mounted read-only at `/run/openclaw/soul.md` inside the container
5. `SOUL_FILE=/run/openclaw/soul.md` injected as env var
6. `entrypoint.sh` reads `$SOUL_FILE`, builds `SOUL_ARGS=(--system-prompt "$SOUL_CONTENT")` for claude-code/codex
7. CLI invoked as `"${CLI_RUNTIME}" "${SOUL_ARGS[@]}" --task "${TASK_DESCRIPTION}"`

---

_Verified: 2026-02-24_
_Verifier: Claude (gsd-verifier)_
