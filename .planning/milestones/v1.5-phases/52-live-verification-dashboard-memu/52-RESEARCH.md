# Phase 52: Live Verification — Dashboard & memU - Research

**Researched:** 2026-02-25
**Domain:** End-to-end live verification of v1.4 dashboard and memU features
**Confidence:** HIGH — all findings based on direct codebase inspection and live service probing

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Service prerequisites**
- Plan includes full startup steps for dashboard and memU (not assumed running)
- Include a pre-flight health check (curl endpoints) to confirm services are up before running tests
- Use real data from an existing project (not seeded test data) — more realistic verification
- For test state setup: use API/CLI calls where straightforward (e.g., POST a memory), manual dashboard interaction for complex scenarios (e.g., triggering a conflict)

**Pass/fail evidence**
- Structured JSON log per test with timestamps, status, and relevant response data
- Screenshots captured for all UI-based tests (health badges, conflict panel, sidebar badge, suggestions page)
- API tests: appropriate detail per test (full request+response for critical paths, status+key fields for simpler checks)

**Failure handling**
- Run all 9 tests first (log and continue on failure), then address failures in priority order
- Bugs discovered during verification are fixed in-phase and re-verified — keeps the loop tight
- If memU or dashboard is unresponsive, plan includes basic troubleshooting before marking blocked

### Claude's Discretion

- Which project to use as test target (pick based on richest memory data)
- Storage location for verification log and screenshots (phase dir vs data dir — follow project conventions)
- Whether structured log records full run history (initial fail + fix + re-pass) or just final state
- API evidence detail level per test
- Service recovery troubleshooting depth

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 52 is a verify-and-fix phase covering 9 end-to-end tests for v1.4 dashboard and memU features. Research found **two hard blockers** and several environment gaps that the plan must address before any tests can run.

**Blocker 1 — memU Docker image is stale.** The running `openclaw-memory` container was built 2026-02-24T06:51:38Z. The `docker/memory/memory_service/routers/memories.py` file that adds `POST /memories/health-scan`, `PUT /memories/{id}`, and `GET /memories/health-flags` was last modified 2026-02-24T18:30 — AFTER the build. Live probe confirms: `GET /openapi.json` returns only 5 routes (`/health`, `/memorize`, `/retrieve`, `/memories`, `/memories/{memory_id}` DELETE-only). The image must be rebuilt before tests 1–4 can work.

**Blocker 2 — Health settings do not persist across refresh.** `MemoryPanel.tsx` initializes `healthSettings` from a hardcoded `DEFAULT_HEALTH_SETTINGS` constant (no `localStorage` read). `SettingsPanel.tsx` calls `onUpdate(draft)` which sets React state only. Success criterion 5 ("threshold adjustment in settings page persists across refresh") requires adding `localStorage` persistence. This is a code fix required in-phase.

**Secondary gaps:** memU has 0 memories across all projects (no test data exists naturally); dashboard is not running; suggest.py requires workspace-state.json with activity entries OR memU memories to produce suggestions. The plan must seed test data explicitly.

**Primary recommendation:** Wave 0 = rebuild memU image + start dashboard + seed test memories via `POST /memorize`. Then run all 9 tests. Fix failures (settings persistence, any API issues) before final re-verify.

---

## Standard Stack

### Core (already in use — no new dependencies)

| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| Next.js (App Router) | 14.2.5 | Dashboard framework | Running on port 6987 via `bun run dev` |
| React | 18 | UI | SWR for data fetching |
| SWR | ^2.4.0 | API polling, cache invalidation | `mutate()` used throughout |
| react-toastify | ^10.0.5 | Toast notifications | Already imported in MemoryPanel |
| FastAPI | >=0.115.0 | memU HTTP API | `docker/memory/memory_service/` |
| Docker Compose | — | memU + postgres lifecycle | `docker/memory/docker-compose.yml` |
| python3 / uv | — | suggest.py CLI | `packages/orchestration/src/openclaw/cli/suggest.py` |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `curl` | Pre-flight health checks and API evidence capture | All API-based tests |
| `bun` | Dashboard dev server startup | `cd packages/dashboard && bun install && bun run dev` |
| `docker compose` | memU rebuild and restart | Wave 0 setup |
| `localStorage` | Health settings persistence (FIX needed) | Test 5 |
| `screenshots` via browser | UI evidence capture | Tests 1, 3, 6, 8 |

---

## Architecture Patterns

### Service Topology

