---
phase: 37-category-field-e2e-fix
verified: 2026-02-24T16:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 37: Category Field E2E Fix — Verification Report

**Phase Goal:** The `category` field flows end-to-end from memorize callers through MemoryClient, MemorizeRequest, and memu-py storage, so `_format_memory_context()` primary routing path fires and category metadata appears on retrieved items.

**Verified:** 2026-02-24
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `MemorizeRequest` accepts `category` as an optional field — extra fields are no longer silently discarded | VERIFIED | `models.py` line 14: `category: Optional[CategoryValue] = None`; `CategoryValue = Literal["review_decision", "task_outcome"]` at line 7; Pydantic validation rejects invalid values by construction |
| 2 | `MemoryClient.memorize()` includes `category` in POST payload when provided | VERIFIED | `memory_client.py` lines 199-200: `if category is not None: payload["category"] = category`; `test_memorize_includes_category_in_payload` passes; `test_memorize_omits_category_when_none` passes |
| 3 | A memorized item with `category="review_decision"` returns that category on retrieval | VERIFIED | Router `memorize.py` lines 14-16 injects `user_dict["category"] = request.category` before `service.memorize()` — category is stored in memu-py via `ConfigDict(extra="allow")` user dict; `snapshot.py` line 77 confirms existing caller already sends `"category": "review_decision"` |
| 4 | `_format_memory_context()` routes `category=="review_decision"` items to "Past Review Outcomes" via primary path (not agent_type fallback) | VERIFIED | `spawn.py` lines 203-206: `CATEGORY_SECTION_MAP = {"review_decision": "Past Review Outcomes", "task_outcome": "Task Outcomes"}`; lines 254-255: `if category in CATEGORY_SECTION_MAP: bucket_name = CATEGORY_SECTION_MAP[category]` fires before `elif agent_type == "l2_pm"` fallback; `test_category_primary_routing_review_decision` passes (no agent_type field in item) |

**Score:** 4/4 truths verified

---

## Required Artifacts

### Plan 37-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker/memory/memory_service/models.py` | `CategoryValue` Literal type and `category` field on `MemorizeRequest` | VERIFIED | Line 7: `CategoryValue = Literal["review_decision", "task_outcome"]`; Line 14: `category: Optional[CategoryValue] = None`; File is 31 lines, substantive |
| `docker/memory/memory_service/routers/memorize.py` | Category injection into user dict before `service.memorize()` | VERIFIED | Lines 14-16: non-mutating `user_dict` merge with `user_dict["category"] = request.category` conditional; Line 20: passes `user=user_dict if user_dict else None` to service |
| `orchestration/memory_client.py` | `category` parameter wired into `memorize()` payload | VERIFIED | Lines 171-172: `category: Optional[str] = None` signature; Lines 199-200: `if category is not None: payload["category"] = category` |
| `tests/test_memory_client.py` | Tests for category inclusion and omission | VERIFIED | `test_memorize_includes_category_in_payload` (line 110) and `test_memorize_omits_category_when_none` (line 132) — both pass |

### Plan 37-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/spawn_specialist/spawn.py` | `CATEGORY_SECTION_MAP` and three-bucket `_format_memory_context()` | VERIFIED | Lines 203-206: `CATEGORY_SECTION_MAP` constant; Lines 239-272: three buckets (`work_bullets`, `review_bullets`, `task_bullets`); Lines 276-283: review-first output ordering |
| `tests/test_spawn_memory.py` | Tests for category-primary routing, task_outcome section, ordering | VERIFIED | 6 new tests added (lines 488-615): `test_category_section_map_contains_expected_keys`, `test_category_primary_routing_review_decision`, `test_category_primary_routing_task_outcome`, `test_category_routing_with_mixed_categories`, `test_legacy_items_without_category_still_route_correctly`, `test_task_outcome_category_budget_shared` — all pass |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `orchestration/memory_client.py` | `docker/memory/memory_service/routers/memorize.py` | POST `/memorize` payload with top-level `category` field | WIRED | `memory_client.py` builds payload with `payload["category"] = category`; `MemorizeRequest` at FastAPI boundary extracts `category` as a validated top-level field |
| `docker/memory/memory_service/routers/memorize.py` | `memu-py service.memorize()` | `user_dict["category"] = request.category` injection | WIRED | `memorize.py` `_run_memorize()` builds `user_dict` and conditionally injects `category` before calling `await service.memorize(user=user_dict ...)` |
| `skills/spawn_specialist/spawn.py` | memu-py retrieved items | `item.get("category")` primary routing check via `CATEGORY_SECTION_MAP` | WIRED | `_format_memory_context()` checks `if category in CATEGORY_SECTION_MAP` as first branch; `CATEGORY_SECTION_MAP` lookup is canonical; `test_category_primary_routing_review_decision` fires without `agent_type` field, confirming primary path |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MEM-01 | 37-01 | L3 task outcomes auto-memorized after successful container exit | SATISFIED | Phase scope: the category field wiring enables `task_outcome` category on L3 memorize calls. `MemorizeRequest` now accepts and stores `category` so memu-py persists it. Full MEM-01 lifecycle coverage completed across phases 28+37. |
| MEM-02 | 37-01, 37-02 | L2 review decisions memorized after each review cycle | SATISFIED | `snapshot.py` line 77 sends `"category": "review_decision"` (wired in Phase 34). Plan 37-01 ensures that category value is no longer dropped at `MemorizeRequest` boundary — it now flows into memu-py storage via user dict injection. |
| RET-02 | 37-01, 37-02 | Retrieved memories injected into SOUL template with memory context section | SATISFIED | `_format_memory_context()` now routes `review_decision` items to "## Past Review Outcomes" via `CATEGORY_SECTION_MAP` primary path (not agent_type fallback). Three-bucket formatter with review-first ordering (review -> task outcomes -> work context) completes the retrieval side. 49/49 tests in `test_spawn_memory.py` and `test_memory_client.py` pass. |

