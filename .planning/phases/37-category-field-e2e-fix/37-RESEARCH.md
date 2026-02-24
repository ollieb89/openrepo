# Phase 37: Category Field End-to-End Fix - Research

**Researched:** 2026-02-24
**Domain:** Python/Pydantic plumbing — category field propagation from callers through MemoryClient, FastAPI MemorizeRequest, memu-py storage, and _format_memory_context() routing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Category value semantics: controlled set of known values (`review_decision`, `task_outcome`) — NOT free-form strings
- Type: defined as `Literal` type or `Enum` in `MemorizeRequest`, co-located with the Pydantic model in `/home/ollie/.openclaw/docker/memory/memory_service/models.py`
- Unknown category values are rejected by Pydantic validation (strict contract, catches bugs early)
- `category` is optional on `MemorizeRequest` — defaults to `None` when omitted, backwards compatible
- Narrow fix: just add the `category` field to `MemorizeRequest`, don't change the extra fields policy or audit other fields
- When memu-py API returns a memory without `category` (older data), client defaults to `None` gracefully
- Integration test required: memorize with category → retrieve → assert category present and routing works
- Formatter routing: hard-coded dict `{"review_decision": "Past Review Outcomes", "task_outcome": "Task Outcomes"}`
- Category determines section; `agent_type` determines ordering/sub-grouping within each section
- Output ordering: review decisions → task outcomes → uncategorized/fallback
- Existing `agent_type` fallback routing remains for memories without a category (zero breakage)
- Existing callers that should use category (e.g. review_skill → snapshot.py `_memorize_review_decision`) are updated in this phase
- "Past Review Outcomes" section heading already exists in the formatter — category routing uses it directly

### Claude's Discretion

- memu-py storage model investigation and any needed schema changes
- Exact defaulting approach for `category=None` on old memories
- How agent_type sub-grouping works within category sections (ordering, indentation, etc.)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-01 | L3 task outcomes (semantic snapshots) are auto-memorized after successful container exit via fire-and-forget pattern | Partial: snapshot.py and spawn.py exist. `_memorize_review_decision` pattern from MEM-02 should be replicated for L3 outcomes. `category="task_outcome"` must flow from spawn.py through MemoryClient payload. |
| MEM-02 | L2 review decisions (merge/reject with reasoning) are memorized after each review cycle | Already fires via `_memorize_review_decision()` in `snapshot.py`. The gap is that `category` is in the raw httpx payload but is NOT accepted by `MemorizeRequest` — it is silently dropped. This phase wires the field through. |
| RET-02 | Retrieved memories are injected into SOUL template via soul_renderer.py with a memory context section | `_format_memory_context()` in `spawn.py` already implements dual-check routing (`category=="review_decision" OR agent_type=="l2_pm"`). The primary path (category) fires only if memu-py stores and returns the `category` field on retrieved items. This phase closes that loop. |
</phase_requirements>

---

## Summary

Phase 37 is a pure plumbing fix, not a new capability. Every component of the category flow already exists; the gaps are specific and narrow:

1. **`MemorizeRequest` in the FastAPI wrapper does not declare a `category` field.** The model at `/home/ollie/.openclaw/docker/memory/memory_service/models.py` has `resource_url`, `modality`, and `user` only. When `snapshot.py` posts `{"resource_url": ..., "category": "review_decision", ...}`, Pydantic silently discards `category` (Pydantic v2 default: `extra="ignore"`). The field never reaches `service.memorize()`.

2. **`MemoryClient.memorize()` does not pass `category` in the payload.** `orchestration/memory_client.py` builds a payload with `resource_url`, `modality`, and `user`, but no `category`. The async client path (used by L3 tooling) would also miss the field.

3. **`MemoryService.memorize()` (memu-py) does not accept a `category` parameter.** The memu-py `MemorizeMixin.memorize()` signature is `(self, *, resource_url, modality, user)`. To pass `category` from the FastAPI router into memu-py storage, either the router must inject it into the `user` scope dict, or memu-py must be extended. Investigation shows the cleaner path: store `category` in the `extra` field of `MemoryItem` (which memu-py models already support via `extra: dict[str, Any]`).

