# Phase 7: Phase 4 Formal Verification - Research

**Researched:** 2026-02-23
**Domain:** End-to-end verification of a Next.js 16 dashboard (DSH-01/02/03/04, SEC-02) via scripted Python/bash checks against a live runtime
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Verification approach:**
- Scripted checks using Python/bash — no manual browser testing
- Live runtime verification: start the dashboard, hit real endpoints, verify real responses
- Evidence standard: PASS/FAIL + actual script output + specific gaps/issues found (even on pass)
- Verification scripts kept as project artifacts in `scripts/` for future regression

**Dashboard acceptance bar:**
- All DSH requirements (DSH-01 through DSH-04) must be verified — no subset pass
- DSH-02 (real-time monitoring): polling on an interval (e.g., 2-5s) is acceptable — no WebSocket/SSE required
- Dashboard must look production-ready — broken layout, missing styles, or unreadable data is a fail
- Functional correctness AND visual polish both matter

**Redaction standards (SEC-02):**
- Broad definition of sensitive: API keys, auth tokens, credentials, host filesystem paths, IP addresses, usernames, container IDs — anything that could leak infrastructure details
- Test method: inject synthetic/fake secrets into test logs, verify they are redacted in dashboard output
- Hard fail if redaction logic is entirely missing — SEC-02 is a requirement, not optional
- Redaction must be verifiable end-to-end (secret enters log → appears redacted in dashboard)

**Gap handling:**
- Phase 7 is pure verification — document gaps, do not fix them inline
- Gaps organized by requirement ID (DSH-01, DSH-02, etc.) with severity tags: Critical / Major / Minor
- Each gap includes a recommended fix suggestion to feed directly into a gap-closure phase
- VERIFICATION.md is the primary output artifact

### Claude's Discretion
- Redaction format (e.g., `[REDACTED]` vs `[REDACTED:TYPE]`)
- DSH-04 metrics visualization pass/fail bar (summary numbers vs charts)
- Overall pass/fail threshold based on actual findings and severity distribution
- Specific verification script implementation details

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSH-01 | Deploy "occc" dashboard built with Next.js 16 and Tailwind 4. | Verify: dashboard starts on port 6987, TypeScript compiles clean, Next.js 16 in package.json, Tailwind 4 in devDependencies |
| DSH-02 | Real-time monitoring of swarm status via state.json or WebSockets. | Verify: /api/swarm returns live agent/metrics data; SWR polling at 2s interval confirmed via code inspection; SSE stream at /api/swarm/stream emits on state.json changes |
| DSH-03 | Live log feeds from isolated agent containers. | Verify: /api/logs/[agent] SSE endpoint connects to Docker, streams redacted logs; useLogStream hook wires SSE to LogStream component |
| DSH-04 | Global metrics visualization (task throughput, error rates). | Verify: /api/swarm returns metrics object with totalByTier, active, idle, errored, totalTasks, completedTasks, failedTasks; GlobalMetrics component renders these |
| SEC-02 | Implement automated redaction logic for sensitive debug information in logs. | Verify: redactSensitiveData applied server-side in docker.ts before SSE emission; all CONTEXT.md sensitive categories covered; synthetic secret injection test |
</phase_requirements>

---

## Summary

Phase 4 built the occc dashboard — a standalone Next.js 16 app deployed on port 6987 providing real-time swarm monitoring. The implementation is structurally complete: all five required files exist (`src/lib/redaction.ts`, `src/lib/docker.ts`, `src/lib/jarvis.ts`, `src/lib/metrics.ts`, `src/app/api/swarm/route.ts`, `src/app/api/swarm/stream/route.ts`, `src/app/api/logs/[agent]/route.ts`), all React components exist, and the redaction pipeline is wired correctly server-side.