**Orphaned requirements check:** REQUIREMENTS.md maps MEM-01 to "Phase 37, 38" and MEM-02/RET-02 to "Phase 37". No additional requirement IDs are mapped to Phase 37 that go unclaimed by these two plans.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `skills/spawn_specialist/spawn.py` | 226 | "placeholders" in docstring comment ("no placeholders") | Info | Not a code anti-pattern — the docstring explicitly states the design decision to omit empty placeholders. No impact. |

No blocker or warning anti-patterns found. No stub implementations, no empty handlers, no `return null` / `return {}` anti-patterns in any modified file.

---

## Human Verification Required

None. All four success criteria are fully verifiable programmatically:

- SC1 verified by code inspection (`models.py` lines 7, 14) and test suite
- SC2 verified by `test_memorize_includes_category_in_payload` and `test_memorize_omits_category_when_none`
- SC3 verified by code inspection of router injection path (`memorize.py` lines 14-16) and `snapshot.py` line 77 showing existing caller
- SC4 verified by `test_category_primary_routing_review_decision` (item has no `agent_type` field, confirming primary path fires)

---

## Test Suite Results

| Suite | Tests | Result |
|-------|-------|--------|
| `tests/test_memory_client.py` | 11 | 11/11 PASSED |
| `tests/test_spawn_memory.py` | 38 | 38/38 PASSED |
| Full suite (`tests/`) | 71 | 71/71 PASSED — zero regressions |

---

## Commit Verification

All four commits documented in SUMMARYs confirmed in git log:

| Commit | Description |
|--------|-------------|
| `ed791d9` | feat(37-01): add category field to MemorizeRequest and inject into router |
| `3c4a980` | feat(37-01): wire category into MemoryClient.memorize() payload and update tests |
| `76c5376` | feat(37-02): add CATEGORY_SECTION_MAP and upgrade _format_memory_context() to three-bucket routing |
| `3c353dd` | feat(37-02): add category-routing tests and CATEGORY_SECTION_MAP import |

---

## Summary

Phase 37 fully achieves its goal. The `category` field now flows end-to-end:

1. **Storage side (Plan 37-01):** `MemorizeRequest` validates `category` via `CategoryValue = Literal["review_decision", "task_outcome"]`. The FastAPI router injects it into the memu-py user dict (non-mutating merge). `MemoryClient.memorize()` conditionally includes it at the top level of the POST payload. `snapshot.py` (the primary caller) was already sending `category="review_decision"` — it now reaches storage.

2. **Retrieval side (Plan 37-02):** `CATEGORY_SECTION_MAP` provides primary routing. `_format_memory_context()` checks `category in CATEGORY_SECTION_MAP` before the `agent_type == "l2_pm"` fallback. Three sections are emitted in locked order: Past Review Outcomes, Task Outcomes, Past Work Context. Legacy items without a `category` field continue to route correctly via the agent_type fallback.

MEM-01, MEM-02, and RET-02 are fully satisfied by this phase. 71/71 tests pass with zero regressions.

---

_Verified: 2026-02-24_
_Verifier: Claude (gsd-verifier)_