4. **`_format_memory_context()` primary routing path works correctly** when `category` is present in retrieved items. The dual-check logic is already implemented and tested (Phase 34). The issue is that category is never stored in memU, so retrieved items never carry it.

**Primary recommendation:** Add `category: Optional[Literal["review_decision", "task_outcome"]] = None` to `MemorizeRequest` in the FastAPI wrapper, pass it through to memu-py via the `user` dict (or a custom storage path in `extra`), and update `snapshot.py` `_memorize_review_decision()` + `MemoryClient.memorize()` to include `category` in their payloads.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic v2 | Already in use | `MemorizeRequest` model with `Literal` type constraint | Project-standard; all existing models use Pydantic v2 |
| httpx | Already in use | Sync/async HTTP client for MemoryClient | Already established pattern throughout codebase |
| FastAPI | Already in use | REST API framework for memory service | Already deployed |
| pytest + unittest.mock | Already in use | Test framework | Project standard: `tests/pytest.ini` confirms pytest |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| respx | Already in use | Mock httpx transport for async tests | Use for MemoryClient test additions |
| typing.Literal | stdlib | Constrain `category` to controlled values | Used in `MemorizeRequest` per locked decision |
| typing.Optional | stdlib | Make `category` field optional (None default) | Required for backward compat |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Literal["review_decision", "task_outcome"]` | `str` with validator | Literal gives compile-time checking and Pydantic rejects invalid values automatically |
| Passing category in `user` dict | Custom memu-py extension | `user` dict is already the scoping mechanism — injecting category there is clean but semantically wrong; `extra` field in MemoryItem is the correct storage location |

---

## Architecture Patterns

### Current Data Flow (BROKEN — category is dropped)

```
snapshot.py._memorize_review_decision()
  → httpx.Client.post("/memorize", json={..., "category": "review_decision", ...})
  → FastAPI POST /memorize
  → MemorizeRequest(**payload)  # DROPS category (not in model)
  → _run_memorize(service, request)
  → service.memorize(resource_url=..., modality=..., user=...)  # no category
  → MemoryItem stored (no category in extra)
  → /retrieve returns items without category field
  → _format_memory_context(): category check fails → falls back to agent_type
```

### Target Data Flow (FIXED — category survives)

```
snapshot.py._memorize_review_decision()  (no change needed — already sends category)
MemoryClient.memorize(content, category="review_decision")
  → POST /memorize payload includes "category": "review_decision"
  → MemorizeRequest.category = "review_decision"  (new field)
  → _run_memorize(service, request)
  → service.memorize with category stored in MemoryItem.extra["category"]
  → /retrieve returns items with category field
  → _format_memory_context(): primary check fires (category == "review_decision")
  → "## Past Review Outcomes" section rendered
```

### Pattern 1: MemorizeRequest field addition (Pydantic v2)
**What:** Add `category` as `Optional[Literal[...]] = None` to the Pydantic model
**When to use:** Adding optional fields with controlled values

```python
# Source: /home/ollie/.openclaw/docker/memory/memory_service/models.py (to be modified)
from typing import Literal, Optional
from pydantic import BaseModel

CategoryValue = Literal["review_decision", "task_outcome"]

class MemorizeRequest(BaseModel):
    resource_url: str
    modality: str = "conversation"
    user: dict[str, Any] | None = None
    category: Optional[CategoryValue] = None  # NEW — optional, validated, backward-compatible