```
Dashboard (Next.js, port 6987)
  └─ /api/memory/health-scan  → POST http://localhost:18791/memories/health-scan
  └─ /api/memory/{id} PUT/DEL → PUT/DELETE http://localhost:18791/memories/{id}
  └─ /api/suggestions GET     → reads workspace/.openclaw/{project}/soul-suggestions.json
  └─ /api/suggestions POST    → exec python3 suggest.py --project {id}
  └─ /api/suggestions/{id}/action POST → appends to projects/{id}/soul-override.md
                                       → exec python3 soul_renderer.py --project {id} --write --force

memU service (FastAPI, port 18791, Docker)
  └─ GET /memories?user_id=   → list memories for project
  └─ POST /memories/health-scan → staleness + conflict detection
  └─ PUT /memories/{id}       → update content (re-embeds via memu)
  └─ DELETE /memories/{id}    → remove memory
  └─ POST /memorize           → add new memory

postgres (port 5432, Docker internal)
  └─ Stores memories + embeddings for memU
```

### Test Data Strategy

The plan must seed test data explicitly. memU has 0 memories for all projects.

**Minimum viable seed for all 9 tests:**
- At least 1 memory older than `age_threshold_days` (30 days) without recent retrieval → enables stale flag (Test 1)
- At least 2 memories with high cosine similarity (0.75–0.97 range) → enables conflict flag (Test 3)
- At least `MIN_CLUSTER_SIZE=3` memories with shared keywords in `workspace-state.json` activity log OR in memU → enables suggest.py to produce suggestions (Tests 6–9)

**Seeding approach for stale/conflict:** The `POST /memorize` endpoint adds real memories. However, artificially creating stale memories (old `created_at`) is not possible through the API — memU sets `created_at` at write time. **Workaround:** Set `age_threshold_days=1` and `retrieval_window_days=0` in health settings to treat ANY memory as potentially stale immediately, then restore realistic thresholds after.

**Seeding approach for suggestions:** Write synthetic activity log entries directly to `workspace-state.json` with `status: "failed"` and repeated keywords — this is the primary corpus for `suggest.py`.

### Component Data Flow for Each Test

**Test 1 — Health scan populates flag badges**
```
MemoryPanel: runHealthScan()
  → POST /api/memory/health-scan {user_id, age_threshold_days, ...}
  → proxied to POST http://18791/memories/health-scan
  → returns {flags: [...], scanned_at, totals}
  → setHealthFlags(Map<memory_id, HealthFlag>)
  → HealthTab renders FlagTypeBadge per flag
  → Tab badge shows red count bubble (totalFlagCount > 0)
```

**Test 2 — Archive stale flag PUT succeeds, flag removed, toast appears**
```
HealthTab: onArchiveMemory(memoryId)
  → handleArchiveMemory() in MemoryPanel
  → PUT /api/memory/{id} {content: "[ARCHIVED <iso>] <original>"}
  → memU PUT /memories/{id} re-embeds content
  → handleDismissFlag(memoryId) removes from healthFlags Map
  → toast.success('Memory archived.')
```

**Test 3 — Conflict badge click opens ConflictPanel with side-by-side diff**
```
HealthTab: View Conflict button → onOpenConflict(flag)
  → handleOpenConflict() finds flaggedItem + conflictItem in items array
  → setConflictPanel({flaggedItem, conflictItem, similarityScore})
  → ConflictPanel renders with computeWordDiff (LCS algorithm, client-side)
```

**Test 4 — Editing flagged memory triggers re-scan automatically**
NOTE: Re-scan is NOT automatic in current code. `handleEditMemory()` calls `mutate()` (refreshes memory list) but does NOT call `runHealthScan()`. This is a potential gap in success criterion 4 — editing a memory updates content but the health scan flags remain until manually re-run. The plan must test what actually happens and decide if auto-rescan is needed (in-phase fix if criterion requires it).

**Test 5 — Threshold adjustment in settings page persists across refresh**
CONFIRMED GAP: `healthSettings` is React component state only. `DEFAULT_HEALTH_SETTINGS` is a module constant. `SettingsPanel.handleApply()` calls `onUpdate(draft)` which sets `useState`. On refresh, state resets. Fix required: persist to `localStorage('occc-health-settings')` and read in `useState` lazy initializer.

**Test 6 — /suggestions page renders without errors**
```
SuggestionsPage → SuggestionsPanel → useSWR → GET /api/suggestions?project={id}
  → reads workspace/.openclaw/{project}/soul-suggestions.json (or returns EMPTY_STATE)
```
This should work even with no suggestions (renders "Never / No patterns met threshold").

