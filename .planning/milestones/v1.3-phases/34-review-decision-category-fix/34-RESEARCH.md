# Phase 34: Review Decision Category Fix - Research

**Researched:** 2026-02-24
**Domain:** Python payload construction, memory routing logic
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Use a plain string literal `"review_decision"` — no constants, no enums
- Add `"category": "review_decision"` as a new field alongside existing payload fields in `_memorize_review_decision()`
- Always send the category unconditionally — no feature flags, no version checks
- Scoped to review decisions only — other memorize functions are not modified in this phase
- No migration of existing memories — old items stay as-is without a category field
- Items without a category field silently route to "Past Work Context" (default section)
- Items with an unrecognized category value also route to "Past Work Context" (safe fallback)
- Explicit test case required: verify items without category field route to default section
- Keep existing SOUL section names: "Past Review Outcomes" and "Past Work Context"
- Skip empty items — don't render memories with no meaningful content regardless of category
- Both mocked unit test AND optional integration test (with pytest marker) for the round-trip
- Fix is minimal and surgical, touching only `_memorize_review_decision()` in `snapshot.py` and `_format_memory_context()` in `spawn.py`

### Claude's Discretion

- Routing implementation approach (simple if/else vs dict-based mapping) — pick what fits the current `_format_memory_context()` structure
- Whether to emit a debug log for items without a category field — match existing logging patterns in the codebase

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-02 | L2 review decisions (merge/reject with reasoning) are memorized after each review cycle | `_memorize_review_decision()` already fires correctly — gap is the missing `category` field in payload |
| RET-02 | Retrieved memories are injected into SOUL template via soul_renderer.py with a memory context section | `_format_memory_context()` already has routing logic — gap is that review items fall through to fallback instead of primary path |
</phase_requirements>

## Summary

Phase 34 is a surgical correctness fix. The v1.3 memory system already has all plumbing in place — the payload builder (`_memorize_review_decision()` in `orchestration/snapshot.py`) and the SOUL formatter (`_format_memory_context()` in `skills/spawn_specialist/spawn.py`) are both already written. The integration gap is a single missing field: the memorize payload omits `"category": "review_decision"`, so when memU returns those memories via `/retrieve`, the formatter cannot route them to the "Past Review Outcomes" SOUL section via the primary `category == "review_decision"` path.

The formatter already has a dual-check fallback: `item.get("agent_type", "") == "l2_pm"` — but this relies on memU returning the `agent_type` field in retrieve results, which is not guaranteed. The correct fix is upstream: include `"category": "review_decision"` in the memorize payload so routing works via the explicit category field, not the fragile agent_type fallback.

The change is confined to one file (`snapshot.py`) and one dict. Tests already exist for the formatter behavior with `category: "review_decision"` items (`test_format_splits_work_and_review_memories`, `test_format_review_only_no_work_section`, etc.) — Phase 34 adds tests for the payload construction side to close the round-trip verification gap.

**Primary recommendation:** Add `"category": "review_decision"` to the `payload` dict in `_memorize_review_decision()` (one line), then add a unit test that intercepts the actual POST payload and asserts the category field is present.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (unittest.mock) | 3.x | Intercept httpx.Client POST inside daemon thread | Already used in test_l2_review_memorization.py |
| pytest | already installed | Test runner | Project standard |
| httpx | already installed | HTTP client used by `_post()` inner function | Already in spawn.py and snapshot.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading | stdlib | Daemon thread for fire-and-forget | Already used in `_memorize_review_decision()` |

**Installation:** No new dependencies required.

## Architecture Patterns

### The Payload Dict (snapshot.py lines 74-81)

Current structure — the gap is visible:

```python
payload = {
    "resource_url": content,
    "modality": "conversation",
    "user": {
        "user_id": project_id,
        "agent_type": AgentType.L2_PM.value,
    },
}
```

Fixed structure — add `"category"` at the top level:

```python
payload = {
    "resource_url": content,
    "modality": "conversation",
    "category": "review_decision",   # <-- THE FIX: single line addition
    "user": {
        "user_id": project_id,
        "agent_type": AgentType.L2_PM.value,
    },
}
```

The `"category"` field lives at the top level of the payload, not nested under `"user"`. This matches how `_format_memory_context()` retrieves it: `item.get("category", "")`.

### The Routing Logic (spawn.py lines 236-239)

Already correct — no changes needed to `_format_memory_context()`:

```python
is_review = (
    item.get("category", "") == "review_decision"
    or item.get("agent_type", "") == "l2_pm"
)
```

