---
phase: 40-memory-health-monitor
plan: "04"
subsystem: dashboard-frontend, test
tags: [bugfix, archive, memory, health-monitor, regression-test]
dependency_graph:
  requires: [40-03]
  provides: [QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, QUAL-06]
  affects: [workspace/occc/src/components/memory/MemoryPanel.tsx, tests/test_health_scan.py]
tech_stack:
  added: []
  patterns: [content-prefixed-soft-delete, schema-contract-regression-test]
key_files:
  modified:
    - workspace/occc/src/components/memory/MemoryPanel.tsx
    - tests/test_health_scan.py
decisions:
  - "Use content prefix [ARCHIVED <timestamp>] as soft-delete marker — recoverable by editing content back, no backend changes needed"
  - "items array from useMemory hook used directly in handleArchiveMemory (no data?.items indirection — hook exposes items already unwrapped)"
  - "Regression test uses stdlib dict validator instead of pydantic (not available in root test env) — mirrors validation contract faithfully"
metrics:
  duration: "~2 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 40 Plan 04: Archive Body Schema Fix Summary

Fixed the HTTP 422 bug in handleArchiveMemory: replaces { archived_at } body with { content: "[ARCHIVED <timestamp>] <original>" } to satisfy MemoryUpdateRequest's required content field.

## What Was Built

Fixed the only remaining gap blocking full Phase 40 verification. The archive button in HealthTab was sending a PUT body `{ archived_at: new Date().toISOString() }` that the memU backend rejected with Pydantic ValidationError (HTTP 422) because `MemoryUpdateRequest` requires `content: str` (non-optional). The fix routes the archive action through the existing working content-update pipeline.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix handleArchiveMemory to include content in PUT body | 87b4e62 | workspace/occc/src/components/memory/MemoryPanel.tsx |
| 2 | Add regression test for archive PUT body schema | e3fefc1 | tests/test_health_scan.py |

## Key Changes

### Task 1: handleArchiveMemory fix

**Before (broken):**
```ts
body: JSON.stringify({ archived_at: new Date().toISOString() })
```

**After (correct):**
```ts
const item = items.find((m: MemoryItem) => m.id === memoryId);
const currentContent = item?.content ?? '';
body: JSON.stringify({ content: `[ARCHIVED ${new Date().toISOString()}] ${currentContent}` })
```

The fix looks up the current memory content from the `items` array already in scope (from `useMemory` hook), then sends `content` with an `[ARCHIVED <ISO timestamp>]` prefix. This uses the existing PUT proxy that routes to `memu.update_memory_item()`. The archived content is recoverable — an operator can edit the `[ARCHIVED ...]` prefix back.

### Task 2: Regression test

Added `test_archive_body_requires_content` to `tests/test_health_scan.py`:
- Validates that a body with `content` (the new format) is accepted
- Validates that a body with only `archived_at` and no `content` (the old broken format) is rejected
- Uses a stdlib-only dict validator (pydantic not available in root test env)
- Documents the `[ARCHIVED <timestamp>] <original_content>` prefix pattern

## Verification Results

1. `handleArchiveMemory` sends `{ content: "[ARCHIVED ...] ..." }` — grep confirms `content:` in fetch body, no `archived_at:` present
2. TypeScript compilation: no errors in modified files (pre-existing unrelated error in SummaryStream.tsx out of scope)
3. `test_archive_body_requires_content` passes
4. All 20 health scan tests pass (19 existing + 1 new)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Used `items` directly instead of `data?.items`**
- **Found during:** Task 1 — useMemory hook review
- **Issue:** Plan specified `data?.items` but the hook exposes `items` already unwrapped at the component level (line 86: `const { items, ... } = useMemory(...)`)
- **Fix:** Used `items` directly — cleaner, no raw `data` access needed
- **Files modified:** workspace/occc/src/components/memory/MemoryPanel.tsx

**2. [Rule 1 - Bug] Pydantic not available in root test env**
- **Found during:** Task 2 — test execution
- **Issue:** `import pydantic` raised `ModuleNotFoundError` — pydantic is only available inside Docker containers
- **Fix:** Replaced pydantic-based validation with a stdlib dict validator that mirrors the same validation contract (`content` required, raises `ValueError` if missing)
- **Files modified:** tests/test_health_scan.py

## Self-Check: PASSED