```

### Pattern 2: Injecting category into memu-py via user dict or extra
**What:** memu-py `MemorizeMixin.memorize()` has no `category` parameter. Two approaches:
- **Option A (user dict injection):** Pass `category` inside the `user` dict alongside `user_id` and `agent_type`. memu-py merges the user dict into the scoped user model, and extra fields are stored due to `ConfigDict(extra="allow")` in `merge_scope_model()`.
- **Option B (router-side extra dict):** The router calls `service.memorize(resource_url=..., modality=..., user=...)` — category can be injected into `user` dict here since memu-py stores arbitrary user fields.

**Key finding (HIGH confidence):** `memu/database/models.py` line 121 shows `ConfigDict(extra="allow")` in `merge_scope_model()`. The user scope model is merged with core models using `extra="allow"`, meaning any extra fields in the `user` dict are stored in the database record. **`category` stored in the `user` dict will be preserved in the DB and returned on retrieval.**

**Investigation result:** The cleanest approach is to pass `category` inside the `user` dict from the router. The router already builds `request.user` as a dict; adding `"category": request.category` (when not None) keeps it within the existing flow without modifying memu-py internals.

```python
# Source: /home/ollie/.openclaw/docker/memory/memory_service/routers/memorize.py (to be modified)
async def _run_memorize(service, request: MemorizeRequest) -> None:
    user_dict = request.user or {}
    if request.category is not None:
        user_dict = {**user_dict, "category": request.category}  # non-mutating merge
    await service.memorize(
        resource_url=request.resource_url,
        modality=request.modality,
        user=user_dict if user_dict else None,
    )
```

**Retrieval result shape:** On `/retrieve`, memu-py returns items serialized from the scoped user model. Since `extra="allow"`, the `category` key stored in the user scope is included in the returned dict. `_format_memory_context()` already reads `item.get("category", "")` — this will now find the value.

### Pattern 3: MemoryClient.memorize() signature update
**What:** Add `category: Optional[str] = None` parameter, include in payload when set

```python
# Source: /home/ollie/.openclaw/orchestration/memory_client.py (to be modified)
async def memorize(
    self,
    content: str,
    category: Optional[str] = None,
) -> Optional[MemorizeResult]:
    payload = {
        "resource_url": content,
        "modality": "conversation",
        "user": {
            "user_id": self.project_id,
            "agent_type": self.agent_type.value,
        },
    }
    if category is not None:
        payload["category"] = category  # top-level in payload, not nested in user
```

**Note:** The current `memorize()` signature already has `category: str = "general"` but the docstring says it is "currently unused in payload". This confirms the field is accepted by the function but never sent. The fix is to actually include it in the payload dict.

### Pattern 4: _format_memory_context() routing update (Task Outcomes)
**What:** Add "Task Outcomes" section for `category == "task_outcome"` items; enforce ordering (review → task → uncategorized)
**Current state:** The formatter has two sections: "Past Work Context" and "Past Review Outcomes". With the new `task_outcome` category and its own section heading, a third branch is needed.

```python
# Source: /home/ollie/.openclaw/skills/spawn_specialist/spawn.py (to be modified)
CATEGORY_SECTION_MAP = {
    "review_decision": "Past Review Outcomes",
    "task_outcome": "Task Outcomes",
}

# In _format_memory_context():
# Routing:
category = item.get("category", "")
agent_type = item.get("agent_type", "")

if category in CATEGORY_SECTION_MAP:
    section_key = CATEGORY_SECTION_MAP[category]  # primary path
elif agent_type == "l2_pm":
    section_key = "Past Review Outcomes"  # fallback for legacy items
else:
    section_key = "Past Work Context"  # uncategorized