**Test 7 — Accepting a suggestion appends to soul-override.md and re-renders SOUL**
```
SuggestionCard: handleAccept()
  → POST /api/suggestions/{id}/action {action:'accept', project, diff_text}
  → validateDiffText(diff_text) — must pass or returns 422
  → fs.appendFile(projects/{id}/soul-override.md, diff_text)
  → execFile(python3 soul_renderer.py --project {id} --write --force)
  → suggestionsData[idx].status = 'accepted'
  → fs.writeFile(soul-suggestions.json)
```

**Test 8 — Sidebar badge shows correct pending suggestion count**
```
Sidebar: useEffect polls GET /api/suggestions?project=${projectId} every 30s
  → filters suggestions where status === 'pending'
  → pendingCount > 0 → renders red badge on Suggestions nav item
```
Note: `projectId` in Sidebar comes from `localStorage.getItem('occc-project')` — must match the test project.

**Test 9 — POST /api/suggestions invokes suggest.py and returns results**
```
POST /api/suggestions?project={id}
  → execFileAsync(python3, [suggest.py, --project, id], {timeout: 60000})
  → suggest.py: loads activity_memories + memU memories
  → clusters by keyword, applies suppression
  → writes soul-suggestions.json
  → API reads and returns updated file
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| localStorage persistence for settings | Custom serialization | Standard `JSON.stringify/parse` in `useState` lazy initializer (same pattern as `occc-theme`) | Pattern already established in `ThemeContext.tsx` |
| Memory content diff | Custom diff algorithm | Already implemented — `computeWordDiff()` in `ConflictPanel.tsx` is LCS-based, client-side | No server round-trip needed |
| Docker image rebuild | Manual Dockerfile editing | `docker compose build && docker compose up -d` in `docker/memory/` | Standard compose workflow |
| Test data seeding | Complex fixtures | Direct `curl POST /memorize` + direct JSON file writes | Simpler, matches project conventions |

---

## Common Pitfalls

### Pitfall 1: Testing Against Stale memU Image
**What goes wrong:** `POST /api/memory/health-scan` returns 404 or 405 because the running container lacks the endpoint.
**Why it happens:** The `openclaw-memory` container was built 2026-02-24T06:51:38Z — before `memories.py` router was updated to add health-scan, PUT, and health-flags routes.
**How to avoid:** Rebuild image as Wave 0 task: `cd /home/ollie/.openclaw/docker/memory && docker compose build && docker compose up -d`
**Warning signs:** `curl http://localhost:18791/openapi.json` shows only 5 routes (should be 7+ after rebuild)

### Pitfall 2: No Test Memories — Health Scan Returns Empty
**What goes wrong:** Health scan succeeds (HTTP 200) but `flags: []` — nothing to test badges, archive, conflict panel.
**Why it happens:** memU has 0 memories for all projects as of 2026-02-25.
**How to avoid:** Seed memories via `POST http://18791/memorize` before running scan. Use tuned thresholds (`age_threshold_days=1`) to make fresh memories appear stale immediately during testing.
**Warning signs:** `GET http://18791/memories?user_id={project}` returns `{"items": [], "total": 0}`

### Pitfall 3: Health Settings Don't Persist — Test 5 Always Fails
**What goes wrong:** Change threshold in SettingsPanel, refresh, settings reset to defaults.
**Why it happens:** `healthSettings` is `useState(DEFAULT_HEALTH_SETTINGS)` — no localStorage read.
**How to avoid:** Add `localStorage` persistence. Read in lazy initializer, write on Apply. See Code Examples section.
**Warning signs:** After refresh, `age_threshold_days` shows 30 (the default) regardless of what was set.