The primary path (`category == "review_decision"`) will now be hit for all new review memories. The `agent_type == "l2_pm"` fallback remains for backward compatibility with pre-fix memories already stored in memU without a category field.

### Test Pattern: Intercepting Payload Inside Thread

The existing test `test_content_includes_verdict_and_reasoning` (test_l2_review_memorization.py lines 184-229) demonstrates how to intercept the actual POST payload from inside the daemon thread's `_post()` inner function. Phase 34's category test should follow the same pattern from `test_diff_summary_truncated_to_500` (lines 333-366) — it runs the thread target synchronously and captures the payload:

```python
def fake_thread_factory(target=None, daemon=None, name=None):
    with patch("httpx.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
        MockClient.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock()
        target()  # run synchronously to capture payload
        if mock_client.post.called:
            payload_captured.append(mock_client.post.call_args[1]["json"])
    m = MagicMock()
    m.start = MagicMock()
    return m

with patch("orchestration.snapshot.threading.Thread", side_effect=fake_thread_factory):
    _memorize_review_decision(...)

assert payload_captured[0]["category"] == "review_decision"
```

### Round-Trip Test Pattern

The round-trip test (memorize with category → retrieve → format into correct section) works by:
1. Constructing a memory dict that simulates what memU would return (mimicking the stored payload structure)
2. Passing it to `_format_memory_context()` directly
3. Asserting it lands in "Past Review Outcomes"

This is a pure unit test — no actual memU service needed. The existing `test_format_splits_work_and_review_memories` already covers most of this pattern; the new test should explicitly verify items created by `_memorize_review_decision()` format correctly.

### Anti-Patterns to Avoid

- **Modifying `_format_memory_context()` routing logic**: The formatter is already correct. The fix belongs in the producer (`_memorize_review_decision()`), not the consumer.
- **Adding a constant/enum for the category string**: CONTEXT.md locks this as a plain string literal `"review_decision"`.
- **Touching `l2_memorize_task_outcome()` or similar functions**: CONTEXT.md locks scope to review decisions only.
- **Migrating existing stored memories**: CONTEXT.md explicitly prohibits this. Old memories without category route to "Past Work Context" via the default path.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Thread-safe payload capture in tests | Custom threading fixtures | Existing fake_thread_factory pattern (test_l2_review_memorization.py:333) | Already battle-tested in this codebase |
| Mock httpx.Client context manager | Custom mock class | `MagicMock()` with `__enter__`/`__exit__` | Standard pattern used throughout test suite |

## Common Pitfalls

### Pitfall 1: memU payload schema position

**What goes wrong:** Adding `"category"` inside the `"user"` dict instead of at the top level.
**Why it happens:** The `"user"` dict is close to where agent metadata lives.
**How to avoid:** Check how `_format_memory_context()` reads it — `item.get("category", "")` reads from the top-level dict, not `item["user"]["category"]`.
**Warning signs:** Test passes for category field presence but `_format_memory_context()` still routes to "Past Work Context".

### Pitfall 2: Test captures empty `payload_captured`

**What goes wrong:** `payload_captured` list is empty after the thread runs because the inner `patch("httpx.Client")` context is exited before `mock_client.post.called` is checked.
**Why it happens:** The context manager scope exits before the assertion.
**How to avoid:** Follow the exact pattern from `test_diff_summary_truncated_to_500` — check `if mock_client.post.called` inside the patch context, then assert outside using `payload_captured`.

### Pitfall 3: Backward compatibility test missing

**What goes wrong:** Adding category to new items without testing that items WITHOUT category still route correctly.
**Why it happens:** Focus on the new behavior, forgetting the regression guard.
**How to avoid:** CONTEXT.md explicitly requires: "Explicit test case required: verify items without category field route to default section". `test_format_work_only_no_review_section` partially covers this via items with no `category` key — verify it's already testing the right thing, or add a dedicated test.

## Code Examples

### The Complete Fix (snapshot.py)

```python
# orchestration/snapshot.py — _memorize_review_decision()
# Change: add "category": "review_decision" to payload dict

payload = {
    "resource_url": content,
    "modality": "conversation",
    "category": "review_decision",      # <-- ADD THIS LINE
    "user": {
        "user_id": project_id,
        "agent_type": AgentType.L2_PM.value,
    },
}
```

### New Test: Category Field in Payload (test_l2_review_memorization.py)

