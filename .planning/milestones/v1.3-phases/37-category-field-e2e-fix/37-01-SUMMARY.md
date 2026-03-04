---
phase: 37-category-field-e2e-fix
plan: 01
subsystem: memory-pipeline
tags: [memory, category, pydantic, fastapi, memorize]
dependency_graph:
  requires: []
  provides: [category-field-e2e-wiring]
  affects: [docker/memory/memory_service, orchestration/memory_client, tests/test_memory_client]
tech_stack:
  added: []
  patterns: [Literal type alias for validated enum, Optional[str] payload injection, non-mutating user_dict merge]
key_files:
  created: []
  modified:
    - docker/memory/memory_service/models.py
    - docker/memory/memory_service/routers/memorize.py
    - orchestration/memory_client.py
    - tests/test_memory_client.py
decisions:
  - CategoryValue = Literal['review_decision', 'task_outcome'] — strict Pydantic validation catches invalid categories at API boundary
  - category: Optional[str] = None in MemoryClient — orchestration layer does not import Docker service models; validation at FastAPI boundary
  - Non-mutating user_dict merge: dict(request.user) + category injection — never mutates request.user in place
  - category omitted from POST payload entirely when None — clean backward compatibility, no null values in wire format
metrics:
  duration: 104s
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 4
---

# Phase 37 Plan 01: Category Field E2E Fix Summary

**One-liner:** Closed the category field gap by wiring `CategoryValue` Pydantic validation in FastAPI models, non-mutating user_dict injection in the memorize router, and conditional payload inclusion in MemoryClient — category now flows end-to-end from callers through to memu-py storage.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Add category field to MemorizeRequest and inject into router | ed791d9 | models.py, routers/memorize.py |
| 2 | Wire category into MemoryClient.memorize() payload and update tests | 3c4a980 | memory_client.py, test_memory_client.py |

## What Was Built

### Task 1: MemorizeRequest model and router injection

`docker/memory/memory_service/models.py`:
- Added `Literal, Optional` to typing imports
- Defined `CategoryValue = Literal["review_decision", "task_outcome"]` module-level type alias above `MemorizeRequest`
- Added `category: Optional[CategoryValue] = None` field to `MemorizeRequest` — backward-compatible, invalid values raise `ValidationError`

`docker/memory/memory_service/routers/memorize.py`:
- `_run_memorize()` now builds `user_dict = dict(request.user) if request.user else {}` (non-mutating)
- Injects `user_dict["category"] = request.category` when `request.category is not None`
- Passes `user=user_dict if user_dict else None` to `service.memorize()` — category survives into memu-py storage via `ConfigDict(extra="allow")`

### Task 2: MemoryClient and tests

`orchestration/memory_client.py`:
- Changed `memorize()` signature: `category: str = "general"` → `category: Optional[str] = None`
- Added `if category is not None: payload["category"] = category` after payload construction — top-level field matching `MemorizeRequest` shape
- Updated docstring: category is now active in payload, describes injection flow

`tests/test_memory_client.py`:
- `test_memorize_includes_category_in_payload`: verifies `"category": "review_decision"` present at top level of POST body
- `test_memorize_omits_category_when_none`: verifies `"category"` key absent from POST body when not provided
- All 12 memory_client tests pass; full 65-test suite passes with zero regressions

## Success Criteria Verification

- [x] `MemorizeRequest` has `category: Optional[CategoryValue] = None` with `CategoryValue = Literal["review_decision", "task_outcome"]`
- [x] Router injects category into user dict via non-mutating merge before calling `service.memorize()`
- [x] `MemoryClient.memorize()` includes `category` in POST payload when not None
- [x] All existing tests pass with zero regressions (65/65)
- [x] New tests verify category inclusion and omission in payload

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

Files created/modified:
- FOUND: ~/.openclaw/docker/memory/memory_service/models.py
- FOUND: ~/.openclaw/docker/memory/memory_service/routers/memorize.py
- FOUND: ~/.openclaw/orchestration/memory_client.py
- FOUND: ~/.openclaw/tests/test_memory_client.py

Commits:
- FOUND: ed791d9
- FOUND: 3c4a980