### Pitfall 4: suggest.py Produces No Suggestions
**What goes wrong:** `POST /api/suggestions` succeeds but returns `{suggestions: []}` — nothing to accept (Tests 7–9 can't proceed).
**Why it happens:** `suggest.py` requires `MIN_CLUSTER_SIZE=3` memories with the same keyword. Both corpus sources (workspace-state.json and memU) are empty.
**How to avoid:** Write synthetic activity log entries into `workspace/.openclaw/{project}/workspace-state.json` with repeated failure keywords. Do this with direct JSON manipulation (the state file path for pumplai is `/home/ollie/Development/Projects/pumplai/.openclaw/pumplai/workspace-state.json` per `get_state_path()`, but this path may not exist — fall back to `get_project_root()/workspace/.openclaw/pumplai/` which resolves via OPENCLAW_ROOT).
**Warning signs:** `python3 suggest.py --project pumplai --dry-run` prints 0 suggestions found.

### Pitfall 5: Re-scan Not Triggered After Memory Edit (Test 4)
**What goes wrong:** Success criterion 4 says "editing a flagged memory triggers re-scan automatically" — but `handleEditMemory()` in `MemoryPanel.tsx` only calls `mutate()` (refreshes memory list), not `runHealthScan()`.
**Why it happens:** The code saves the edit and reloads memories but does not auto-re-scan.
**How to avoid:** In-phase fix: call `runHealthScan()` after `mutate()` in `handleEditMemory()` and `handleDeleteMemoryFromConflict()`.
**Warning signs:** After editing a memory in ConflictPanel, the Health tab still shows old flags.

### Pitfall 6: Sidebar Badge Uses localStorage Project — May Mismatch Test Project
**What goes wrong:** Sidebar badge shows wrong count or stays 0 even after suggestions are seeded.
**Why it happens:** `Sidebar.tsx` reads `localStorage.getItem('occc-project')` on mount and polls that project's suggestions. If the browser hasn't visited the dashboard or the stored project differs from test target, badge doesn't update.
**How to avoid:** Ensure `localStorage('occc-project')` is set to the test project before testing badge. Navigate the dashboard to the suggestions page first to trigger the SWR fetch.
**Warning signs:** Badge shows 0 but `/api/suggestions?project=pumplai` returns pending suggestions.

### Pitfall 7: soul-suggestions.json Path Mismatch
**What goes wrong:** `GET /api/suggestions?project=pumplai` returns EMPTY_STATE even after `suggest.py` runs.
**Why it happens:** `suggest.py` uses `get_project_root() / "workspace" / ".openclaw" / project_id / "soul-suggestions.json"`. The API route uses `OPENCLAW_ROOT + "/workspace/.openclaw/{projectId}/soul-suggestions.json"`. Both resolve to the same path when `OPENCLAW_ROOT` is set, but the workspace path for pumplai is at `/home/ollie/Development/Projects/pumplai/.openclaw/pumplai/` via `get_state_path()`.
**How to avoid:** Run `suggest.py --dry-run` first and confirm it writes to the path the API reads. Also confirm `OPENCLAW_ROOT` is exported when starting the dashboard.
**Warning signs:** `suggest.py` prints "Saved N suggestion(s)" but `GET /api/suggestions?project=pumplai` still returns `{suggestions:[]}`.

---

## Code Examples

### localStorage Persistence for HealthSettings (Test 5 Fix)
```typescript
// Source: ThemeContext.tsx pattern (already established in this codebase)
// In MemoryPanel.tsx — replace:
const [healthSettings, setHealthSettings] = useState<HealthSettings>(DEFAULT_HEALTH_SETTINGS);

// With lazy initializer that reads localStorage:
const [healthSettings, setHealthSettings] = useState<HealthSettings>(() => {
  if (typeof window === 'undefined') return DEFAULT_HEALTH_SETTINGS;
  try {
    const stored = localStorage.getItem('occc-health-settings');
    if (stored) return { ...DEFAULT_HEALTH_SETTINGS, ...JSON.parse(stored) };
  } catch {
    // Ignore parse errors
  }
  return DEFAULT_HEALTH_SETTINGS;
});

// In handleSettingsUpdate:
function handleSettingsUpdate(settings: HealthSettings) {
  setHealthSettings(settings);
  try {
    localStorage.setItem('occc-health-settings', JSON.stringify(settings));
  } catch {
    // Ignore quota errors
  }
}
```

### Auto-Rescan After Memory Edit (Test 4 Fix)
```typescript
// Source: MemoryPanel.tsx handleEditMemory — add runHealthScan() call
async function handleEditMemory(id: string, content: string): Promise<void> {
  const res = await fetch(`/api/memory/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  await mutate();
  // Trigger re-scan so health flags reflect updated content
  await runHealthScan();
}
```

### Seed Memories for Health Scan Testing
```bash
# Seed two memories with similar content for conflict detection
# (Run these via curl against the live memU service)
curl -X POST http://localhost:18791/memorize \
  -H "Content-Type: application/json" \
  -d '{"resource_url": "The pumplai payment gateway uses Stripe API v3 for all transactions", "modality": "conversation", "user": {"user_id": "pumplai", "run_id": "test-seed-1", "agent_id": "main"}}'