However, research has uncovered **two substantive gaps** before scripted verification even begins: (1) the actual `workspace-state.json` file has `version: 1` (integer) and no `protocol` field, but the Zod schema in `jarvis.ts` requires `version: string` and `protocol: literal('jarvis')` — this mismatch will cause the `/api/swarm` endpoint to return a 500 error against the live state file, which is a Critical gap for DSH-01/02/04; (2) the SEC-02 redaction scope in CONTEXT.md includes host filesystem paths, IP addresses, usernames, and container IDs — none of which are covered by the 10 patterns in `redaction.ts`.

The verification approach follows the same scripted pattern established in Phase 6: a `scripts/verify_phase4.py` Python script that starts the dev server, hits real HTTP endpoints, exercises the SSE streams, and runs synthetic secret injection. The VERIFICATION.md is the primary artifact.

**Primary recommendation:** Verification scripts structured per-requirement (verify_dsh01 through verify_dsh04, verify_sec02), consolidated into `scripts/verify_phase4.py`. Start the dashboard with `npm run dev` in `workspace/occc/`, wait for readiness on port 6987, then run curl-based and Python requests-based checks. Note known issues upfront so the verification does not spiral into fixing.

---

## Standard Stack

### Core (What Phase 4 Delivered)

| Component | Version | File | Status |
|-----------|---------|------|--------|
| Next.js | 16.1.6 | `workspace/occc/package.json` | Installed, node_modules present |
| Tailwind CSS | 4.x | `devDependencies` | Installed |
| SWR | 2.4.0 | `package.json` | Installed |
| React | 19.2.3 | `package.json` | Installed |
| dockerode | 4.0.9 | `package.json` | Installed |
| zod | 4.3.6 | `package.json` | Installed |
| react-toastify | 11.0.5 | `package.json` | Installed |
| lucide-react | 0.572.0 | `package.json` | Installed |

### Verification Runtime

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 25.6.1 | Run Next.js dev server (bun not in PATH, npm available) |
| npm | 11.9.0 | `npm run dev` to start dashboard |
| Python 3 | available | Verification script (same pattern as verify_phase3.py) |
| curl / requests | available | HTTP/SSE endpoint probing |
| Docker SDK | docker>=7.1.0 | Already used in verify_phase3.py |

**Critical:** `bun` is not in PATH on this host. The `package.json` scripts use `next` CLI, which is available in `node_modules/.bin/next`. Use `npm run dev` to start the server.

---

## Architecture Patterns

### Phase 4 Implementation — Verified Structure

The implementation matches the planned architecture exactly:

```
workspace/occc/src/
├── app/
│   ├── api/
│   │   ├── swarm/route.ts          # GET: reads state.json, returns agents+metrics+state
│   │   ├── swarm/stream/route.ts   # SSE: watches state.json mtime, emits {updated:true}
│   │   └── logs/[agent]/route.ts   # SSE: Docker container log stream (redacted)
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx                    # MissionControl: 3-panel layout
├── components/
│   ├── AgentHierarchy.tsx           # Left: L1/L2/L3 tree with status dots
│   ├── AgentDetail.tsx              # Center: selected agent detail
│   ├── LogStream.tsx                # Right: SSE log viewer with filter/search
│   ├── GlobalMetrics.tsx            # Top bar: tier counts + active/idle/error
│   └── StatusToast.tsx              # Toast notifications
├── hooks/
│   ├── useSwarmState.ts             # SWR 2s poll + SSE invalidation hybrid
│   └── useLogStream.ts              # SSE with circular 1000-entry buffer
└── lib/
    ├── jarvis.ts                    # Zod schema + TypeScript types for state.json
    ├── docker.ts                    # dockerode wrapper + DockerLogStreamParser + redaction
    ├── redaction.ts                 # REDACTION_PATTERNS array + redactSensitiveData()
    └── metrics.ts                   # buildAgentHierarchy() + deriveSwarmMetrics()
```

### Verification Script Pattern (from Phase 6)

The established pattern from `scripts/verify_phase3.py`:
- `find_project_root()` — locate `openclaw.json`
- `print_section()` / `print_check()` — structured PASS/FAIL/WARN/INFO output
- One function per requirement section
- Exit code 0 = all pass, 1 = any fail
- Cleanup in `finally` blocks (kill server processes)

