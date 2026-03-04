# Phase 44: v1.4 Tech Debt Cleanup — Research

**Researched:** 2026-02-25
**Domain:** Documentation gaps, TypeScript parse error, Python test patch paths
**Confidence:** HIGH

---

## Summary

Phase 44 addresses three discrete tech debt items identified by the v1.4 milestone audit. Each item is fully understood — no unknown dependencies, no new libraries needed, no architectural decisions to make. This is a pure cleanup phase.

**Item 1 — Documentation gap (Makefile + README):** `OPENCLAW_ROOT` must be exported into the shell environment before starting the dashboard, because `execFileAsync` in the Next.js API route for suggestions inherits its env from the server process. If unset, `suggest.py` falls back to resolving paths relative to its own file location inside `packages/orchestration/src/`, which lands `soul-suggestions.json` at the wrong path and ADV-03 silently returns empty state. The fix is purely documentation — a comment in the Makefile `dashboard` target and a note in the README Dashboard section.

**Item 2 — SummaryStream.tsx parse error (line 44):** The file contains a literal newline character embedded in a `buffer.split('...')` call. The split delimiter should be the escape sequence `'\n'` but instead the file has a raw newline, splitting the string literal across two source lines (44 and 45). This causes a TypeScript/JavaScript parse error ("unterminated string literal"). The fix is a one-line edit replacing the raw newline with `\n`.

**Item 3 — Stale patch paths (test_l2_review_memorization.py + test_pool_memorization.py):** The audit flagged these files as potentially containing pre-refactor `orchestration.*` patch targets. Upon inspection, both files already use correct `openclaw.*` module paths (e.g., `patch("openclaw.snapshot.threading.Thread")`, `patch("openclaw.memory_client.MemoryClient")`). Tests pass cleanly with no warnings (148/148 green) when run via `uv run pytest` from `packages/orchestration`. The patch targets in `test_pool_memorization.py` that use `pool.get_memu_config` are correct because `skills/spawn/` is on sys.path and `pool` is the bare module name. No changes are required to patch paths — only verification is needed to confirm and document the finding.

**Primary recommendation:** Implement all three items in a single plan wave. Items 1 and 2 are independent one-shot edits. Item 3 requires running tests with `-W all` to confirm no MagicMock warnings, then documenting the finding as resolved.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Python `unittest.mock.patch` | stdlib | Target verification | Already in use throughout test suite |
| TypeScript | project-native | SummaryStream.tsx fix | Language of the dashboard |
| Makefile | project-native | Documentation target comments | Already the primary dev command interface |

No new libraries are needed. All tooling is already in place.

---

## Architecture Patterns

### Pattern 1: `patch()` Target Resolution in Python

**What:** When `unittest.mock.patch("module.symbol")` is used, Python resolves the module name at runtime using the same `sys.modules` namespace as the importing code. If a module is imported as `pool` (bare name from sys.path) then the correct patch target is `"pool.symbol"`, not `"orchestration.pool.symbol"` or `"openclaw.pool.symbol"`.

**Current state in this codebase:**
- `skills/spawn/pool.py` is on sys.path via conftest. Patch targets use `pool.*` — this is correct.
- `openclaw.snapshot`, `openclaw.memory_client`, `openclaw.project_config` are installed package paths. Patch targets use `openclaw.*` — this is correct.
- There are no remaining `orchestration.*` patch targets in the test suite. The refactor cleanup already happened.

**Verification command:**
```bash
cd packages/orchestration && uv run pytest tests/test_l2_review_memorization.py tests/test_pool_memorization.py -v -W all
```
Expected: 17 passed, 0 warnings.

### Pattern 2: Makefile Documentation Comment Placement

**What:** Environment variable prerequisites are documented as inline comments on the relevant `make` target, not as separate doc-only targets. This makes the dependency visible exactly where the user will run the command.

**Example pattern:**
```makefile
dashboard: ## Start dashboard dev server (port 6987) — requires OPENCLAW_ROOT to be exported
	@if [ -z "$$OPENCLAW_ROOT" ]; then echo "ERROR: OPENCLAW_ROOT must be exported. Example: export OPENCLAW_ROOT=$$HOME/.openclaw"; exit 1; fi
	cd packages/dashboard && bun install && bun run dev
```

Or a softer warning-only form:
```makefile
dashboard: ## Start dashboard dev server (port 6987)
	@[ -n "$$OPENCLAW_ROOT" ] || echo "WARNING: OPENCLAW_ROOT is unset — suggest.py will use wrong path. Run: export OPENCLAW_ROOT=$$HOME/.openclaw"
	cd packages/dashboard && bun install && bun run dev
```

