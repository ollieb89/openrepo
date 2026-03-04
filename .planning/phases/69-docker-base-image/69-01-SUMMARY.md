---
phase: 69-docker-base-image
plan: 01
subsystem: infra
tags: [docker, dockerfile, base-image, debian, bookworm-slim, l3-specialist]

# Dependency graph
requires: []
provides:
  - "docker/base/Dockerfile: shared openclaw-base:bookworm-slim image (debian:bookworm-slim + tools + sandbox UID 1000)"
  - "docker-base Makefile target for building openclaw-base"
  - "L3 Dockerfile rebased on openclaw-base instead of openclaw-sandbox submodule image"
affects: [docker-l3-builds, spawn-infrastructure, any-phase-adding-docker-containers]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared base image pattern: openclaw-base:bookworm-slim as common ancestor for all OpenClaw containers"
    - "docker-base Makefile target as prerequisite for docker-l3 via make dependency chain"

key-files:
  created:
    - docker/base/Dockerfile
  modified:
    - docker/l3-specialist/Dockerfile
    - Makefile

key-decisions:
  - "No CMD in base image — consumers (L3) define their own entrypoint; base image stays minimal"
  - "Explicit --uid 1000 on useradd in base for clarity (was implicit in original Dockerfile.sandbox)"
  - "Old docker-sandbox-base and docker-sandbox-common Makefile targets retained — serve submodule's own purposes"
  - "docker-all updated to include docker-base alongside existing sandbox targets"

patterns-established:
  - "Base image pattern: debian:bookworm-slim + common tools + sandbox UID 1000, no CMD"
  - "Makefile dependency chain: docker-l3 depends on docker-base (not docker-sandbox-base)"

requirements-completed: [DOCK-01]

# Metrics
duration: 1min
completed: 2026-03-04
---

# Phase 69 Plan 01: Docker Base Image Summary

**New shared `openclaw-base:bookworm-slim` Docker image extracted from submodule Dockerfile.sandbox, with L3 Dockerfile and Makefile updated to use it as the canonical base layer**

## Performance

- **Duration:** ~1 min (automated, all cached layers)
- **Started:** 2026-03-04T19:55:55Z
- **Completed:** 2026-03-04T19:57:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Created `docker/base/Dockerfile` derived from `openclaw/Dockerfile.sandbox` with explicit UID 1000 and no CMD (consumers set their own entrypoint)
- Added `docker-base` Makefile target; `docker-l3` now depends on `docker-base` instead of `docker-sandbox-base`
- Rebased `docker/l3-specialist/Dockerfile` from `openclaw-sandbox:bookworm-slim` to `openclaw-base:bookworm-slim`
- All three success criteria verified: base builds, L3 FROM uses openclaw-base, `make docker-l3` succeeds end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Create openclaw-base Dockerfile and update Makefile** - `066c809` (feat)
2. **Task 2: Rebase L3 Dockerfile on openclaw-base** - `4773ee5` (feat)

**Plan metadata:** (docs commit — pending)

## Files Created/Modified

- `docker/base/Dockerfile` - Shared openclaw-base image: debian:bookworm-slim + bash/curl/git/jq/python3/ripgrep + sandbox UID 1000
- `docker/l3-specialist/Dockerfile` - Updated ARG BASE_IMAGE default and openclaw.base label to reference openclaw-base:bookworm-slim
- `Makefile` - Added docker-base target, updated docker-l3 dependency and docker-all; retained old sandbox targets

## Decisions Made

- No `CMD` in base image — base images should not define a default command; L3 defines its own `ENTRYPOINT`
- Kept `--uid 1000` explicit in `useradd` (was implicit in the submodule's original) for clarity
- Old `docker-sandbox-base` and `docker-sandbox-common` targets in Makefile kept intact per earlier user decision
- Added `docker-base` to `docker-all` so the full chain builds the new base plus legacy sandbox images

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 69 Plan 01 complete — DOCK-01 satisfied
- `openclaw-base:bookworm-slim` is now the canonical base for L3 containers
- Future container images (additional specialist types) can use `FROM openclaw-base:bookworm-slim` without depending on the openclaw submodule

---
*Phase: 69-docker-base-image*
*Completed: 2026-03-04*