The Phase 7 script should follow the same structure with sections: DSH-01, DSH-02, DSH-03, DSH-04, SEC-02.

### Starting the Dashboard for Live Verification

```bash
# Start the dev server (bun not available, use npm)
cd ~/.openclaw/workspace/occc
npm run dev &  # starts on port 6987

# Wait for readiness
timeout 30 bash -c 'until curl -sf http://localhost:6987/api/swarm; do sleep 1; done'
```

### Probing /api/swarm

```python
import requests, json, time

resp = requests.get("http://localhost:6987/api/swarm", timeout=10)
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
data = resp.json()
assert "agents" in data
assert "metrics" in data
assert "state" in data
metrics = data["metrics"]
assert "totalByTier" in metrics
assert "active" in metrics
assert "idle" in metrics
assert "errored" in metrics
assert "totalTasks" in metrics
assert "completedTasks" in metrics
assert "failedTasks" in metrics
```

### Probing /api/swarm/stream (SSE)

```python
import requests, time

# SSE: open connection, read one event, verify format
with requests.get("http://localhost:6987/api/swarm/stream",
                  stream=True, timeout=5,
                  headers={"Accept": "text/event-stream"}) as resp:
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("Content-Type", "")
    # Read one line to confirm stream is alive
    line = next(resp.iter_lines(decode_unicode=True), None)
    # line may be ": keepalive" or "data: ..." — either confirms connection
```

### Probing /api/logs/[agent] (Docker log SSE)

```python
# This requires a running container named matching the agent
# If no container is running, expect 404 {"error": "Container not found for agent"}
import requests

resp = requests.get("http://localhost:6987/api/logs/pumplai_pm", timeout=5)
# Acceptable: 200 (container running) or 404 (container not found, graceful)
# Fail: 500 (docker socket permission error, dockerode crash)
assert resp.status_code in [200, 404], f"Unexpected status: {resp.status_code}"
```

### SEC-02 Synthetic Secret Injection

The test method per CONTEXT.md: inject fake secrets into a log payload and verify redaction through the `/api/logs` pipeline. Since the logs endpoint requires a running Docker container, the unit-level test targets `redactSensitiveData()` directly:

```python
import subprocess, sys

# Run a Node.js test script that calls redactSensitiveData
test_script = """
const { redactSensitiveData } = require('./src/lib/redaction.ts');
// Or: compile TS and run
"""

# Alternatively, test the redaction patterns by importing from Python
# and applying the same regex logic to validate coverage

synthetic_secrets = [
    ("sk-test12345678901234567890abcdefgh", "OPENAI_KEY"),
    ("AKIAIOSFODNN7EXAMPLE1234", "AWS_KEY"),
    ("AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKfm", "GOOGLE_KEY"),  # 35 chars after AIza
    ("ghp_abcdefghijklmnopqrstuvwxyz123456", "GITHUB_TOKEN"),
    ("xoxb-123456789012-123456789012-abcdefghijklmnopqrstuvwxyz", "SLACK_TOKEN"),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test", "AUTH_HEADER"),
    ("x-api-key: my-secret-api-key-123", "API_KEY_HEADER"),
    ("user@example.com", "EMAIL"),
    ("PASSWORD=mysecretpassword123", "GENERIC_SECRET"),
]
```

**Note:** TypeScript cannot be directly imported into Python. The SEC-02 verification script must either:
1. Compile the TypeScript and run with Node.js, OR
2. Replicate the regex patterns in Python and apply them to verify coverage, OR
3. Create a small Node.js test script and call it via `subprocess`

The recommended approach: write a `scripts/test_redaction.cjs` helper that imports the compiled JS and runs the synthetic secrets through it, called from the Python verification script.

---

## Known Gaps (Pre-Verified by Research)

These gaps are documented here to give the planner and executor a head start. The verification phase must confirm them with evidence.

### Gap 1: Zod Schema Mismatch (CRITICAL — DSH-01/02/04)