The guard form (exit 1) is stronger and prevents silent failures on fresh deployments. The warning form preserves current behavior for existing deployments. **Recommendation: use the guard form** — the audit item is specifically about silent ADV-03 failures on fresh deployments.

### Pattern 3: TypeScript Literal Newline Fix

**What:** The file `~/.openclaw/packages/dashboard/src/components/sync/SummaryStream.tsx` has a literal newline at line 44 inside a string literal:

```
Line 43: "          buffer += decoder.decode(value, { stream: true });"
Line 44: "          const lines = buffer.split('"        ← string starts
Line 45: "');"                                            ← newline + string ends → parse error
```

**Fix:** Replace with the escape sequence `\n`:
```typescript
const lines = buffer.split('\n');
```

The file uses `'use client'` directive confirming it's a Next.js client component. The fix is a character-level substitution.

### Anti-Patterns to Avoid

- **Documenting env var only in README:** Users who run `make dashboard` without reading README will hit the silent failure. Put the guard in the Makefile too.
- **Softening the parse error fix:** The literal newline is unambiguously wrong. Fix it completely to `'\n'` — do not introduce `\r\n` or template literals.
- **Changing patch targets that are correct:** The `orchestration.*` concern from the audit is already resolved. Do not "fix" working patch targets.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var guard in Makefile | Custom shell script | `@[ -n "$$VAR" ] || echo/exit` inline | One-liner suffices; Makefile already owns this |
| Test path verification | New test harness | `uv run pytest tests/ -v -W all` | Existing pytest surfaces any MagicMock warnings |

---

## Common Pitfalls

### Pitfall 1: Double `$$` in Makefile Shell Expressions

**What goes wrong:** Writing `$OPENCLAW_ROOT` instead of `$$OPENCLAW_ROOT` in a Makefile recipe. Single `$` is interpreted by Make as a Make variable — it expands to empty string silently.

**How to avoid:** Always double the `$` for shell variable access in Makefile recipes: `$$OPENCLAW_ROOT`, `$$HOME`, etc.

**Warning sign:** The guard always passes (never fires) even when the variable is unset.

### Pitfall 2: README Dashboard Section is Outdated

**What goes wrong:** The README `## Dashboard` section still references `cd workspace/occc && bun run dev` (the pre-refactor path). The actual path is now `packages/dashboard`. If updating README, correct both the env var documentation AND the stale path references.

**Current README state (line ~469-476):**
```bash
cd workspace/occc
bun install
bun run dev    # http://localhost:6987
```

**Correct post-refactor path:**
```bash
export OPENCLAW_ROOT=$HOME/.openclaw
make dashboard   # or: cd packages/dashboard && bun install && bun run dev
```

This is a bonus cleanup item discovered during research — not in the audit but directly relevant.

### Pitfall 3: SummaryStream.tsx Line Numbering After Edit

**What goes wrong:** The line 44 parse error is caused by a single raw newline character inside the string. After the fix, `buffer.split('\n')` will be on one line. Any references to "line 44" in comments or docs will shift by one. This is a non-issue — no code references this line number.

### Pitfall 4: Test Run from Wrong Directory

**What goes wrong:** Running `uv run pytest packages/orchestration/tests/` from the repo root fails with `ModuleNotFoundError: No module named 'openclaw'` — the `openclaw` package is not installed in the root uv environment.

**Correct invocation:** Either `cd packages/orchestration && uv run pytest tests/ -v` or install the package first via `make dev` (which runs `cd packages/orchestration && uv pip install -e ".[dev]"`). The audit's "148/148 tests pass" claim was verified with the package installed.

---

## Code Examples

### Makefile guard pattern

```makefile
dashboard: ## Start dashboard dev server (port 6987) — OPENCLAW_ROOT must be exported
	@if [ -z "$$OPENCLAW_ROOT" ]; then \
		echo "ERROR: OPENCLAW_ROOT is not set."; \
		echo "  Run: export OPENCLAW_ROOT=$$HOME/.openclaw"; \
		exit 1; \
	fi
	cd packages/dashboard && bun install && bun run dev
```

Source: Standard POSIX shell guard pattern — verified against GNU Make behavior.

### SummaryStream.tsx fix (line 44)

Before (broken — contains literal newline):
```
          const lines = buffer.split('
');
```

After (correct):
```typescript
          const lines = buffer.split('\n');
```

Source: Direct file inspection at `~/.openclaw/packages/dashboard/src/components/sync/SummaryStream.tsx` lines 44-45.

### Test verification run

```bash
cd ~/.openclaw/packages/orchestration
uv run pytest tests/test_l2_review_memorization.py tests/test_pool_memorization.py -v -W all
# Expected: 17 passed, 0 warnings
```

