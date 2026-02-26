# Phase 51: Live Verification — Docker & Sentinel - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Verify that three specific v1.4 Docker/sentinel behaviors work correctly in a live environment:
1. `docker stop` on a running L3 container → exit code 143, workspace state shows `interrupted`
2. SIGTERM while L3 is mid-memorize → memorize call completes before container exits
3. `unset OPENCLAW_ROOT && make dashboard` → prints ERROR and does not start bun dev server

This is a verify-and-fix phase: run the tests, confirm they pass, fix any failures in-place. No new features.

</domain>

<decisions>
## Implementation Decisions

### Test environment setup
- Claude selects the project (pumplai preferred, or cleanest option)
- memU must be live — Test 2 (SIGTERM drain) requires a real memorize call completing
- Fresh L3 image build (`docker build`) is first step — ensures tests run against current code
- Pre-flight check before tests: `openclaw-monitor status`, container list, memU ping — catch environment issues before tests so failures are meaningful

### SIGTERM mid-memorize timing (Test 2)
- Use an injected sleep in the SOUL task to create a reliable timing window (not a race condition)
- Task is minimal: one memorize call with a slow payload, then sleep — predictable and easy to verify
- Use existing drain timeout config — do not change it for the test
- Confirmation that drain worked: query memU API after container exits and verify the memory entry exists (not just that the container exited cleanly)

### Verification evidence
- Each test step documents: the shell command to run + the expected output to look for
- Test 1 evidence: `docker inspect` exit code + `cat workspace-state.json` showing `interrupted`
- Test 2 evidence: memU API query for the stored memory entry after container exit
- Test 3 evidence: stderr contains `ERROR`, `bun` process not running (ps or port check)
- After all 3 tests: executor fills in a PASS/FAIL checklist, appended to VERIFICATION.md

### Failure handling
- If a test fails, fix it within this phase — phase is not done until all 3 tests pass
- Code changes are in scope: spawn.py, SOUL templates, L3 entrypoint, Makefile — whatever is needed
- Researcher should identify any known implementation risks before planning (e.g., SIGTERM drain flakiness, missing Makefile guard, state write race conditions)

### Claude's Discretion
- Which project to use for container tests (pumplai or a minimal throwaway)
- Exact SOUL task payload for the memorize injection
- How many seconds of sleep to inject (enough to reliably send SIGTERM mid-call)
- Format of VERIFICATION.md checklist

</decisions>

<specifics>
## Specific Ideas

- The SIGTERM drain test should be repeatable — if it can only pass once due to state, the plan should include cleanup/reset steps between runs
- Pre-flight check should be a literal checklist the executor runs, not just implied setup

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 51-live-verification-docker-sentinel*
*Context gathered: 2026-02-25*