**What:** The Zod schema in `src/lib/jarvis.ts` requires:
```typescript
JarvisStateSchema = z.object({
  version: z.string(),          // expects "1.0.0"
  protocol: z.literal('jarvis'), // expects exactly "jarvis"
  metadata: z.object({
    created_at: z.number(),     // expects both fields
    last_updated: z.number(),
  }),
})
```

The actual `workspace/.openclaw/workspace-state.json` on disk contains:
```json
{
  "version": 1,               // integer, not string
  "onboardingCompletedAt": "...", // extra field (not an issue — zod ignores extras by default)
  // "protocol" key is ABSENT
  "metadata": {
    "last_updated": 1771846399.25
    // "created_at" is ABSENT
  }
}
```

**Impact:** `parseJarvisState(rawState)` will throw a `ZodError`. The `/api/swarm` route catches this and returns `{error: "Failed to read swarm state", detail: "...ZodError..."}` with status 500. The dashboard will show the error state ("Connection Failed" UI).

**Severity:** Critical — renders DSH-01, DSH-02, and DSH-04 unverifiable in the live runtime test until this is fixed or the schema is made lenient.

**Root cause:** The state file was initialized by the pre-Phase-4 openclaw setup with `version: 1` (integer). The state_engine.py creates `version: "1.0.0"` (string) only for fresh initializations. The existing file was created before Phase 4, so its schema differs from what the Zod model expects.

**Fix suggestion (for gap-closure phase):** Either (a) update `JarvisStateSchema` to use `z.union([z.string(), z.number()])` for version, make `protocol` optional, and make `metadata.created_at` optional; OR (b) add a migration step that rewrites the state file to conform to the schema.

### Gap 2: SEC-02 Redaction Coverage Incomplete (MAJOR — SEC-02)

**What:** CONTEXT.md requires redaction of: API keys, auth tokens, credentials, host filesystem paths, IP addresses, usernames, container IDs.

Current `redaction.ts` covers: AWS keys, OpenAI/Anthropic/Google keys, GitHub/Slack tokens, auth headers, email addresses, generic env-style secrets (PASSWORD=..., SECRET=...).

**Missing categories:**
- Host filesystem paths (e.g., `~/.ssh/id_rsa`, `/root/.aws/credentials`)
- IP addresses (e.g., `192.168.1.100`, `10.0.0.1`)
- Container IDs (e.g., `968134ac3afe`, full 64-char SHA256 IDs)
- Usernames in path context (e.g., `~/`)

**Severity:** Major — SEC-02 is explicitly described as a hard requirement in CONTEXT.md. Missing categories constitute a gap, not a complete failure (redaction logic exists).

**Fix suggestion:** Add patterns for IPv4/IPv6, Linux path patterns starting with `/home/`, `/root/`, `/etc/`, and Docker container ID patterns (12-char and 64-char hex strings).

### Gap 3: Agent Level Data Missing from openclaw.json (MINOR — DSH-01)

**What:** All 6 agents in `openclaw.json` have `"level": null` and `"reports_to": null`. The `buildAgentHierarchy()` function defaults missing levels to 1 (`const level = (agent.level || 1) as 1 | 2 | 3`). This means all agents appear under "Level 1: Strategy" in the hierarchy panel — the L2/L3 tiers will show no agents.

**Impact:** The visual hierarchy (DSH-01 requirement: render "live agent status") shows incorrect structure. This is a data/configuration gap, not a code gap.

**Severity:** Minor — the dashboard renders, agents are listed, but the L1/L2/L3 grouping is wrong.

**Fix suggestion:** Update `openclaw.json` agents list to set correct `level` (1/2/3) and `reports_to` values for each agent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dashboard process management | Custom process spawner | Python `subprocess.Popen` with `npm run dev` | Already established in verify_phase3.py pattern |
| HTTP/SSE testing | Custom TCP client | `requests` library with `stream=True` | Already in Python stdlib-adjacent packages |
| TypeScript execution for redaction test | TS transpile pipeline | Small `.cjs` helper script with pre-compiled output | Avoids ts-node complexity in verification scripts |
| Schema validation testing | Full Zod re-implementation | Direct HTTP response inspection (check for 200 vs 500) | The symptom (500 error) is the evidence |

