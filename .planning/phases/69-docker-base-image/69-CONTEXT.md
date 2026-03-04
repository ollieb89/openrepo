# Phase 69: Docker Base Image - Context

**Gathered:** 2026-03-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a shared `openclaw-base:bookworm-slim` image in `docker/base/` and rebase the L3 Dockerfile on it. This reduces Dockerfile duplication and standardizes the base layer across OpenClaw containers. Scope is limited to the base image and L3 rebase — no new container types, no CI/CD pipeline changes.

</domain>

<decisions>
## Implementation Decisions

### Base image contents
- `openclaw-base` should contain the common packages already proven in the sandbox base: bash, ca-certificates, curl, git, jq, python3, ripgrep
- Non-root user setup (UID 1000) belongs in the base image — all OpenClaw containers run non-root
- `DEBIAN_FRONTEND=noninteractive` and apt cleanup (`rm -rf /var/lib/apt/lists/*`) in base
- No Python pip packages in base — those are layer-specific (L3 adds jsonschema, memory adds its own stack)

### Relationship to sandbox submodule
- `docker/base/Dockerfile` is a standalone file in openrepo (not dependent on the openclaw submodule)
- It replaces the dependency on `openclaw/Dockerfile.sandbox` for the L3 build chain
- Makefile targets updated: `docker-l3` depends on new `docker-base` target instead of `docker-sandbox-base`
- Old sandbox targets (`docker-sandbox-base`, `docker-sandbox-common`) remain for now — they serve the submodule's own purposes

### L3 Dockerfile rebase
- L3 Dockerfile changes `FROM openclaw-sandbox:bookworm-slim` → `FROM openclaw-base:bookworm-slim`
- L3-specific layers stay as-is: pip install jsonschema, user rename to l3worker, entrypoint, healthcheck
- Labels updated to reference `openclaw-base:bookworm-slim`

### Image naming & tagging
- Tag: `openclaw-base:bookworm-slim` (matches success criteria exactly)
- No version tags or registry push for now — local builds only
- Multi-arch not needed — development/single-host deployment

### Memory Dockerfile
- Stays independent (`python:3.13-slim-bookworm`) — it needs Rust toolchain, Postgres libs, and a completely different package set
- No value in sharing a base with openclaw-base for this service

### Claude's Discretion
- Exact order of RUN directives in the base Dockerfile
- Whether to add LABEL metadata to the base image
- Dockerfile best practices (layer caching optimization)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The success criteria are fully prescriptive:
1. `docker build -t openclaw-base:bookworm-slim docker/base/` succeeds
2. L3 Dockerfile uses `FROM openclaw-base:bookworm-slim`
3. `make docker-l3` builds successfully

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `openclaw/Dockerfile.sandbox`: Current base image definition — contents to be extracted into `docker/base/Dockerfile`
- `docker/l3-specialist/Dockerfile`: L3 layer that needs FROM line update
- `docker/l3-specialist/entrypoint.sh`: L3 entrypoint — unchanged by this phase

### Established Patterns
- Makefile dependency chain: `docker-sandbox-base` → `docker-l3` (will become `docker-base` → `docker-l3`)
- Non-root user at UID 1000 with `--no-new-privileges` and `cap_drop ALL` at container spawn time
- Build context is the subdirectory (e.g., `docker build ... docker/l3-specialist/`)

### Integration Points
- `Makefile`: New `docker-base` target, update `docker-l3` dependency
- `docker/l3-specialist/Dockerfile`: FROM line and base label update
- `skills/spawn/spawn.py`: References image name — verify it uses the L3 image name (not the base)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 69-docker-base-image*
*Context gathered: 2026-03-04*