Source: Direct test run in this session — 17 passed, 0 warnings confirmed.

---

## Findings by Item

### Item 1: OPENCLAW_ROOT Documentation Gap

**Status:** Actionable — 2 files need editing.

**Files to edit:**
1. `~/.openclaw/Makefile` — `dashboard` target needs env guard + comment
2. `~/.openclaw/README.md` — Dashboard section needs:
   - `OPENCLAW_ROOT` export requirement documented
   - Stale `workspace/occc` path corrected to `packages/dashboard`

**Why `execFileAsync` inherits env:** The Next.js API route at `packages/dashboard/src/app/api/suggestions/route.ts` calls `execFileAsync` to spawn `suggest.py`. Node.js `child_process.execFile` and its promise wrapper inherit the parent process environment by default (no explicit `env:` option). So `OPENCLAW_ROOT` must be set before `bun run dev` starts. If it is unset, `suggest.py` computes `OPENCLAW_ROOT = os.path.dirname(__file__)` or similar, resolving to inside `packages/orchestration/src/openclaw/cli/` — wrong root.

### Item 2: SummaryStream.tsx Parse Error

**Status:** Actionable — 1 file, 1 line edit.

**File:** `~/.openclaw/packages/dashboard/src/components/sync/SummaryStream.tsx`

**Nature of bug:** Literal newline character embedded in string literal at line 44. TypeScript parser sees an unterminated string on line 44 and errors. The component is a streaming markdown renderer — it is used for summarization features, not the core orchestration flow. Pre-existing since before v1.4.

**Fix is safe:** `buffer.split('\n')` is exactly what was intended — splitting newline-delimited Server-Sent Events or JSON lines. The `\n` escape is the correct delimiter.

### Item 3: Stale Patch Paths Audit

**Status:** No code changes needed. Verification only.

**Findings:**
- `test_l2_review_memorization.py`: All `patch()` targets use `openclaw.snapshot.*`, `openclaw.project_config.*` — correct post-refactor paths.
- `test_pool_memorization.py`: `patch()` targets use `pool.*` (correct — bare module name from sys.path) and `openclaw.memory_client.*` (correct — installed package path).
- No `orchestration.*` targets remain in either file.
- 17/17 tests pass with `-W all` — zero MagicMock attribute access warnings.

**Documentation action:** Update the audit item in `v1.4-MILESTONE-AUDIT.md` from "Stale patch targets — should be audited" to "Verified clean — no stale orchestration.* targets found; all 17 tests pass with -W all."

---

## Open Questions

1. **Should the OPENCLAW_ROOT guard be hard-fail (exit 1) or soft-warn (echo)?**
   - What we know: The audit says "mitigation: document in Makefile/README (no code fix needed for correctly-deployed environments)."
   - What's unclear: "document" could mean comment or guard.
   - Recommendation: Use hard-fail guard (`exit 1`). Silent failures on fresh deployments are the exact problem this item addresses. A hard fail is self-documenting.

2. **Should README's stale `workspace/occc` path be fixed in the same plan?**
   - What we know: README still references pre-refactor paths for dashboard startup.
   - Recommendation: Yes — it's in the same file the planner must edit anyway for the OPENCLAW_ROOT documentation.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `~/.openclaw/packages/dashboard/src/components/sync/SummaryStream.tsx` — line 44 literal newline confirmed via `node -e` character-level inspection
- Direct test run: `uv run pytest tests/test_l2_review_memorization.py tests/test_pool_memorization.py -v -W all` — 17 passed, 0 warnings
- Direct grep: `grep -rn "orchestration\." packages/orchestration/tests/` — zero `orchestration.*` patch targets found
- `~/.openclaw/.planning/v1.4-MILESTONE-AUDIT.md` — canonical source for all three tech debt items
- `~/.openclaw/Makefile` — current dashboard target, no env guard present
- `~/.openclaw/README.md` — stale `workspace/occc` path at line ~469, no OPENCLAW_ROOT requirement documented

### Secondary (MEDIUM confidence)
- Node.js `child_process.execFile` documentation: env inheritance is standard behavior — child inherits parent env when no `env:` option provided (well-documented Node.js behavior, consistent with POSIX fork/exec semantics)

---

## Metadata

**Confidence breakdown:**
- Item 1 (documentation gap): HIGH — root cause confirmed by code inspection; fix scope clear
- Item 2 (parse error): HIGH — literal newline confirmed by character-level inspection; fix is unambiguous
- Item 3 (patch paths): HIGH — grep and test run confirm no stale targets exist

**Research date:** 2026-02-25
**Valid until:** 2026-04-25 (stable — no external dependencies)