---

## Common Pitfalls

### Pitfall 1: Zod Schema Failure Masking Dashboard Functionality

**What goes wrong:** The `/api/swarm` endpoint returns 500, verification marks DSH-01/02/04 as FAIL, but the actual dashboard code (components, layout, SSE) is correct.

**Why it happens:** The state file on disk was initialized before Phase 4 and does not conform to the strict Zod schema. This is a data/schema alignment issue, not a dashboard implementation issue.

**How to handle:** Report the Zod mismatch as a gap with clear root cause. Test what CAN be verified independently: TypeScript compilation, component file existence, layout code review, the `/api/swarm/stream` SSE endpoint (which doesn't use Zod), and the `/api/logs` endpoint (which doesn't touch state.json).

**Warning sign:** `/api/swarm` returns `{"error": "Failed to read swarm state", "detail": "..."}` — this is the Zod issue, not a missing route.

### Pitfall 2: bun Not Available

**What goes wrong:** Script tries `bun run dev` and fails silently.

**Prevention:** Always use `npm run dev` (node_modules/.bin/next available, npm 11.9.0 available).

### Pitfall 3: Dashboard Port Not Released After Script

**What goes wrong:** Verification script kills the dev server but port 6987 remains bound, causing subsequent runs to fail.

**Prevention:** Use `lsof -ti:6987 | xargs kill -9` in cleanup, or use a unique PID-based kill. Always run in finally block.

### Pitfall 4: SEC-02 Verification Requires TypeScript Execution

**What goes wrong:** Python verification script can't directly `import` TypeScript modules.

**Prevention:** Create a `scripts/test_redaction.cjs` Node.js CommonJS helper that:
1. Uses compiled Next.js output (`.next/server/chunks/`) to import the redaction module, OR
2. Reimplements the regex patterns inline and tests them, OR
3. Spins up a minimal Node.js eval to test patterns

The simplest approach: the redaction patterns are pure regex with no external dependencies — replicate them in Python for verification purposes and document this as an equivalent test.

### Pitfall 5: SSE Stream Hangs Verification Script

**What goes wrong:** `requests.get(..., stream=True)` blocks forever waiting for SSE events.

**Prevention:** Use `timeout=5` and read only the first few bytes/lines to confirm the stream is alive. Use `resp.iter_lines()` with a counter that breaks after 3 lines.

---

## Code Examples

### Starting and Waiting for Dashboard Readiness

```python
import subprocess, time, requests, signal, os

def start_dashboard(occc_dir: str) -> subprocess.Popen:
    """Start Next.js dev server, wait for port 6987."""
    proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=occc_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait up to 30s for the server to be ready
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            resp = requests.get("http://localhost:6987/api/swarm", timeout=2)
            if resp.status_code in [200, 500]:  # 500 is OK - server is up, Zod may fail
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise RuntimeError("Dashboard did not start within 30 seconds")

def stop_dashboard(proc: subprocess.Popen) -> None:
    """Kill the dev server and release port 6987."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    # Belt and suspenders: kill anything on port 6987
    subprocess.run("lsof -ti:6987 | xargs kill -9 2>/dev/null", shell=True)
```

### DSH-01: File and Build Verification

