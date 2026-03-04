# Phase 30: L2 Review Decision Memorization - Research

**Researched:** 2026-02-24
**Domain:** Python synchronous fire-and-forget, snapshot.py call site injection, memU category tagging
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Memory content shape**
- Full context bundle per decision: verdict (merge/reject/conflict), free-text reasoning, diff summary, task type (code/test), and original task description
- Reasoning is free-text from L2 (not structured fields) — works well with semantic retrieval
- Task type (skill_type from spawn) is included for filtering capability
- Metadata tags: task_id + verdict + skill_type

**Trigger timing**
- Memorization fires AFTER the merge/reject/conflict resolution completes — decision must be final before storing
- Fire-and-forget pattern (consistent with Phase 28's L3 auto-memorization) — failure logged but does not block L2
- Merge conflicts that abort are also memorized as a distinct event type
- All decisions stored (no deduplication) — if a task is retried and reviewed again, both decisions persist for full narrative

**Rejection surfacing in future L3 SOULs**
- Structured warning block format: `## Past Review Outcomes` with entries like `- Task X was rejected: [reason]`
- Both merges AND rejections surface in future L3 SOULs — merges provide positive signal, rejections provide warnings
- SOUL injection separates review memories from work context memories: distinct `## Past Work Context` (Phase 28) and `## Past Review Outcomes` (Phase 30) sections

**Category and tagging**
- Review memories persist indefinitely — old rejections remain relevant for similar future work
- Metadata tags per memory item: task_id, verdict, skill_type

### Claude's Discretion
- Diff summary truncation/sizing approach
- memU category naming (single 'review_decision' vs split categories — align with Phase 28 patterns)
- Agent type naming (l2_pm vs l2_reviewer — align with existing conventions)
- Cap on how many review memories get injected into a single L3 SOUL

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-02 | L2 review decisions (merge/reject with reasoning) are memorized after each review cycle | Call site is inside `l2_merge_staging()` and `l2_reject_staging()` in `orchestration/snapshot.py`; fire-and-forget pattern via threading (sync context); MemoryClient.memorize() already sentinel-safe |
</phase_requirements>

---

## Summary

Phase 30 wires memorization into the L2 review cycle. The call sites are `l2_merge_staging()` and `l2_reject_staging()` in `orchestration/snapshot.py`. These are **synchronous functions** — unlike `pool.py` which is async, `snapshot.py` has no event loop. This changes the fire-and-forget implementation: instead of `asyncio.create_task()`, a `threading.Thread` must be used to fire the memorization without blocking the review cycle.

The memory content shape is a structured text block: verdict + reasoning + diff summary header + task metadata. The diff summary is already available from `capture_semantic_snapshot()` output (files_changed, insertions, deletions), which is typically called before the review decision. For the memorization content, the diff stat from `l2_review_diff()` is the correct source: it is available at review time, is human-readable, and is compact enough to include without truncation risk.

The SOUL injection side (surfacing past review outcomes to future L3 spawns) requires a second section in the memory context formatter in `spawn.py`. Currently, `_format_memory_context()` in `spawn.py` already has a forward-compatible `if category == "l2_review": tag = "(from L2 review)"` guard. Phase 30 must upgrade this into a proper `## Past Review Outcomes` section, separate from `## Past Work Context` (Phase 28/29 memories). The category name to use for review memories stored in memU drives this split.

**Primary recommendation:** Add `_memorize_review_decision()` as a synchronous threading.Thread-based fire-and-forget in `snapshot.py`. Call it as the last action inside `l2_merge_staging()` (success path), the conflict-abort path, and `l2_reject_staging()`. Upgrade `_format_memory_context()` in `spawn.py` to separate review memories (by category) into a distinct `## Past Review Outcomes` section.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| threading.Thread | stdlib | Fire-and-forget from sync context | snapshot.py is sync; asyncio.create_task() is not available without a running event loop |
| httpx.Client (sync) | 0.27+ | HTTP call inside thread | Same pattern as `_retrieve_memories_sync()` in spawn.py (Phase 29 decision); avoids async/event-loop complexity |
| MemoryClient (async) | Phase 27 | memU REST API wrapper | Already exists; but NOT usable from sync thread — use httpx.Client directly instead (same pattern as spawn.py) |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| orchestration.project_config.get_memu_config | existing | Read MEMU_API_URL from openclaw.json | Already used by pool.py and spawn.py; same pattern here |
| orchestration.memory_client.AgentType | existing | Enum for agent type tagging | AgentType.L2_PM already defined; correct value for L2 review decisions |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| threading.Thread | asyncio.create_task | asyncio.create_task requires running event loop; snapshot.py is sync, called from L2 agent (no event loop) |
| threading.Thread | concurrent.futures.ThreadPoolExecutor | ThreadPoolExecutor is overkill for one-shot fire-and-forget; thread.start() with daemon=True is simpler |
| threading.Thread | asyncio.run() inside thread | asyncio.run() in a sync context works but adds complexity; plain httpx.Client is cleaner |
| Direct httpx.Client | MemoryClient (async) | MemoryClient is async-only; sync thread needs sync HTTP; httpx.Client (sync) already established by Phase 29 |

**Installation:** No new packages required — threading is stdlib, httpx already installed.

---

## Architecture Patterns

### Recommended Project Structure

No new files required. Changes are additive to:

```
orchestration/
└── snapshot.py     # + _memorize_review_decision_async() helper + thread calls in l2_merge_staging() / l2_reject_staging()

skills/spawn_specialist/
└── spawn.py        # + _format_review_outcomes() helper or upgrade _format_memory_context() to split by category

tests/
└── test_l2_review_memorization.py  # new — unit tests for memorization helper and SOUL section injection
```

### Pattern 1: Fire-and-Forget from Sync Context via threading.Thread

**What:** Launch a daemon thread to perform the memU POST after the review decision completes. The thread is daemon=True so it does not block process exit.

**When to use:** Any time fire-and-forget is needed inside a synchronous function with no asyncio event loop.

**Why daemon=True:** L2 agent process must not be kept alive by pending memorization. If the process exits before the thread finishes, the memorization is silently dropped — this is the correct fire-and-forget behavior (non-blocking, non-critical).

**Example (based on Phase 29 _retrieve_memories_sync pattern):**

```python
# In orchestration/snapshot.py

import threading
from orchestration.project_config import get_memu_config
from orchestration.memory_client import AgentType

def _memorize_review_decision(
    project_id: str,
    task_id: str,
    verdict: str,           # "merge", "reject", or "conflict"
    reasoning: str,         # Free-text from L2 agent
    diff_summary: str,      # Compact stat string from l2_review_diff()['stat']
    skill_type: str = "",   # "code", "test", or "" if unknown
) -> None:
    """
    Fire-and-forget memorization of L2 review decision.

    Launches a daemon thread to POST to memU. Never raises. Returns immediately.
    Called AFTER the merge/reject/conflict action completes — decision is final.
    """
    memu_cfg = get_memu_config()
    base_url = memu_cfg.get("memu_api_url", "").strip()
    if not base_url or not project_id:
        logger.debug(
            "MEMU_API_URL not configured -- skipping review memorization",
            extra={"task_id": task_id},
        )
        return

    # Build memory content
    diff_section = f"\n\nDiff summary:\n{diff_summary.strip()}" if diff_summary.strip() else ""
    content = (
        f"# L2 Review Decision: task {task_id}\n"
        f"Verdict: {verdict}\n"
        f"Task type: {skill_type}\n"
        f"Reasoning: {reasoning}"
        f"{diff_section}"
    )

    def _post() -> None:
        import httpx
        payload = {
            "resource_url": content,
            "modality": "conversation",
            "user": {
                "user_id": project_id,
                "agent_type": AgentType.L2_PM.value,
            },
            "metadata": {
                "task_id": task_id,
                "verdict": verdict,
                "skill_type": skill_type,
                "category": "review_decision",
            },
        }
        try:
            with httpx.Client(base_url=base_url, timeout=httpx.Timeout(10.0, connect=2.0)) as client:
                response = client.post("/memorize", json=payload)
                response.raise_for_status()
                logger.info(
                    "Review decision memorized",
                    extra={"task_id": task_id, "verdict": verdict, "project_id": project_id},
                )
        except Exception as exc:
            logger.warning(
                "Review memorization failed (non-blocking)",
                extra={"task_id": task_id, "verdict": verdict, "error": str(exc)},
            )

    t = threading.Thread(target=_post, daemon=True, name=f"memu-review-{task_id}")
    t.start()
```

### Pattern 2: Call Site in l2_merge_staging()

**What:** Three verdict paths exist inside `l2_merge_staging()`: success, conflict-abort, and GitOperationError. Only success and conflict need memorization. GitOperationError is a programming error, not a review decision.

```python
# In l2_merge_staging() — SUCCESS PATH (after branch deletion):
def l2_merge_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",        # NEW param: free-text from L2
    skill_type: str = "",       # NEW param: code/test
    project_id: Optional[str] = None,  # NEW param: for memU scoping
) -> Dict[str, Any]:
    ...
    # At end of success path, before return:
    _memorize_review_decision(
        project_id=project_id or "",
        task_id=task_id,
        verdict="merge",
        reasoning=reasoning,
        diff_summary="",   # diff already merged; stat not available post-merge
        skill_type=skill_type,
    )
    return {"success": True, ...}

    # At end of conflict-abort path:
    _memorize_review_decision(
        project_id=project_id or "",
        task_id=task_id,
        verdict="conflict",
        reasoning=reasoning or f"Merge conflict in task {task_id}",
        diff_summary=merge_result.stderr[:500],
        skill_type=skill_type,
    )
    return {"success": False, "message": ..., "conflicts": conflicts}
```

### Pattern 3: Call Site in l2_reject_staging()

```python
def l2_reject_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",        # NEW param: free-text from L2
    skill_type: str = "",       # NEW param: code/test
    project_id: Optional[str] = None,  # NEW param: for memU scoping
) -> Dict[str, Any]:
    ...
    # After branch deletion, before return:
    _memorize_review_decision(
        project_id=project_id or "",
        task_id=task_id,
        verdict="reject",
        reasoning=reasoning,
        diff_summary="",
        skill_type=skill_type,
    )
    return {"success": True, ...}
```

### Pattern 4: SOUL Section Split in spawn.py

**What:** `_format_memory_context()` in `spawn.py` currently generates a single `## Memory Context` section for all memory types. Phase 30 requires splitting this into two distinct sections — `## Past Work Context` (l3_outcome memories from Phase 28) and `## Past Review Outcomes` (review_decision memories from Phase 30).

**Category discriminator:** The `category` field in memU items (or the `agent_type` field in the payload user) identifies the origin. The current `_format_memory_context()` already has `if category == "l2_review": tag = "(from L2 review)"`. Phase 30 needs to use a consistent category name — use `"review_decision"` to align with the Phase 28 `"l3_outcome"` convention.

**Implementation approach:** Split the memory list into two groups before formatting. Items with `category == "review_decision"` go into `## Past Review Outcomes`; all others go into `## Past Work Context`. Both sections share the 2,000-char budget.

```python
# Upgraded _format_memory_context() in spawn.py:
def _format_memory_context(memories: list) -> str:
    """
    Format retrieved memories into two SOUL sections:
    - ## Past Work Context: l3_outcome memories (Phase 28)
    - ## Past Review Outcomes: review_decision memories (Phase 30)

    Total character budget across both sections: MEMORY_CONTEXT_BUDGET.
    """
    if not memories:
        return ""

    work_bullets = []
    review_bullets = []
    total_chars = 0

    for item in memories:
        text = item.get("resource_url", "") or item.get("content", "") or ""
        if not text:
            continue
        category = item.get("category", "")
        is_review = (category == "review_decision")

        bullet = f"- {text}"
        candidate = total_chars + len(bullet) + 1
        if candidate > MEMORY_CONTEXT_BUDGET:
            break

        if is_review:
            review_bullets.append(bullet)
        else:
            work_bullets.append(bullet)
        total_chars += len(bullet) + 1

    sections = []
    if work_bullets:
        sections.append("## Past Work Context\n\n" + "\n".join(work_bullets))
    if review_bullets:
        sections.append("## Past Review Outcomes\n\n" + "\n".join(review_bullets))

    return "\n\n".join(sections) if sections else ""
```

**Cap on review memories injected:** Claude's discretion. Recommendation: no separate cap. The shared 2,000-char budget already caps total injection. Review memories are typically smaller than l3_outcome snapshots (which contain full diffs), so in practice review memories will not dominate the budget.

### Pattern 5: memU payload metadata field usage

The current `MemoryClient.memorize()` does not include a `metadata` field in the payload — it sends only `resource_url`, `modality`, and `user`. The metadata tags (task_id, verdict, skill_type) specified in the CONTEXT.md decisions could be stored either:

1. **In the content string** (approach used for l3_outcome): prefix the text with structured header lines
2. **As a separate `metadata` field** in the memU payload (if the API supports it)

From Phase 26/27 research, `memu-py` accepts a `metadata` dict in the memorize request. However, `MemoryClient.memorize()` does not expose this. Since we are calling `httpx.Client` directly in the thread (not via `MemoryClient`), we can include `metadata` in the payload directly. The content string header approach (Pattern 1 example above) is sufficient for semantic retrieval without depending on metadata field support.

**Recommendation:** Use content-embedded metadata (header lines) for the primary memory text. Optionally include metadata dict in the raw POST if the memU API is known to support it — but treat it as optional decoration, not the retrieval mechanism.

### Anti-Patterns to Avoid

- **Awaiting or joining the thread:** `t.join()` would block the review cycle — exactly what fire-and-forget must prevent.
- **Using asyncio.create_task() in snapshot.py:** snapshot.py functions are sync; no event loop is running when they are called by L2 agent scripts. asyncio.create_task() would raise `RuntimeError: no running event loop`.
- **Memorizing before the decision is final:** The merge/conflict paths inside `l2_merge_staging()` can raise `GitOperationError` — do not call `_memorize_review_decision()` inside a try/except around git ops; call it only after the git operation result is known.
- **Using MemoryClient (async) inside the thread:** The thread has its own stack; calling `asyncio.run(MemoryClient.memorize(...))` inside a daemon thread works but is fragile if a parent event loop exists. Use `httpx.Client` (sync) directly as in Phase 29's `_retrieve_memories_sync()`.
- **Adding reasoning/project_id as required params without defaults:** `l2_merge_staging()` and `l2_reject_staging()` are public API functions exported from `orchestration/__init__.py`. Any L2 caller that does not pass the new params must still work. All new params must have safe defaults (`reasoning=""`, `project_id=None`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fire-and-forget from sync | Custom thread pool, queue, or asyncio | `threading.Thread(daemon=True)` | One-shot; no retry; stdlib; matches project pattern |
| memU HTTP POST | Custom requests wrapper | `httpx.Client` (same as _retrieve_memories_sync in spawn.py) | Already installed; already tested pattern in project |
| Agent type for L2 | New string constant | `AgentType.L2_PM` from memory_client.py | Already defined; `.value` gives "l2_pm" for JSON |
| MEMU URL resolution | Inline openclaw.json parse | `get_memu_config()` from project_config.py | Already exists; tested; handles missing config gracefully |

**Key insight:** The entire memorization infrastructure (MemoryClient, AgentType, get_memu_config, httpx) already exists. Phase 30 is integration work: adding the call sites to snapshot.py and upgrading the SOUL formatter in spawn.py.

---

## Common Pitfalls

### Pitfall 1: snapshot.py is sync — asyncio.create_task() will fail

**What goes wrong:** `asyncio.create_task()` raises `RuntimeError: no running event loop` when called from a synchronous context (no event loop running).

**Why it happens:** `snapshot.py` functions are called by L2 agents (AI processes), not from within an asyncio event loop. Unlike `pool.py` (which is async), `snapshot.py` is pure sync.

**How to avoid:** Use `threading.Thread(daemon=True)` instead of `asyncio.create_task()`. This is the correct pattern for fire-and-forget from sync code.

**Warning signs:** `RuntimeError: no running event loop` on `asyncio.create_task()` call.

### Pitfall 2: project_id not available inside snapshot.py functions

**What goes wrong:** `l2_merge_staging()` and `l2_reject_staging()` do not currently receive `project_id` as a parameter. Without it, `_memorize_review_decision()` cannot scope the memory to the correct project.

**Why it happens:** The snapshot.py functions predate the project-scoping architecture. `state_file` was the original project identifier (the state file path encodes the project: `workspace/.openclaw/{project_id}/workspace-state.json`).

**How to avoid:** Add `project_id: Optional[str] = None` as a new keyword-only parameter to both `l2_merge_staging()` and `l2_reject_staging()`. Use safe default `None` to preserve backward compatibility. When `project_id` is None, fall back to `get_active_project_id()` — same pattern used throughout the project.

Alternatively: extract `project_id` from `state_file` path if state_file is provided (`state_file.parent.name` when path is `.../{project_id}/workspace-state.json`). This is fragile — prefer explicit `project_id` param.

**Warning signs:** Memories stored without project scoping (user_id empty) — all projects would see each other's review memories.

### Pitfall 3: reasoning param is empty string when L2 agent doesn't pass it

**What goes wrong:** All existing callers of `l2_merge_staging()` and `l2_reject_staging()` do not pass `reasoning`. The stored memory would say `Reasoning: ` (empty) for all historical data.

**Why it happens:** These are new parameters on existing public functions.

**How to avoid:** The default behavior (empty reasoning) is acceptable — memory is still stored with verdict + task_id + task_type. The content degrades gracefully to less informative but not broken. Document in the function docstring that `reasoning` is recommended for rich memory context.

**Warning signs:** All stored review memories have empty reasoning — still functional but less useful for L3 retrieval.

### Pitfall 4: diff_summary from l2_review_diff() may be large

**What goes wrong:** `l2_review_diff()` returns `stat` (short, file list + counts) and `diff` (full patch, potentially megabytes). Including the full diff in the memory content would produce giant memory entries and slow embedding.

**Why it happens:** Temptation to include the full diff for richness.

**How to avoid:** Use only the `stat` field from `l2_review_diff()` in the memory content. This gives the reviewer's context (files changed, insertions, deletions) without the full patch. Truncate `stat` to ~500 chars if needed. The full semantic snapshot (diff) is already stored separately by Phase 28.

**Warning signs:** Memory entries exceeding memU's max content size; slow memorization thread.

### Pitfall 5: Thread not started if project_id is None and get_active_project_id() raises

**What goes wrong:** `get_active_project_id()` raises `FileNotFoundError` or `ValueError` if openclaw.json is missing or has no active project. The thread creation itself would fail before starting.

**Why it happens:** `_memorize_review_decision()` calls `get_memu_config()` and conditionally `get_active_project_id()` — both can fail.

**How to avoid:** Wrap the entire `_memorize_review_decision()` body (including thread creation) in a try/except that logs and returns silently. This is the same pattern as all other memory helpers: never raise from memorization helpers.

### Pitfall 6: category field not returned by memU /retrieve

**What goes wrong:** The SOUL injection split (Pattern 4) depends on the `category` field being present in /retrieve response items. If memU does not echo back the `category` metadata in retrieve results, the split will not work.

**Why it happens:** The `category` parameter in `MemoryClient.memorize()` is passed in the payload but memU's /retrieve response format may not include it.

**How to avoid:** Inspect Phase 26/27 retrieve response shape. From `memory_client.py` code: retrieve returns items from memU directly. If `category` is not in the response, fall back to discriminating by `agent_type` field: items with `agent_type == "l2_pm"` are review decisions; others are l3_outcome memories. Both fields should be available in the stored record — verify in the implementation task.

**Warning signs:** SOUL section always empty for `## Past Review Outcomes` despite stored memories.

---

## Code Examples

### Complete _memorize_review_decision implementation

```python
# Source: threading stdlib docs + Phase 29 _retrieve_memories_sync pattern
import threading

def _memorize_review_decision(
    project_id: str,
    task_id: str,
    verdict: str,
    reasoning: str,
    diff_summary: str = "",
    skill_type: str = "",
) -> None:
    """
    Fire-and-forget memorization of L2 review decision. Never raises. Returns immediately.

    Launches a daemon thread to POST the decision to memU. The thread is daemon=True
    so it does not block process exit if still running when L2 agent process exits.

    Args:
        project_id:   Project scope for memU user_id isolation.
        task_id:      L3 task identifier.
        verdict:      "merge", "reject", or "conflict".
        reasoning:    Free-text explanation from L2 agent.
        diff_summary: Short stat string from l2_review_diff()['stat'] (optional).
        skill_type:   "code", "test", or "" if unknown.
    """
    from orchestration.project_config import get_memu_config
    from orchestration.memory_client import AgentType

    try:
        memu_cfg = get_memu_config()
        base_url = memu_cfg.get("memu_api_url", "").strip()
        if not base_url or not project_id:
            logger.debug(
                "MEMU_API_URL not configured -- skipping review memorization",
                extra={"task_id": task_id},
            )
            return

        diff_section = f"\n\nDiff summary:\n{diff_summary[:500].strip()}" if diff_summary.strip() else ""
        content = (
            f"# L2 Review Decision: task {task_id}\n"
            f"Verdict: {verdict}\n"
            f"Task type: {skill_type}\n"
            f"Reasoning: {reasoning}"
            f"{diff_section}"
        )

        def _post() -> None:
            import httpx
            payload = {
                "resource_url": content,
                "modality": "conversation",
                "user": {
                    "user_id": project_id,
                    "agent_type": AgentType.L2_PM.value,
                },
            }
            try:
                with httpx.Client(
                    base_url=base_url,
                    timeout=httpx.Timeout(10.0, connect=2.0),
                ) as client:
                    response = client.post("/memorize", json=payload)
                    response.raise_for_status()
                    logger.info(
                        "Review decision memorized",
                        extra={"task_id": task_id, "verdict": verdict, "project_id": project_id},
                    )
            except Exception as exc:
                logger.warning(
                    "Review memorization failed (non-blocking)",
                    extra={"task_id": task_id, "verdict": verdict, "error": str(exc)},
                )

        t = threading.Thread(target=_post, daemon=True, name=f"memu-review-{task_id}")
        t.start()

    except Exception as exc:
        logger.warning(
            "Failed to launch review memorization thread",
            extra={"task_id": task_id, "error": str(exc)},
        )
```

### Function signature additions to snapshot.py public functions

```python
def l2_merge_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",
    skill_type: str = "",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    ...

def l2_reject_staging(
    task_id: str,
    workspace_path: str,
    state_file: Optional[Path] = None,
    reasoning: str = "",
    skill_type: str = "",
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    ...
```

### Upgraded _format_memory_context in spawn.py

```python
def _format_memory_context(memories: list) -> str:
    """
    Format retrieved memories into two distinct SOUL sections:
    - ## Past Work Context: l3_outcome memories (Phase 28)
    - ## Past Review Outcomes: review_decision memories (Phase 30)

    Budget: MEMORY_CONTEXT_BUDGET characters shared across both sections.
    Items are added in rank order; whole items dropped (not truncated) when budget exhausted.
    """
    if not memories:
        return ""

    work_bullets = []
    review_bullets = []
    total_chars = 0

    for item in memories:
        text = item.get("resource_url", "") or item.get("content", "") or ""
        if not text:
            continue

        # Discriminate by category or agent_type
        category = item.get("category", "")
        agent_type = item.get("agent_type", "")
        is_review = (category == "review_decision") or (agent_type == "l2_pm")

        bullet = f"- {text}"
        candidate = total_chars + len(bullet) + 1
        if candidate > MEMORY_CONTEXT_BUDGET:
            break

        if is_review:
            review_bullets.append(bullet)
        else:
            work_bullets.append(bullet)
        total_chars += len(bullet) + 1

    sections = []
    if work_bullets:
        sections.append("## Past Work Context\n\n" + "\n".join(work_bullets))
    if review_bullets:
        sections.append("## Past Review Outcomes\n\n" + "\n".join(review_bullets))

    return "\n\n".join(sections) if sections else ""
```

---

## Critical Discovery: L2 Review Functions Have No Active Callers in Python Source

Confirmed by exhaustive grep across the codebase: `l2_merge_staging()` and `l2_reject_staging()` are defined in `snapshot.py`, re-exported from `orchestration/__init__.py`, but **not called from any other Python or JS file in the project**. They are the API that L2 (an AI agent process) calls when it runs review decisions — the AI agent directly invokes these functions as part of its workflow.

This means:
1. The call site injection approach (adding `_memorize_review_decision()` call at the end of each function) is correct — there is no controller or pool wrapper to hook into instead.
2. The new `reasoning`, `skill_type`, and `project_id` params will be passed by the L2 agent when it calls these functions — the AI agent is responsible for supplying context. This is the correct design: the agent knows its reasoning.
3. No existing callers will break from the new optional params (they have safe defaults).

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Phase 28 fire-and-forget via asyncio.create_task | Phase 30 fire-and-forget via threading.Thread | Necessary change — snapshot.py is sync; pool.py is async |
| Single `## Memory Context` section in SOUL | Two sections: `## Past Work Context` + `## Past Review Outcomes` | Better signal separation for L3 agent |
| `_format_memory_context()` with `(from L2 review)` tag stub | Full section-split formatter | Fulfills Phase 29's forward-compatible stub |

---

## Open Questions

1. **Does memU /retrieve echo back the `category` or `agent_type` field in items?**
   - What we know: MemoryClient.memorize() sends `user.agent_type` in the payload. The retrieve response shape returns items from memu-py's retrieve() result.
   - What's unclear: Whether `agent_type` or any metadata appears in retrieve response items.
   - Recommendation: Implement the discriminator with both `category == "review_decision"` AND `agent_type == "l2_pm"` as fallback. One of these will be present. Verify in the implementation task by inspecting a real retrieve response.

2. **Should diff_summary be passed to _memorize_review_decision() from the call sites?**
   - What we know: `l2_merge_staging()` does not have the stat summary available after the merge completes (the branch is deleted). `l2_reject_staging()` similarly has no diff at rejection time.
   - What's unclear: Should the caller (L2 agent) be expected to call `l2_review_diff()` first and pass the stat to `l2_merge_staging()` / `l2_reject_staging()`?
   - Recommendation: Add `diff_summary: str = ""` as an optional parameter. Make it the caller's responsibility to pass if they want it. The memory is still useful without it (verdict + reasoning alone has high retrieval value). Default to empty — do not require callers to call `l2_review_diff()` first.

3. **Agent type naming: l2_pm or l2_reviewer?**
   - What we know: `AgentType.L2_PM = "l2_pm"` is already defined in `memory_client.py`. No `l2_reviewer` variant exists.
   - Recommendation: Use `AgentType.L2_PM`. Adding a new `L2_REVIEWER` variant would create confusion and serve no retrieval benefit — all L2 operations are from the PM tier.

4. **Category naming: review_decision vs l2_review?**
   - What we know: The current `_format_memory_context()` stub in spawn.py checks `category == "l2_review"`. Phase 28 uses `"l3_outcome"` which follows `{tier}_{event}` convention.
   - Recommendation: Use `"review_decision"` for the stored category (more descriptive, self-explanatory). Update the stub in `_format_memory_context()` from `"l2_review"` to `"review_decision"`. Alternatively, keep the existing stub and store as `"l2_review"` — but `"review_decision"` is clearer.

---

## Sources

### Primary (HIGH confidence)

- `~/.openclaw/orchestration/snapshot.py` — `l2_merge_staging()` and `l2_reject_staging()` full implementations; three verdict paths identified (success, conflict-abort, GitOperationError); no existing callers
- `~/.openclaw/skills/spawn_specialist/spawn.py` — `_retrieve_memories_sync()` (sync httpx.Client pattern), `_format_memory_context()` (forward-compatible `category == "l2_review"` stub), `_build_augmented_soul()` (two-section SOUL structure)
- `~/.openclaw/skills/spawn_specialist/pool.py` — `_memorize_snapshot_fire_and_forget()` (asyncio.create_task pattern; confirmed correct for async context only)
- `~/.openclaw/orchestration/memory_client.py` — `AgentType.L2_PM = "l2_pm"`, `MemoryClient.memorize()` payload shape, sentinel degradation pattern
- `~/.openclaw/orchestration/project_config.py` — `get_memu_config()` (already exists; returns memu_api_url + enabled)
- `~/.openclaw/orchestration/__init__.py` — confirmed export of `l2_merge_staging`, `l2_reject_staging`; exhaustive caller search confirms no active callers
- `~/.openclaw/tests/pytest.ini` — `asyncio_mode = auto`; test framework confirmed
- Python 3 stdlib docs — `threading.Thread(daemon=True)` pattern for fire-and-forget from sync context

### Secondary (MEDIUM confidence)

- Phase 28 RESEARCH.md — fire-and-forget pattern using asyncio.create_task; clarifies why threading is needed for sync context
- Phase 29 SUMMARY.md — MagicMock (not AsyncMock) pattern for sync httpx.Client in tests; SOUL injection separation requirement confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in codebase; threading.Thread is stdlib
- Architecture: HIGH — call sites verified by direct code reading; no callers exist so injection into snapshot.py functions is unambiguous
- Pitfalls: HIGH — derived from direct analysis of sync vs async context, existing public API constraints, memU payload shape

**Research date:** 2026-02-24
**Valid until:** Stable — implementation targets sync Python stdlib and internal modules; no fast-moving dependencies
