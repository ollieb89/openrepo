---
phase: 67
slug: integration-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-04
---

# Phase 67 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (uv run pytest) |
| **Config file** | `packages/orchestration/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/test_topology_public_api.py packages/orchestration/tests/test_route_directive_importable.py -x -q` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/test_topology_public_api.py packages/orchestration/tests/test_route_directive_importable.py -x -q`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 67-01-01 | 01 | 0 | PROP-02, PROP-03, CORR-02 | unit | `uv run pytest packages/orchestration/tests/test_topology_public_api.py -x` | ❌ W0 | ⬜ pending |
| 67-01-02 | 01 | 0 | CORR-07 | unit | `uv run pytest packages/orchestration/tests/test_route_directive_importable.py -x` | ❌ W0 | ⬜ pending |
| 67-01-03 | 01 | 1 | PROP-02, PROP-03 | unit | `uv run pytest packages/orchestration/tests/test_topology_public_api.py -x` | ❌ W0 | ⬜ pending |
| 67-01-04 | 01 | 1 | CORR-02, CORR-07 | unit | `uv run pytest packages/orchestration/tests/test_route_directive_importable.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/orchestration/tests/test_topology_public_api.py` — stubs for PROP-02, PROP-03, CORR-02 (tests `from openclaw.topology import score_proposal, render_diff_summary`)
- [ ] `packages/orchestration/tests/test_route_directive_importable.py` — stubs for CORR-07 (tests `import agents.main.skills.route_directive` and RouteDecision/RouteType symbols)

*Existing infrastructure covers framework setup — only test files needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