```python
def verify_dsh01(occc_dir: str) -> dict:
    """DSH-01: occc dashboard exists with Next.js 16 and Tailwind 4."""
    results = []

    # 1. package.json has next 16.x
    import json
    pkg = json.loads(open(f"{occc_dir}/package.json").read())
    next_version = pkg.get("dependencies", {}).get("next", "")
    results.append(("PASS" if "16." in next_version else "FAIL",
                    f"Next.js version: {next_version}"))

    # 2. Tailwind 4 in devDependencies
    tw_version = pkg.get("devDependencies", {}).get("tailwindcss", "")
    results.append(("PASS" if tw_version.startswith("^4") else "FAIL",
                    f"Tailwind CSS version: {tw_version}"))

    # 3. TypeScript compilation
    result = subprocess.run(
        ["node_modules/.bin/tsc", "--noEmit"],
        cwd=occc_dir, capture_output=True, text=True
    )
    results.append(("PASS" if result.returncode == 0 else "FAIL",
                    "TypeScript compilation"))

    # 4. Dashboard responds on port 6987
    try:
        resp = requests.get("http://localhost:6987/", timeout=5)
        results.append(("PASS" if resp.status_code == 200 else "WARN",
                        f"Dashboard root: HTTP {resp.status_code}"))
    except Exception as e:
        results.append(("FAIL", f"Dashboard not reachable: {e}"))

    return results
```

### SEC-02: Redaction Verification (Python-native regex)

```python
import re

# Mirror the redaction.ts patterns in Python for verification
REDACTION_PATTERNS = [
    ("AWS_KEY",        re.compile(r"AKIA[0-9A-Z]{16}")),
    ("OPENAI_KEY",     re.compile(r"sk-[a-zA-Z0-9]{20,}")),
    ("ANTHROPIC_KEY",  re.compile(r"sk-ant-[a-zA-Z0-9-]{20,}")),
    ("GOOGLE_KEY",     re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("GITHUB_TOKEN",   re.compile(r"gh[ps]_[a-zA-Z0-9]{36,}")),
    ("SLACK_TOKEN",    re.compile(r"xox[pboa]-[0-9]+-[0-9A-Za-z-]+")),
    ("AUTH_HEADER",    re.compile(r"authorization:\s*bearer\s+\S+", re.IGNORECASE)),
    ("API_KEY_HEADER", re.compile(r"x-api-key:\s*\S+", re.IGNORECASE)),
    ("EMAIL",          re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("GENERIC_SECRET", re.compile(r"(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)\s*[=:]\s*\S+", re.IGNORECASE)),
]

SYNTHETIC_SECRETS = [
    ("sk-test12345678901234567890abcdef", "OPENAI_KEY"),
    ("AKIAIOSFODNN7EXAMPLETEST1", "AWS_KEY"),
    ("AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKfm", "GOOGLE_KEY"),
    ("ghp_abcdefghijklmnopqrstuvwxyz1234567", "GITHUB_TOKEN"),
    ("ghs_abcdefghijklmnopqrstuvwxyz1234567", "GITHUB_TOKEN"),
    ("xoxb-123456789012-123456789012-testtoken", "SLACK_TOKEN"),
    ("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test", "AUTH_HEADER"),
    ("x-api-key: my-secret-api-key-9999", "API_KEY_HEADER"),
    ("test@example.com", "EMAIL"),
    ("PASSWORD=mysecretpassword123", "GENERIC_SECRET"),
]

# Test MISSING from CONTEXT.md (expected FAIL — document as gap)
MISSING_CATEGORIES = [
    ("~/.ssh/id_rsa", "HOST_PATH"),
    ("192.168.1.100", "IP_ADDRESS"),
    ("968134ac3afe", "CONTAINER_ID"),
]

def verify_sec02_redaction():
    results = []
    for secret, pattern_name in SYNTHETIC_SECRETS:
        matched = any(pat.search(secret) for _, pat in REDACTION_PATTERNS)
        results.append(("PASS" if matched else "FAIL",
                        f"Pattern {pattern_name} catches: {secret[:30]}..."))

    for secret, category in MISSING_CATEGORIES:
        matched = any(pat.search(secret) for _, pat in REDACTION_PATTERNS)
        results.append(("WARN" if not matched else "PASS",
                        f"[EXPECTED MISS] {category}: {secret}"))

    return results
```

---

## Verification Evidence Requirements

Per CONTEXT.md, each PASS/FAIL must include actual evidence. Here is what the verification script must capture for VERIFICATION.md:

