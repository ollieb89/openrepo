# Phase 38: Phase 28 Verification + Dead Code Cleanup - Research

**Researched:** 2026-02-24
**Domain:** Documentation verification, dead code removal, technical debt closure
**Confidence:** HIGH

## Summary

Phase 38 is a two-concern cleanup phase with no new functionality. It closes the only missing VERIFICATION.md in the v1.3 milestone (Phase 28 has no formal verification despite having two plan SUMMARYs and 5 passing tests) and removes two pieces of confirmed dead code that accumulated during v1.3 development.

The verification gap is real but easily closed: Phase 28's implementation is fully tested by `tests/test_pool_memorization.py` (5 tests, all passing at 0.07s) and its requirements (MEM-01, MEM-03) were retroactively declared complete in Phase 33's VERIFICATION.md. The VERIFICATION.md for Phase 28 merely needs to be written — it is a documentation artifact, not a test gap.

The dead code consists of exactly two items, both confirmed by direct file inspection: (1) the `MEMU_SERVICE_URL` constant in `orchestration/memory_client.py` (line 29), which was the original default URL before `get_memu_config()` was established as the config source — it now exists only in the module docstring example (line 10) and is never called by any production path; (2) a stale "Placeholder" comment at line 75 of `docker/l3-specialist/entrypoint.sh`, flagged as an `Info`-level anti-pattern in Phase 33's VERIFICATION.md — the CLI invocation below it is fully implemented but the comment predates that implementation.

**Primary recommendation:** One plan, two tasks. Task 1 removes the two dead code items. Task 2 writes Phase 28's VERIFICATION.md using the existing test suite as evidence, cross-referencing Phase 33's requirement declarations.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MEM-01 | L3 task outcomes (semantic snapshots) are auto-memorized after successful container exit via fire-and-forget pattern | Already implemented in Phase 28 Plan 02; confirmed by 5 passing tests in `tests/test_pool_memorization.py`; VERIFICATION.md needed to formally document this |
| MEM-03 | Memorization failure is non-blocking — L3 task lifecycle and L2 review flow continue uninterrupted if memory service is unavailable | `test_memorize_exception_is_non_blocking` covers this; `MemoryClient.memorize()` catches all exceptions internally; belt-and-suspenders outer catch in `_memorize_snapshot_fire_and_forget()`; Phase 33 VERIFICATION.md declared it complete |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (stdlib) | 3.14 | Dead code removal — `del` statement or simple line delete | No library needed; direct file edit |
| Bash | POSIX | Comment removal in entrypoint.sh | Direct line edit |
| pytest | 9.0.2 | Confirming 5 existing tests still pass after cleanup | Already installed; `pytest.ini` in tests/ |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gsd-verifier format | internal | VERIFICATION.md schema with YAML frontmatter | Match all other 8 VERIFICATION.md files in the project |

**Installation:** No new packages required — all changes are file edits and a new markdown document.

---

## Architecture Patterns

### VERIFICATION.md Structure (from Phase 33 reference implementation)

All existing VERIFICATION.md files share the same YAML frontmatter + markdown body format. Phase 28's must match exactly.

```markdown
---
phase: 28-l3-auto-memorization
verified: 2026-02-24T00:00:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification: []
---

# Phase 28: L3 Auto-Memorization Verification Report
...
```

The body contains these sections (based on Phase 33 and Phase 27 examples):
- **Goal Achievement** — Observable Truths table (rows from plan must_haves.truths), Required Artifacts table, Key Link Verification table
- **Requirements Coverage** table — mapping MEM-01, MEM-03 to plan and evidence
- **Anti-Patterns Found** — list or "None"
- **Human Verification Required** — list or "None"
- **Gaps Summary** — count, and test results line

### Observable Truths for Phase 28 VERIFICATION.md

Derived directly from `28-02-PLAN.md` `must_haves.truths`:

