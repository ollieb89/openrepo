---
phase: 63
slug: correction-system-and-approval-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-03
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.0+ |
| **Config file** | `packages/orchestration/pyproject.toml` |
| **Quick run command** | `uv run pytest packages/orchestration/tests/test_correction.py packages/orchestration/tests/test_approval.py -x` |
| **Full suite command** | `uv run pytest packages/orchestration/tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest packages/orchestration/tests/test_correction.py packages/orchestration/tests/test_approval.py -x`
- **After every plan wave:** Run `uv run pytest packages/orchestration/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 63-01-01 | 01 | 0 | CORR-01 | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestSoftCorrection -x` | ❌ W0 | ⬜ pending |
| 63-01-02 | 01 | 0 | CORR-02 | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestHardCorrection -x` | ❌ W0 | ⬜ pending |
| 63-01-03 | 01 | 0 | CORR-06 | unit | `uv run pytest packages/orchestration/tests/test_correction.py::TestCycleLimit -x` | ❌ W0 | ⬜ pending |
| 63-02-01 | 02 | 0 | CORR-03 | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApproveTopology -x` | ❌ W0 | ⬜ pending |
| 63-02-02 | 02 | 0 | CORR-04 | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApproveTopology::test_hard_correction_immediate -x` | ❌ W0 | ⬜ pending |
| 63-02-03 | 02 | 0 | CORR-05 | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestPushbackNote -x` | ❌ W0 | ⬜ pending |
| 63-02-04 | 02 | 0 | CORR-07 | unit | `uv run pytest packages/orchestration/tests/test_approval.py::TestApprovalGate -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/orchestration/tests/test_correction.py` — stubs for CORR-01, CORR-02, CORR-06
- [ ] `packages/orchestration/tests/test_approval.py` — stubs for CORR-03, CORR-04, CORR-05, CORR-07
- [ ] `packages/orchestration/src/openclaw/topology/correction.py` — CorrectionSession, export_draft, import_draft, apply_soft_correction
- [ ] `packages/orchestration/src/openclaw/topology/approval.py` — approve_topology, compute_pushback_note, approval gate helpers

*No framework install needed — pytest already in dev dependencies.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive feedback loop UX | CORR-01 | Requires TTY input from user | Run `openclaw-propose`, type feedback text, verify re-proposal displays diff + updated version |
| Editor-based hard correction | CORR-02 | Requires external editor interaction | Run propose, select edit, modify proposal-draft.json, verify import succeeds |
| Pushback note inline display | CORR-05 | Visual rendering verification | Approve a topology that contradicts high-confidence proposal, verify note appears |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