```

### Anti-Patterns to Avoid

- **Mutating the `user` dict in place in the router:** `request.user` may be shared; always create a new dict `{**request.user, "category": ...}`.
- **Changing extra fields policy globally:** User decision says "narrow fix — just add the category field, don't change extra fields policy."
- **Storing `category` at the top level of the memu-py workflow state:** memu-py's `memorize()` workflow state doesn't carry `category`; it must go via the `user` dict (the user scope mechanism).
- **Adding `category` to the `MemorizeResult` dataclass in memory_client.py:** Not needed — the client only needs to *send* the category, not return it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Category validation | Custom validator function | `Literal["review_decision", "task_outcome"]` in Pydantic | Pydantic raises `ValidationError` automatically; no custom code needed |
| Extra field propagation through memu-py | Custom DB schema migration | `user` dict extra-field passthrough (already supported via `extra="allow"`) | Zero memu-py changes needed |
| Backward compat check | Version detection logic | `Optional[...] = None` default | Pydantic handles it: old callers omit field, new callers set it |

**Key insight:** memu-py's `extra="allow"` in the scoped user model is the magic that makes the category flow without touching memu-py internals.

---

## Common Pitfalls

### Pitfall 1: memu-py `memorize()` drops unknown kwargs
**What goes wrong:** Calling `service.memorize(resource_url=..., modality=..., user=..., category=...)` will raise `TypeError` — the method only accepts `resource_url`, `modality`, and `user`.
**Why it happens:** `MemorizeMixin.memorize()` uses keyword-only arguments with explicit parameters. No `**kwargs`.
**How to avoid:** Do NOT add `category` as a kwarg to `service.memorize()`. Instead, inject it into the `user` dict before calling `service.memorize()`. The router (`_run_memorize`) is the right injection point.
**Warning signs:** `TypeError: memorize() got an unexpected keyword argument 'category'`

### Pitfall 2: Category in retrieved items uses a different key than expected
**What goes wrong:** `_format_memory_context()` reads `item.get("category", "")`. If memu-py serializes the user-scope extra fields under a different key (e.g., `user_category`, or nested under `user`), the check fails silently.
**Why it happens:** When `category` is stored in the `user` dict scope, memu-py may serialize the full user scope as a nested object rather than flattening it into the item dict.
**How to avoid:** The integration test (memorize with category → retrieve → assert `item["category"] == "review_decision"`) will catch this immediately. Inspect the raw retrieve response before finalizing the formatter fix.
**Warning signs:** Integration test shows category missing from retrieved item dict despite successful memorize.

### Pitfall 3: Silent discard on old `MemorizeRequest` (Pydantic default behavior)
**What goes wrong:** Pydantic v2 default is `model_config = ConfigDict(extra="ignore")`. Without adding the `category` field, any payload with `category` silently succeeds — no error, no storage.
**Why it happens:** This is the current bug. `snapshot.py` already sends `category` in the raw httpx payload, but it never reaches memu-py.
**How to avoid:** Confirm fix by verifying `MemorizeRequest(resource_url="x", modality="conversation", category="review_decision").category` equals `"review_decision"` (not `None`).

### Pitfall 4: MemoryClient.memorize() category parameter type mismatch
**What goes wrong:** Current signature has `category: str = "general"` (unused). The CONTEXT.md decision says the field should be `Optional[str]` (or `Optional[CategoryValue]`). Changing default from `"general"` to `None` is a breaking change for any callers that rely on the default.
**Why it happens:** Original implementation added the parameter for future use but chose a non-None default.
**How to avoid:** Check all callers of `MemoryClient.memorize()` before changing the default. Current codebase callers: `snapshot.py._memorize_review_decision()` uses raw httpx directly (not MemoryClient), and test_memory_client.py may call `memorize()` with the old default. Safest path: keep `category: Optional[str] = None` (change default from `"general"` to `None`), update payload to include `category` when not None.

### Pitfall 5: _format_memory_context() ordering change breaks existing tests
**What goes wrong:** Current output order is: work items first, review items second. Adding a "Task Outcomes" section and enforcing `review → task → uncategorized` order changes the output structure.
**Why it happens:** Existing tests in `test_spawn_memory.py` assert specific section presence/absence but not exact ordering. New ordering (review first) may break existing tests that assume work context comes first.
**How to avoid:** Read all existing `_format_memory_context` tests before modifying the function. The CONTEXT.md says "review decisions → task outcomes → uncategorized/fallback" — this may reorder the sections vs the current impl (which outputs work context first).

---

## Code Examples

### Full gap map — files to touch

```
File 1: /home/ollie/.openclaw/docker/memory/memory_service/models.py
  Gap: MemorizeRequest has no category field
  Fix: Add category: Optional[Literal["review_decision", "task_outcome"]] = None