curl -X POST http://localhost:18791/memorize \
  -H "Content-Type: application/json" \
  -d '{"resource_url": "PumplAI payment processing is handled by Stripe API version 3", "modality": "conversation", "user": {"user_id": "pumplai", "run_id": "test-seed-2", "agent_id": "main"}}'

# Health scan with relaxed thresholds to immediately detect these
curl -X POST http://localhost:18791/memories/health-scan \
  -H "Content-Type: application/json" \
  -d '{"user_id":"pumplai","age_threshold_days":0,"retrieval_window_days":0,"similarity_min":0.75,"similarity_max":0.97}'
```

### Seed Activity Log for suggest.py
```python
# Write synthetic failed task entries to workspace-state.json
# (Path varies by project — use get_state_path())
import json, time

state_path = "/path/to/workspace-state.json"  # confirm via get_state_path('pumplai')
with open(state_path) as f:
    state = json.load(f)

# Add 3 failed tasks mentioning "authentication" — meets MIN_CLUSTER_SIZE=3
for i in range(3):
    state.setdefault("tasks", {})[f"test-task-{i}"] = {
        "activity_log": [{
            "status": "failed",
            "entry": f"Task failed: authentication token expired during API call {i}",
            "timestamp": time.time() - (i * 100),
        }]
    }

with open(state_path, "w") as f:
    json.dump(state, f, indent=2)
```

### Rebuild memU Image
```bash
cd /home/ollie/.openclaw/docker/memory
docker compose build --no-cache  # or just 'docker compose build' if faster
docker compose up -d
sleep 5  # Wait for startup
curl http://localhost:18791/health  # Should return {"status":"ok","memu_initialized":true}
curl http://localhost:18791/openapi.json | python3 -c "import json,sys; [print(k) for k in json.load(sys.stdin)['paths']]"
# Must show /memories/health-scan
```

### Start Dashboard
```bash
export OPENCLAW_ROOT=/home/ollie/.openclaw
make dashboard  # or: cd packages/dashboard && bun install && bun run dev
# Verify: curl http://localhost:6987/api/projects
```

---

## Test-by-Test Risk Assessment

| Test | Description | Risk Level | Known Issues |
|------|-------------|------------|--------------|
| T1 | Health scan populates flag badges | HIGH | memU image stale (no health-scan endpoint); no test memories |
| T2 | Archive stale flag PUT succeeds + toast | HIGH | memU image stale (no PUT endpoint); no stale memories |
| T3 | Conflict badge click opens ConflictPanel | HIGH | memU image stale; no conflict memories; need embeddings |
| T4 | Editing flagged memory triggers re-scan | MEDIUM | Auto-rescan not implemented — code fix required |
| T5 | Threshold adjustment persists across refresh | HIGH | Not implemented — localStorage fix required |
| T6 | /suggestions renders without errors | LOW | Should work with empty state (EMPTY_STATE fallback) |
| T7 | Accepting suggestion appends + re-renders SOUL | MEDIUM | Need valid pending suggestion with diff_text; soul-override.md exists for pumplai |
| T8 | Sidebar badge shows correct pending count | LOW | Works if projectId matches localStorage; suggestions seeded |
| T9 | POST /api/suggestions invokes suggest.py | MEDIUM | suggest.py needs clusterable data; 60s timeout may be tight |

---

## Open Questions

1. **Where does workspace-state.json for pumplai actually live?**
   - What we know: `get_state_path('pumplai')` resolves based on `OPENCLAW_ROOT` and project workspace. For pumplai, workspace is `/home/ollie/Development/Projects/pumplai`. The state file should be at `/home/ollie/Development/Projects/pumplai/.openclaw/pumplai/workspace-state.json`.
   - What's unclear: File does not exist at that path currently (verified). `suggest.py` gracefully returns [] on missing state file.
   - Recommendation: Create the state file with synthetic activity entries rather than relying on existing data.

2. **Does conflict detection work with fresh memories?**
   - What we know: `_find_conflicts()` requires `item.embedding is not None`. Embeddings are generated by memU at memorize time (via OpenAI API). The memU service requires `OPENAI_API_KEY`.
   - What's unclear: Is the `OPENAI_API_KEY` configured in the Docker environment? If not, memorize will fail and no embeddings → no conflicts.
   - Recommendation: Pre-flight check should include `POST /memorize` with a simple payload and confirm the response is `{"status":"accepted"}`, then wait and verify the memory appears in `GET /memories?user_id=pumplai`.

3. **Success criterion 4 interpretation: "triggers re-scan automatically" — is it truly automatic?**
   - What we know: Current code does NOT auto-rescan after edit.
   - What's unclear: Does the test require automatic behavior, or is "re-scan manually after edit" acceptable?
   - Recommendation: Implement auto-rescan (add `runHealthScan()` call in `handleEditMemory`) since the criterion says "automatically" — this is a straightforward one-line fix.

---

## Pre-Flight Checklist (for Plan)

The plan should include this explicit pre-flight before any test:

```bash
# 1. Rebuild memU image
cd /home/ollie/.openclaw/docker/memory
docker compose build && docker compose up -d
sleep 10