1. After a successful L3 task completes, a memorize call is fired via asyncio.create_task (non-blocking) — covered by `test_memorize_called_on_success`
2. The pool slot is released before the memorize pipeline finishes (fire-and-forget) — architectural fact; `asyncio.create_task` schedules coroutine, `_attempt_task` returns before coroutine completes
3. When memU service is unreachable, the L3 task still completes successfully — covered by `test_memorize_exception_is_non_blocking`
4. Only successful task completions trigger memorization — code review of pool.py success branch only
5. Snapshot content is read from the .diff file on disk after container exit — covered by `test_snapshot_content_includes_header`

### Dead Code Removal Pattern

**`MEMU_SERVICE_URL` in `memory_client.py`:**
- The constant at line 29 (`MEMU_SERVICE_URL = os.environ.get(...)`) is not referenced by any production call path
- It appears in the module docstring example (line 10) as `MemoryClient(MEMU_SERVICE_URL, ...)` — this example in the docstring must also be updated (the example should show `get_memu_config()["memu_api_url"]` or a literal URL string to avoid referencing a removed name)
- No other file references `MEMU_SERVICE_URL` (confirmed: only `memory_client.py` contains it)
- The actual URL is read at call time via `get_memu_config()` in `pool.py` and `spawn.py` — the constant is truly dead

**Stale comment in `entrypoint.sh` line 75:**
- Lines 75-76 read:
  ```bash
  # Placeholder: actual CLI invocation will depend on runtime
  # This is the hook point where Claude Code / Codex / Gemini CLI runs
  ```
- The `if command -v "${CLI_RUNTIME}"` block directly below is fully implemented
- Removing both comment lines (75 and 76) leaves the code correct and unambiguous
- Phase 33's VERIFICATION.md already flagged this as an `Info`-level anti-pattern

### Anti-Patterns to Avoid

- **Removing `MEMU_SERVICE_URL` without updating the docstring example:** The module docstring at lines 7-13 uses `MEMU_SERVICE_URL` in the usage example. Removing the constant while leaving the docstring example creates a `NameError` if anyone copies the example. Update the docstring to use a literal URL string instead.
- **Creating a VERIFICATION.md that invents new tests:** Phase 38's job is to document what already exists, not to add tests. All 5 tests were written in Phase 28 Plan 02 and still pass.
- **Retroactively marking MEM-03 as "tested in Phase 38":** The requirement was already declared complete in Phase 33's VERIFICATION.md (Requirements Coverage table, row MEM-03). Phase 38's VERIFICATION.md should cross-reference Phase 33 as the source of that declaration rather than claiming new coverage.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Verifying the dead code is actually unused | Custom import graph analysis | `grep -rn "MEMU_SERVICE_URL"` across codebase | Already confirmed: only two lines in `memory_client.py` itself contain it |
| VERIFICATION.md format | Invent new schema | Copy Phase 33 or Phase 27 VERIFICATION.md YAML frontmatter verbatim | All 8 existing VERIFICATION.md files use the same schema — consistency is the goal |
| Re-running tests from scratch | Writing new tests | `python3 -m pytest tests/test_pool_memorization.py -v` | 5 tests already exist and pass at 0.07s |

---

## Common Pitfalls

### Pitfall 1: Incomplete Docstring Update After MEMU_SERVICE_URL Removal

**What goes wrong:** `MEMU_SERVICE_URL` is removed from the module body (line 29), but the module docstring example on line 10 still references it: `async with MemoryClient(MEMU_SERVICE_URL, ...)`. The file is syntactically valid Python but the docstring becomes misleading or broken if copy-pasted.

**Why it happens:** Dead code removal often focuses on the definition site (line 29) but overlooks usage in strings/comments.

**How to avoid:** Search for all occurrences of `MEMU_SERVICE_URL` in `memory_client.py` (there are exactly 2: line 10 in docstring, line 29 as definition). Update both. Replace the docstring example with a literal URL: `async with MemoryClient("http://localhost:18791", ...)`.

**Warning signs:** Grep of `MEMU_SERVICE_URL` still returns hits after the removal task.

### Pitfall 2: VERIFICATION.md Score Mismatch