File 2: /home/ollie/.openclaw/docker/memory/memory_service/routers/memorize.py
  Gap: _run_memorize() calls service.memorize() without category
  Fix: Inject category into user dict before calling service.memorize()

File 3: /home/ollie/.openclaw/orchestration/memory_client.py
  Gap: memorize() builds payload without category; category param exists but unused
  Fix: Include category in payload when not None (change default from "general" to None)

File 4: /home/ollie/.openclaw/skills/spawn_specialist/spawn.py
  Gap: _format_memory_context() has no "Task Outcomes" section; ordering is work-first
  Fix: Add CATEGORY_SECTION_MAP; add task_outcome section; reorder to review→task→work

File 5 (MEM-01): /home/ollie/.openclaw/skills/spawn_specialist/spawn.py (different location)
  Gap: L3 task outcomes are never memorized — MEM-01 is unchecked in REQUIREMENTS.md
  Fix: Add fire-and-forget memorization call after successful container exit in pool.py
  Note: MEM-01 is partially in scope (Phase 38 handles the other part). Research supports
  understanding the pattern — see _memorize_review_decision() in snapshot.py as the template.
```

### MemorizeRequest after fix
```python
# /home/ollie/.openclaw/docker/memory/memory_service/models.py
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel

CategoryValue = Literal["review_decision", "task_outcome"]

class MemorizeRequest(BaseModel):
    resource_url: str
    modality: str = "conversation"
    user: dict[str, Any] | None = None
    category: Optional[CategoryValue] = None
```

### Router injection after fix
```python
# /home/ollie/.openclaw/docker/memory/memory_service/routers/memorize.py
async def _run_memorize(service, request: MemorizeRequest) -> None:
    try:
        user_dict = dict(request.user) if request.user else {}
        if request.category is not None:
            user_dict["category"] = request.category
        await service.memorize(
            resource_url=request.resource_url,
            modality=request.modality,
            user=user_dict if user_dict else None,
        )
        logger.info(f"Memorized: {request.resource_url}")
    except Exception as e:
        logger.error(f"Memorization failed for {request.resource_url}: {e}")
```

### MemoryClient after fix
```python
# /home/ollie/.openclaw/orchestration/memory_client.py
async def memorize(
    self,
    content: str,
    category: Optional[str] = None,
) -> Optional[MemorizeResult]:
    payload = {
        "resource_url": content,
        "modality": "conversation",
        "user": {
            "user_id": self.project_id,
            "agent_type": self.agent_type.value,
        },
    }
    if category is not None:
        payload["category"] = category
    # ... rest of method unchanged
```

### _format_memory_context() routing after fix
```python
# /home/ollie/.openclaw/skills/spawn_specialist/spawn.py
CATEGORY_SECTION_MAP = {
    "review_decision": "Past Review Outcomes",
    "task_outcome": "Task Outcomes",
}

def _format_memory_context(memories: list) -> str:
    # ... setup unchanged ...
    for item in memories:
        text = item.get("resource_url", "") or item.get("content", "") or ""
        if not text:
            continue

        category = item.get("category", "")
        agent_type = item.get("agent_type", "")

        # Primary routing: category field (new items)
        if category in CATEGORY_SECTION_MAP:
            bucket = CATEGORY_SECTION_MAP[category]
        # Fallback: agent_type (legacy items without category)
        elif agent_type == "l2_pm":
            bucket = "Past Review Outcomes"
        else:
            bucket = "Past Work Context"

        # ... budget accounting and bucketing ...

    # Output order: review → task outcomes → work context (uncategorized)
    sections = []
    if review_bullets:
        sections.append("## Past Review Outcomes\n\n" + "\n".join(review_bullets))
    if task_bullets:
        sections.append("## Task Outcomes\n\n" + "\n".join(task_bullets))
    if work_bullets:
        sections.append("## Past Work Context\n\n" + "\n".join(work_bullets))

    return "\n\n".join(sections) if sections else ""