# 2. Verify memU health + new endpoints
curl http://localhost:18791/health
curl http://localhost:18791/openapi.json | python3 -c "import json,sys; paths=json.load(sys.stdin)['paths']; assert '/memories/health-scan' in paths, 'FAIL: health-scan missing'; print('PASS: health-scan endpoint present')"

# 3. Start dashboard
export OPENCLAW_ROOT=/home/ollie/.openclaw
cd /home/ollie/.openclaw && make dashboard &
sleep 5
curl http://localhost:6987/ | head -1  # Should return HTML

# 4. Seed test memory
curl -X POST http://localhost:18791/memorize -H "Content-Type: application/json" \
  -d '{"resource_url":"test memory alpha","modality":"conversation","user":{"user_id":"pumplai","run_id":"preflight","agent_id":"main"}}'

# 5. Verify seed
sleep 3  # Wait for async memorize
TOTAL=$(curl -s http://localhost:18791/memories?user_id=pumplai | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('items',[])))")
echo "Memories for pumplai: $TOTAL (expect ≥ 1)"
```

---

## Validation Architecture

> `workflow.nyquist_validation` is not set in `.planning/config.json` — the key is absent.
> Skipping Validation Architecture section per instructions.

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection: `/home/ollie/.openclaw/packages/dashboard/src/components/memory/MemoryPanel.tsx` — health settings state management, scan flow
- Direct file inspection: `/home/ollie/.openclaw/packages/dashboard/src/components/memory/SettingsPanel.tsx` — settings panel behavior (no localStorage)
- Direct file inspection: `/home/ollie/.openclaw/packages/dashboard/src/components/layout/Sidebar.tsx` — badge polling logic
- Direct file inspection: `/home/ollie/.openclaw/docker/memory/memory_service/routers/memories.py` — memU router with health-scan, PUT endpoints
- Direct file inspection: `/home/ollie/.openclaw/docker/memory/memory_service/service.py` — `run_health_scan()` implementation
- Direct file inspection: `/home/ollie/.openclaw/packages/dashboard/src/app/api/suggestions/[id]/action/route.ts` — accept flow, soul-override.md append, soul_renderer.py invocation
- Direct file inspection: `/home/ollie/.openclaw/packages/orchestration/src/openclaw/cli/suggest.py` — full extraction pipeline
- Live service probe: `curl http://localhost:18791/openapi.json` — confirmed 5 routes (missing health-scan, PUT, health-flags)
- Live service probe: `curl http://localhost:18791/memories?user_id=pumplai` — confirmed 0 memories
- `docker inspect openclaw-memory --format "{{.Created}}"` — confirmed build date 2026-02-24T06:51:38Z
- File timestamp inspection: `memories.py` last modified 2026-02-24T18:30 (after container build)

### Secondary (MEDIUM confidence)
- ThemeContext.tsx pattern for localStorage in lazy initializer — verified as established project pattern

---

## Metadata

**Confidence breakdown:**
- Service topology and API contracts: HIGH — direct code inspection + live probing
- Known bugs/gaps (settings persistence, auto-rescan): HIGH — code confirmed no localStorage, no auto-rescan
- Stale Docker image: HIGH — build timestamp vs file timestamp confirmed
- Seeding strategy for embeddings: MEDIUM — depends on OPENAI_API_KEY being configured in Docker env (not verified directly)
- suggest.py path resolution: MEDIUM — get_state_path() behavior confirmed in code, actual file path not verified to exist

**Research date:** 2026-02-25
**Valid until:** 2026-03-11 (14 days — stable codebase, no external API changes)