| Requirement | Evidence to Capture |
|-------------|---------------------|
| DSH-01 | next/tailwind versions from package.json, `tsc --noEmit` exit code + output, HTTP 200 from root URL |
| DSH-02 | `/api/swarm` response body (truncated), polling interval confirmed in source (2s), SSE `Content-Type: text/event-stream` header |
| DSH-03 | `/api/logs/{agent}` response status + first 3 SSE events or 404 body, docker.ts redaction call confirmed in source |
| DSH-04 | metrics object from `/api/swarm` with all 7 fields (totalByTier, active, idle, errored, totalTasks, completedTasks, failedTasks) |
| SEC-02 | Per-pattern PASS/FAIL for all 10 implemented patterns + FAIL/WARN for missing categories |

---

## Open Questions

1. **Will the Zod schema error be fixed inline or documented as a gap?**
   - What we know: CONTEXT.md says "Phase 7 is pure verification — document gaps, do not fix them inline"
   - What's unclear: If /api/swarm returns 500, DSH-02 and DSH-04 cannot be functionally verified at the API level
   - Recommendation: Document the schema mismatch as a Critical gap. For the verification script, test what can still be verified: TypeScript compilation, component file existence, the `/api/swarm/stream` endpoint (doesn't use Zod), and the redaction pipeline. Mark DSH-02/04 as PARTIAL with evidence.

2. **Can the SEC-02 end-to-end test work without a running Docker container?**
   - What we know: The end-to-end path requires: fake secret → Docker log → SSE → redacted in dashboard. The Docker log source requires a running container.
   - What's unclear: Can we inject a test log entry without a real container?
   - Recommendation: For end-to-end, use the `redactSensitiveData()` function unit-level test (verified via Node.js subprocess). Document this as "unit-verified" since full e2e requires a container with known log content.

3. **Do agents in openclaw.json need level/reports_to populated to pass DSH-01?**
   - What we know: All agents have `level: null`, so all appear under "Level 1" in the UI
   - What's unclear: Is correct hierarchical grouping part of DSH-01 acceptance?
   - Recommendation: DSH-01 says "render live agent status" — agents render, just in wrong tier. Mark as Minor gap. The Phase 4 SUMMARY's human checklist item was "Confirm 3-panel mission control layout" which is layout, not hierarchy accuracy.

---

## Validation Architecture

Note: `workflow.nyquist_validation` is not present in `.planning/config.json`. The project testing framework is Playwright (per `preferences.testing_framework`). No Playwright config or spec files exist in the occc project directory (only a shell integration test). Per the researcher instructions, this section is skipped when nyquist_validation is false/absent.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `~/.openclaw/workspace/occc/src/` — all source files read and analyzed
- Direct data inspection: `~/.openclaw/workspace/.openclaw/workspace-state.json` — schema mismatch confirmed
- Direct config inspection: `~/.openclaw/openclaw.json` — agent level data confirmed null
- Phase 6 VERIFICATION.md pattern: `~/.openclaw/.planning/phases/06-phase3-verification/06-VERIFICATION.md`
- Phase 6 verify script pattern: `~/.openclaw/scripts/verify_phase3.py`
- Runtime check: `npm` 11.9.0 available, `node` 25.6.1 available, `bun` NOT in PATH

### Secondary (MEDIUM confidence)
- Phase 4 SUMMARY `04-04-SUMMARY.md` — confirms TypeScript passes, build passes, smoke test run
- Phase 4 CONTEXT.md — original implementation decisions and SEC-02 scope

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Known gaps (Zod schema, SEC-02 coverage): HIGH — confirmed by direct code + data inspection
- Verification approach (scripted Python, npm run dev): HIGH — follows established project pattern
- Gap severity classification: MEDIUM — based on requirements analysis, actual test results may differ
- SEC-02 regex coverage for missing categories: HIGH — confirmed by grep of redaction.ts patterns

**Research date:** 2026-02-23
**Valid until:** 2026-03-09 (stable codebase, 14 days)