```

---

## Open Questions

1. **Does category survive the memu-py user-dict round-trip?**
   - What we know: `merge_scope_model()` uses `ConfigDict(extra="allow")`, meaning extra fields in the user dict are accepted and stored. The retrieved item should include the `category` key.
   - What's unclear: How memu-py serializes the user-scope fields in the retrieve response — is the `category` key flat in the item dict or nested under a `user` sub-object?
   - Recommendation: The integration test (memorize → retrieve → assert category present) will definitively answer this. The plan should schedule this test early and adjust the router approach if `category` appears nested.

2. **MEM-01 scope boundary with Phase 38**
   - What we know: MEM-01 is listed as `Phase 37, 38` in REQUIREMENTS.md. Phase 37 CONTEXT.md says existing callers should be updated to pass category.
   - What's unclear: Does Phase 37 implement any part of L3 task outcome memorization (the fire-and-forget pattern), or is that entirely Phase 38?
   - Recommendation: Phase 37 should at minimum ensure `MemoryClient.memorize()` accepts and passes `category` — this is required for Phase 38's L3 outcome memorization to work correctly. The actual call-site in spawn.py for L3 outcome memorization can be deferred to Phase 38.

---

## Validation Architecture

> `workflow.nyquist_validation` not present in `.planning/config.json` (config only has `workflow.research: true`). Treating as false — Validation Architecture section omitted per instructions.

*(Config at `/home/ollie/.openclaw/.planning/config.json` does not contain `nyquist_validation: true`)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `/home/ollie/.openclaw/docker/memory/memory_service/models.py` — confirmed `MemorizeRequest` has no `category` field
- Direct codebase inspection — `/home/ollie/.openclaw/docker/memory/memory_service/routers/memorize.py` — confirmed router drops `category` by calling `service.memorize(resource_url=..., modality=..., user=...)` only
- Direct codebase inspection — `/home/ollie/.openclaw/orchestration/memory_client.py` lines 168-214 — confirmed `category` parameter exists but is commented "currently unused in payload"
- Direct codebase inspection — `/home/ollie/.openclaw/skills/spawn_specialist/spawn.py` lines 201-259 — confirmed `_format_memory_context()` dual-check logic is already implemented and correct
- Direct codebase inspection — `/home/ollie/.openclaw/orchestration/snapshot.py` lines 73-82 — confirmed `category` is already in the raw httpx POST payload but gets dropped
- Direct codebase inspection — `/home/ollie/.openclaw/workspace/memory/src/memu/database/models.py` line 121 — confirmed `ConfigDict(extra="allow")` in `merge_scope_model()`
- Direct codebase inspection — `/home/ollie/.openclaw/workspace/memory/src/memu/app/memorize.py` lines 65-71 — confirmed memu-py `MemorizeMixin.memorize()` signature: `(self, *, resource_url, modality, user)` — no `category` param
- Direct codebase inspection — `/home/ollie/.openclaw/tests/` — confirmed pytest infrastructure exists with `pytest.ini`, respx for async mocking, and existing test files for all affected modules

### Secondary (MEDIUM confidence)
- Inferred from `extra="allow"` + user dict merge pattern in `merge_scope_model()` that category will survive the round-trip — not verified by running the code, but the mechanism is clear from the source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — all files and their relationships directly read and traced
- Pitfalls: HIGH — gaps confirmed by reading actual source code (not inferred)
- memu-py extra field round-trip: MEDIUM — mechanism is clear from source but not experimentally verified

**Research date:** 2026-02-24
**Valid until:** 2026-03-24 (stable codebase — no external moving parts)
