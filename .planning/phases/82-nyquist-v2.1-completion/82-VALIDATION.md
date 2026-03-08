---
phase: 82
slug: nyquist-v2-1-completion
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 82 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | File-system verification (bash) — no application test suite |
| **Config file** | none |
| **Quick run command** | `ls .planning/phases/{74,75,78,79,80}-*/*-VALIDATION.md 2>/dev/null` |
| **Full suite command** | See Validation Architecture below |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick existence check for the file just created
- **After every plan wave:** Run full suite (all 5 files + audit)
- **Before `/gsd:verify-work`:** Full suite must confirm all 5 have `nyquist_compliant: true`
- **Max feedback latency:** 5 seconds

---

## Validation Architecture

### What "Done" Looks Like

All 5 VALIDATION.md files exist AND contain `nyquist_compliant: true`:
1. `.planning/phases/74-*/74-VALIDATION.md` — `nyquist_compliant: true`
2. `.planning/phases/75-*/75-VALIDATION.md` — `nyquist_compliant: true`
3. `.planning/phases/78-*/78-VALIDATION.md` — `nyquist_compliant: true`
4. `.planning/phases/79-*/79-VALIDATION.md` — `nyquist_compliant: true`
5. `.planning/phases/80-*/80-VALIDATION.md` — `nyquist_compliant: true`

Additionally: `v2.1-MILESTONE-AUDIT.md` updated with `nyquist.overall: compliant`.

### Verification Commands

```bash
# Check all 5 VALIDATION.md files exist and have nyquist_compliant: true
for phase in 74 75 78 79 80; do
  file=$(ls .planning/phases/${phase}-*/*-VALIDATION.md 2>/dev/null | head -1)
  if [ -z "$file" ]; then
    echo "MISSING: Phase ${phase} VALIDATION.md"
  else
    val=$(grep "nyquist_compliant:" "$file" | head -1 | awk '{print $2}')
    echo "Phase ${phase}: nyquist_compliant=${val} (${file})"
  fi
done

# Check milestone audit updated
grep "overall:" .planning/v2.1-MILESTONE-AUDIT.md 2>/dev/null || echo "MISSING: audit file"
```

### Pass/Fail Criteria

| Check | Pass | Fail |
|-------|------|------|
| Phase 74 VALIDATION.md exists | file present | no file |
| Phase 74 nyquist_compliant | `true` | `false` or missing |
| Phase 75 VALIDATION.md exists | file present | no file |
| Phase 75 nyquist_compliant | `true` | `false` or missing |
| Phase 78 VALIDATION.md exists | file present | no file |
| Phase 78 nyquist_compliant | `true` | `false` or missing |
| Phase 79 VALIDATION.md exists | file present | no file |
| Phase 79 nyquist_compliant | `true` | `false` or missing |
| Phase 80 VALIDATION.md exists | file present | no file |
| Phase 80 nyquist_compliant | `true` | `false` or missing |
| Milestone audit updated | `nyquist.overall: compliant` | missing or `partial` |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 82-01-01 | 01 | 1 | Nyquist gap | file-check | `grep "nyquist_compliant: true" .planning/phases/74-*/*-VALIDATION.md` | pending |
| 82-01-02 | 01 | 1 | Nyquist gap | file-check | `grep "nyquist_compliant: true" .planning/phases/75-*/*-VALIDATION.md` | pending |
| 82-01-03 | 01 | 1 | Nyquist gap | file-check | `grep "nyquist_compliant: true" .planning/phases/78-*/*-VALIDATION.md` | pending |
| 82-01-04 | 01 | 1 | Nyquist gap | file-check | `grep "nyquist_compliant: true" .planning/phases/79-*/*-VALIDATION.md` | pending |
| 82-01-05 | 01 | 1 | Nyquist gap | file-check | `grep "nyquist_compliant: true" .planning/phases/80-*/*-VALIDATION.md` | pending |
| 82-01-06 | 01 | 2 | Milestone audit | grep | `grep "overall: compliant" .planning/v2.1-MILESTONE-AUDIT.md` | pending |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework installation needed — verification is file-system based.

---

## Manual-Only Verifications

All phase behaviors have automated verification (file-existence + grep checks).

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