**What goes wrong:** The YAML frontmatter says `score: 5/5 must-haves verified` but the Observable Truths table only has 4 rows (or 6). The number must match exactly.

**Why it happens:** The `must_haves.truths` list in `28-02-PLAN.md` has 5 items. If the VERIFICATION.md author adds or drops a truth during writing, the score diverges.

**How to avoid:** Count the truths in `28-02-PLAN.md` (there are exactly 5) and create one table row per truth. Set score to `5/5`.

### Pitfall 3: Wrong Phase Scope in VERIFICATION.md

**What goes wrong:** Phase 28 had two plans. Plan 01 covered MEM-04 (MEMU env var injection). Plan 02 covered MEM-01 and MEM-03 (fire-and-forget memorization). MEM-04 belongs to Phase 28 but was formally re-verified in Phase 33. The Phase 28 VERIFICATION.md should cover MEM-01 and MEM-03 (Plan 02's requirements) — its primary deliverable — while noting MEM-04 was also established here.

**Why it happens:** REQUIREMENTS.md traceability table maps MEM-01 to "Phase 37, 38" (a legacy error from Phase 33's partial declaration) and MEM-03 to Phase 38. The source of truth is the plan files: 28-02-PLAN.md has `requirements: [MEM-01, MEM-03]`.

**How to avoid:** Reference the plan frontmatter `requirements` field directly. MEM-04 was declared Complete in Phase 33's REQUIREMENTS.md update — mention it as a Plan 01 deliverable but don't re-verify it (it's covered in Phase 33 VERIFICATION.md).

### Pitfall 4: Entrypoint Comment Removal Breaks Surrounding Context

**What goes wrong:** Removing lines 75-76 from `entrypoint.sh` accidentally deletes the wrong lines if the editor is off-by-one.

**Why it happens:** The two lines are a two-line block. If the surrounding code (line 74: `update_state`, line 77: `if command -v`) is affected, the script breaks.

**How to avoid:** The removal is exactly lines 75-76:
```bash
# Placeholder: actual CLI invocation will depend on runtime
# This is the hook point where Claude Code / Codex / Gemini CLI runs
```
After removal, line 74 (`update_state "in_progress" "Executing task with ${CLI_RUNTIME}..."`) connects directly to line 77 (`if command -v "${CLI_RUNTIME}" &>/dev/null;`). Run `bash -n entrypoint.sh` after the edit to confirm syntax.

---

## Code Examples

### Exact Lines to Remove from memory_client.py

Line 29 (delete the constant definition):
```python
#: Default memU service URL — override via environment variable.
MEMU_SERVICE_URL = os.environ.get("MEMU_SERVICE_URL", "http://memu-server:18791")
```

Lines 7-13 (update docstring example — change `MEMU_SERVICE_URL` to literal URL):
```python
# Before (current):
    async with MemoryClient(MEMU_SERVICE_URL, "pumplai", AgentType.L3_CODE) as client:

# After (corrected):
    async with MemoryClient("http://localhost:18791", "pumplai", AgentType.L3_CODE) as client:
```

### Exact Lines to Remove from entrypoint.sh

Lines 75-76 (delete both comment lines, leave the `if` block untouched):
```bash
# Placeholder: actual CLI invocation will depend on runtime
# This is the hook point where Claude Code / Codex / Gemini CLI runs
```

Post-removal verification command:
```bash
bash -n /home/ollie/.openclaw/docker/l3-specialist/entrypoint.sh && echo "syntax OK"
```

### Phase 28 VERIFICATION.md Frontmatter

```yaml
---
phase: 28-l3-auto-memorization
verified: 2026-02-24T00:00:00Z
status: passed
score: 5/5 must-haves verified
gaps: []
human_verification: []
---
```

### Test Run Evidence for VERIFICATION.md

```bash
cd /home/ollie/.openclaw && python3 -m pytest tests/test_pool_memorization.py -v
# Result: 5 passed in 0.07s
```

Test list (from confirmed run):
1. `test_memorize_called_on_success` — PASSED
2. `test_memorize_not_called_when_url_empty` — PASSED
3. `test_memorize_exception_is_non_blocking` — PASSED
4. `test_agent_type_code_vs_test` — PASSED
5. `test_snapshot_content_includes_header` — PASSED

---

## State of the Art

| Old State | Current State After Phase 38 | Impact |
|-----------|------------------------------|--------|
| Phase 28 has 2 plan SUMMARYs but no VERIFICATION.md | Phase 28 has formal VERIFICATION.md with 5/5 truths verified | Milestone audit closure; no orphan phase |
| `MEMU_SERVICE_URL` dead constant in `memory_client.py` | Constant removed, docstring example uses literal URL | No misleading API surface; module docstring is accurate |
| Stale "Placeholder" comment in entrypoint.sh | Comment removed | Code matches implementation; no confusion for future maintainers |
| MEM-01 and MEM-03 "pending" in REQUIREMENTS.md traceability | MEM-01 and MEM-03 formally documented in Phase 28 VERIFICATION.md | Complete traceability chain for v1.3 milestone |

---

## Open Questions

1. **Should the module-level constant removal also remove the `os` import if it becomes unused?**
   - What we know: `memory_client.py` currently uses `os` only for `MEMU_SERVICE_URL = os.environ.get(...)`. If the constant is removed, `os` has no other uses in the file.
   - What's unclear: Whether removing the `os` import causes any downstream import chain issues (it shouldn't — standard library).
   - Recommendation: Remove the `import os` line as well if `os` has no other usages after the constant is deleted. Verify by searching `os.` in the file after the removal.

2. **Should REQUIREMENTS.md traceability table be updated to clarify Phase 38 as MEM-01/MEM-03 verification phase?**
   - What we know: The table currently maps MEM-01 to "Phase 37, 38" and MEM-03 to "Phase 38" with status "Pending". After this phase both should be "Complete".
   - Recommendation: Yes — update REQUIREMENTS.md traceability table as part of the plan (standard practice per all prior phases). Mark MEM-01 as "Phase 28, 38" (Phase 28 implemented it, Phase 38 formally verified it) and MEM-03 as "Phase 28, 38" with "Complete" status.

---

## Sources

### Primary (HIGH confidence)

- `/home/ollie/.openclaw/orchestration/memory_client.py` — direct inspection confirmed MEMU_SERVICE_URL at lines 10, 29; no other production callers
- `/home/ollie/.openclaw/docker/l3-specialist/entrypoint.sh` — direct inspection confirmed stale comment at lines 75-76
- `/home/ollie/.openclaw/tests/test_pool_memorization.py` — 5 tests confirmed; live test run confirmed all pass (0.07s)
- `/home/ollie/.openclaw/.planning/phases/28-l3-auto-memorization/28-02-PLAN.md` — source of truth for must_haves.truths (5 items) and requirements [MEM-01, MEM-03]
- `/home/ollie/.openclaw/.planning/phases/28-l3-auto-memorization/28-01-SUMMARY.md` and `28-02-SUMMARY.md` — what was actually built; confirms no VERIFICATION.md created at Phase 28 time
- `/home/ollie/.openclaw/.planning/phases/33-integration-gap-closure/33-VERIFICATION.md` — reference implementation for VERIFICATION.md format; confirmed MEM-01 and MEM-03 as pre-existing implementations
- `grep -rn "MEMU_SERVICE_URL"` — confirmed no external callers; only `memory_client.py` references the constant

### Secondary (MEDIUM confidence)

- All 8 existing VERIFICATION.md files reviewed (Phases 26, 27, 29, 30, 33, 34, 35, 36, 37) — consistent YAML frontmatter schema confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; pure file edits and markdown authoring
- Architecture: HIGH — directly verified by reading every file involved; no speculation
- Pitfalls: HIGH — derived from direct code analysis and cross-referencing existing VERIFICATION.md files

**Research date:** 2026-02-24
**Valid until:** Stable — all targets are static files with confirmed content; no external dependencies
