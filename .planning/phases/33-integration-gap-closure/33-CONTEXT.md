# Phase 33: Integration Gap Closure - Context

**Gathered:** 2026-02-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two broken integration points from the v1.3 milestone audit: (1) entrypoint.sh SOUL_FILE handling so augmented SOUL content reaches L3 agents, and (2) MEMU_API_URL container networking so L3 containers can reach the memU service. Verify and update MEM-01/MEM-03 requirement checkboxes. No new capabilities — wiring fixes only.

</domain>

<decisions>
## Implementation Decisions

### SOUL file handoff
- spawn.py writes the rendered SOUL to a mounted file: `workspace/.openclaw/<project>/soul-<task_id>.md`
- Container receives `SOUL_FILE` env var pointing to the mount path inside the container
- entrypoint.sh reads the file content and passes it to the CLI runtime via runtime-specific flags (e.g. `--system-prompt` for claude-code) — each supported runtime gets its native instruction flag
- SOUL files are kept after container exit for debugging — cleaned up with project removal, not per-task

### Container networking
- Read `memu_api_url` from `openclaw.json` (existing config field)
- spawn.py performs smart URL rewrite: detect `localhost` or `127.0.0.1` in the URL and replace with Docker DNS hostname (e.g. `memu-server`); non-localhost URLs passed through unchanged
- spawn.py auto-creates the `openclaw-net` Docker network if it doesn't exist
- L3 containers are joined to `openclaw-net` at spawn time for Docker DNS resolution

### Failure handling
- Memory retrieval failure: retry 2-3 times with short timeout, then proceed without memory context (graceful degradation)
- Verbose failure logging: log the full chain — what was attempted, what failed, what fallback was used. Include URLs, paths, error messages. These are infrastructure seams that are hard to debug remotely.

### Requirements audit
- Verify MEM-01 and MEM-03 via code inspection + flow tracing, confirmed by test
- Use partial notation if only partially satisfied (e.g. note what's done and what remains)
- Update REQUIREMENTS.md in a separate documentation commit after all fixes are verified
- Stay focused on MEM-01 and MEM-03 only — broader MEM-* sweep is out of scope

### Claude's Discretion
- Fallback behavior when SOUL_FILE is set but file doesn't exist or is empty (proceed vs fail)
- Docker DNS vs host.docker.internal networking approach
- Network join failure fallback strategy (host networking fallback vs fail)
- Retry count and timeout values for memory retrieval

</decisions>

<specifics>
## Specific Ideas

- The smart URL rewrite should be surgical: only swap the hostname portion, preserve port and path
- Runtime-specific flags mean entrypoint.sh needs a case/switch on the runtime type from L3 config
- SOUL file location follows existing per-project state conventions (alongside workspace-state.json and snapshots)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 33-integration-gap-closure*
*Context gathered: 2026-02-24*
