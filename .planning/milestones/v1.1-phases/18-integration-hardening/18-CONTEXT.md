# Phase 18: Integration Hardening - Context

**Gathered:** 2026-02-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix 4 cross-phase integration wiring issues identified by the v1.1 milestone audit: entrypoint branch detection, package exports, soul_renderer runtime trigger, and geriai project identity. Closes 2 broken E2E flows. No new features — strictly wiring fixes.

</domain>

<decisions>
## Implementation Decisions

### Soul auto-generation trigger
- Auto-generate SOUL.md during `initialize_workspace()` for new projects
- Also expose a CLI command (`openclaw soul generate <project>`) for manual regeneration
- `initialize_workspace()` skips if SOUL.md already exists — never overwrites
- CLI regenerate command requires `--force` flag to overwrite existing SOUL.md; default behavior is skip with warning

### Package export surface
- Define full `__all__` in `orchestration/__init__.py` — not just the 3 missing symbols, but the complete public API
- `__all__` includes strictly public symbols only — symbols intended for external consumers (L3 containers, CLI, dashboard)
- Internal cross-module imports must use direct submodule imports (e.g. `from orchestration.config import X`), not the package root
- Add a brief docstring to `__init__.py` documenting what the orchestration package provides

### Claude's Discretion
- Logging verbosity for write_soul() (generated/skipped/error messages)
- Exact wording of CLI --force warning messages
- Branch detection implementation details (entrypoint.sh changes)
- geriai project.json fix approach (straightforward data correction)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. All 4 fixes have precise success criteria in the roadmap.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-integration-hardening*
*Context gathered: 2026-02-23*