```python
@patch("orchestration.project_config.get_memu_config", return_value=_MEMU_CFG_ENABLED)
def test_memorize_review_decision_sends_category_field(mock_cfg):
    """Payload sent to memU includes category='review_decision'."""
    payload_captured = []

    def fake_thread_factory(target=None, daemon=None, name=None):
        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.post = MagicMock()
            target()
            if mock_client.post.called:
                payload_captured.append(mock_client.post.call_args[1]["json"])
        m = MagicMock()
        m.start = MagicMock()
        return m

    with patch("orchestration.snapshot.threading.Thread", side_effect=fake_thread_factory):
        _memorize_review_decision(
            project_id="proj",
            task_id="T-001",
            verdict="merge",
            reasoning="all tests pass",
        )

    assert payload_captured, "Thread target never called httpx.Client.post"
    assert payload_captured[0]["category"] == "review_decision"
```

### New Test: Round-Trip Category Routing (test_spawn_memory.py or new test file)

```python
def test_review_decision_category_routes_to_review_section():
    """Round-trip: memory stored with category='review_decision' routes to Past Review Outcomes."""
    # Simulate what memU returns after storing a review decision with category field
    memories = [
        {
            "resource_url": "# L2 Review Decision: task T-001\nVerdict: merge\nReasoning: all good",
            "category": "review_decision",
        }
    ]

    result = _format_memory_context(memories)

    assert "## Past Review Outcomes" in result
    assert "## Past Work Context" not in result
    assert "Verdict: merge" in result


def test_item_without_category_routes_to_work_context():
    """Backward compatibility: items without category field route to Past Work Context."""
    memories = [
        {"resource_url": "Legacy memory item with no category"},
    ]

    result = _format_memory_context(memories)

    assert "## Past Work Context" in result
    assert "## Past Review Outcomes" not in result
    assert "Legacy memory item with no category" in result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No category on review payloads → relies on agent_type fallback | Explicit `category: "review_decision"` in payload | Phase 34 | Primary routing path now works; fallback remains for legacy items |

## Open Questions

None — the fix is fully specified. Both the gap and the solution are unambiguous from code inspection.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none (pyproject.toml entry point) |
| Quick run command | `python3 -m pytest tests/ -v` |
| Full suite command | `python3 -m pytest tests/ -v` |
| Estimated runtime | ~0.3 seconds (55 tests currently) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MEM-02 | `_memorize_review_decision()` sends `category: "review_decision"` in payload | unit | `python3 -m pytest tests/test_l2_review_memorization.py -v -k category` | ❌ Wave 0 gap — new test needed |
| RET-02 | Items with `category == "review_decision"` route to "Past Review Outcomes" SOUL section | unit | `python3 -m pytest tests/test_spawn_memory.py -v -k review` | ✅ partially — `test_format_splits_work_and_review_memories` exists but round-trip test is missing |
| RET-02 | Items without `category` field route to "Past Work Context" (backward compat) | unit | `python3 -m pytest tests/test_spawn_memory.py -v -k work_only` | ✅ `test_format_work_only_no_review_section` covers this |

### Nyquist Sampling Rate

- **Minimum sample interval:** After each committed task → run: `python3 -m pytest tests/ -v`
- **Full suite trigger:** Before merging final task
- **Phase-complete gate:** Full suite green (55 + new tests) before verify-work
- **Estimated feedback latency per task:** ~0.3 seconds

### Wave 0 Gaps (must be created before implementation)

- [ ] New test in `tests/test_l2_review_memorization.py` — `test_memorize_review_decision_sends_category_field` — covers MEM-02 payload category assertion
- [ ] New test(s) in `tests/test_spawn_memory.py` — explicit round-trip test for `category == "review_decision"` routing to "Past Review Outcomes" and backward compat guard for items without category

*(The test infrastructure itself already exists — only new test functions needed, not new files or framework setup.)*

## Sources

### Primary (HIGH confidence)

- Direct code inspection of `~/.openclaw/orchestration/snapshot.py` — `_memorize_review_decision()` payload dict (lines 74-81)
- Direct code inspection of `~/.openclaw/skills/spawn_specialist/spawn.py` — `_format_memory_context()` routing logic (lines 230-259)
- Direct code inspection of `~/.openclaw/tests/test_l2_review_memorization.py` — thread interception test pattern (lines 333-366)
- Direct code inspection of `~/.openclaw/tests/test_spawn_memory.py` — all 38 tests including section-split tests

### Secondary (MEDIUM confidence)

N/A — all findings from direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — inspected actual source files, no external libs needed
- Architecture: HIGH — gap is visually obvious from payload dict vs formatter expectations
- Pitfalls: HIGH — identified from existing test patterns and code structure
- Test patterns: HIGH — copied from working tests in same codebase

**Research date:** 2026-02-24
**Valid until:** Indefinite — pure internal codebase fix, no external library dependencies
