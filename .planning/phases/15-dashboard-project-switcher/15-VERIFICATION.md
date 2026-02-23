---
phase: 15-dashboard-project-switcher
verified: 2026-02-23T22:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Open http://localhost:6987 in a browser and confirm the project selector dropdown appears in the dashboard header between the OPENCLAW COMMAND branding and the LIVE badge"
    expected: "A styled native select element with colored status badges is visible. It shows at least pumplai (and geriai if configured)."
    why_human: "Visual rendering of the ProjectSelector component cannot be verified programmatically from the source code alone"
  - test: "If two or more projects exist (pumplai and geriai are both present), switch between them in the header dropdown"
    expected: "A brief loading skeleton (~200-500ms) appears. Task list, agent hierarchy, and metrics update without a full page reload. No stale data from the previous project remains visible."
    why_human: "Project switching behaviour, data-panel refreshes, and stale-data clearance require live browser interaction"
  - test: "Select a project, then reload the page (F5)"
    expected: "The same project is pre-selected after reload — the selection is restored from localStorage key 'openclaw:selected-project'"
    why_human: "localStorage persistence across page reloads can only be confirmed in a running browser"
  - test: "Open browser DevTools Network tab, then switch projects"
    expected: "The old SSE connection (EventStream to /api/swarm/stream?project=<old>) closes; a new connection opens to /api/swarm/stream?project=<new>; an XHR/fetch to /api/swarm?project=<new> is visible"
    why_human: "Network-level SSE reconnect behaviour requires browser DevTools observation"
---

# Phase 15: Dashboard Project Switcher — Verification Report

**Phase Goal:** The occc dashboard is usable with multiple projects; users can switch the active project from the UI; all data panels (tasks, agents, metrics) reflect only the selected project's state.

**Verified:** 2026-02-23T22:30:00Z
**Status:** human_needed (all automated checks passed; 4 human tests remain)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GET /api/projects returns a JSON array of all projects discovered from projects/*/project.json, excluding _templates | VERIFIED | `projects/route.ts` L40: `entry.name.startsWith('_')` skip; reads `project.json`; returns `{ projects }` at L60 |
| 2  | GET /api/swarm?project=pumplai returns only PumplAI state data | VERIFIED | `swarm/route.ts` L124: `searchParams.get('project')`; resolves `resolveStateFilePath(projectId)`; validates via `project.json` at L136-144 |
| 3  | GET /api/swarm?project=nonexistent returns 404 | VERIFIED | `swarm/route.ts` L140-144: `fs.access(projectJsonPath)` throws on missing project, returns 404 `{ error: 'Project not found' }` |
| 4  | GET /api/swarm (no param) defaults to first available project instead of crashing | VERIFIED | `swarm/route.ts` L127-129: `if (!projectId) { projectId = await getDefaultProject(); }` |
| 5  | GET /api/swarm/stream?project=pumplai streams only PumplAI state events | VERIFIED | `stream/route.ts` L7: `searchParams.get('project')`; L55: `resolveStateFilePath(projectId)`; L61+106: `getSwarmState(projectId)` / `getSwarmState(resolvedProjectId)` |
| 6  | Module-level cache in route.ts is per-project (Map keyed by projectId), not a singleton | VERIFIED | `swarm/route.ts` L18: `const stateCache = new Map<string, CachedState>()`; L49, 64, 85: keyed by `projectId` |
| 7  | A project selector dropdown appears in the dashboard header showing all available projects | VERIFIED (code) / HUMAN NEEDED (visual) | `ProjectSelector.tsx` 64 lines: native `<select>`, status badges, ChevronDown icon; rendered in `GlobalMetrics.tsx` L32-37 when `projects && selectedProject && onProjectSwitch` |
| 8  | Selecting a different project updates all data panels without a full page reload | VERIFIED (code) / HUMAN NEEDED (runtime) | `page.tsx` L151: `useSwarmState(selectedProject)`; `handleProjectSwitch` at L141 sets `selectedProject`; all panels receive scoped `agents`, `metrics`, `state` |
| 9  | A loading skeleton displays briefly during project switch while new data loads | VERIFIED (code) / HUMAN NEEDED (runtime) | `page.tsx` L142: `setIsSwitching(true)` on switch; L165: `if (isLoading || isSwitching) return <LoadingState />`; L155: cleared when `!isValidating` |
| 10 | The SSE stream reconnects to the new project's stream on switch | VERIFIED (code) / HUMAN NEEDED (runtime) | `useSwarmState.ts` L115: `[mutate, projectId]` dependency array on `connectSSE`; L117-134: `useEffect([connectSSE])` fires cleanup (closes old EventSource) and re-runs `connectSSE` |
| 11 | The last-selected project persists across page reloads via localStorage | VERIFIED (code) / HUMAN NEEDED (runtime) | `page.tsx` L20: `const LS_KEY = 'openclaw:selected-project'`; L145: `localStorage.setItem(LS_KEY, projectId)` on switch; L122-126: restored on mount |

**Score:** 11/11 truths — all verified at code level; 4 require runtime human confirmation

---

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Key Evidence |
|----------|-----------|--------------|--------|--------------|
| `workspace/occc/src/lib/projects.ts` | 20 | 56 | VERIFIED | Exports `OPENCLAW_ROOT`, `ProjectInfo`, `resolveStateFilePath`, `resolveProjectsDir`, `getDefaultProject` |
| `workspace/occc/src/app/api/projects/route.ts` | 30 | 69 | VERIFIED | GET handler; scans projects dir; derives status; excludes `_`-prefixed dirs; returns sorted `{ projects }` |
| `workspace/occc/src/app/api/swarm/route.ts` | — | 167 | VERIFIED | `searchParams.get` present L124; `stateCache` Map L18; `getSwarmState(projectId)` exported L40; 404 on unknown project |
| `workspace/occc/src/app/api/swarm/stream/route.ts` | — | 154 | VERIFIED | `searchParams.get` present L7; uses `resolveStateFilePath(projectId)` L55; calls `getSwarmState(projectId)` |
| `workspace/occc/src/components/ProjectSelector.tsx` | 30 | 64 | VERIFIED | `'use client'`; native `<select>`; `ChevronDown` icon; status badge map; shimmer on `isLoading` |
| `workspace/occc/src/hooks/useSwarmState.ts` | — | 153 | VERIFIED | `useSwarmState(projectId: string)` signature L36; SWR URL L38; SSE URL L70; `isValidating` exposed L23, 150 |
| `workspace/occc/src/components/GlobalMetrics.tsx` | — | 101 | VERIFIED | `ProjectSelector` imported L6; rendered L32-37 with guard; `projects?`, `selectedProject?`, `onProjectSwitch?` props L10-12 |
| `workspace/occc/src/app/page.tsx` | — | 214 | VERIFIED | `selectedProject` state L104; `isSwitching` state L105; `handleProjectSwitch` L141; `localStorage` L145; `useSwarmState(selectedProject)` L151 |

---

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|----------|
| `api/projects/route.ts` | `lib/projects.ts` | `import resolveProjectsDir, resolveStateFilePath` | WIRED | L4: `import { ProjectInfo, resolveProjectsDir, resolveStateFilePath } from '@/lib/projects'` |
| `api/swarm/route.ts` | `lib/projects.ts` | `import resolveStateFilePath` | WIRED | L6: `import { resolveStateFilePath, resolveProjectsDir, getDefaultProject } from '@/lib/projects'`; L25 + L136 usage |
| `api/swarm/stream/route.ts` | `api/swarm/route.ts` | `import getSwarmState (accepts projectId)` | WIRED | L2: `import { getSwarmState, emptySwarmState } from '@/app/api/swarm/route'`; L61 + L106 calls with `projectId` |
| `page.tsx` | `hooks/useSwarmState.ts` | `useSwarmState(selectedProject)` call | WIRED | L4 import; L151: `useSwarmState(selectedProject)` — projectId argument confirmed |
| `hooks/useSwarmState.ts` | `/api/swarm?project=` | SWR URL includes project param | WIRED | L38: `` `/api/swarm?project=${encodeURIComponent(projectId)}` `` |
| `hooks/useSwarmState.ts` | `/api/swarm/stream?project=` | EventSource URL includes project param | WIRED | L70: `` `/api/swarm/stream?project=${encodeURIComponent(projectId)}` `` |
| `components/GlobalMetrics.tsx` | `components/ProjectSelector.tsx` | `<ProjectSelector` rendered inside header | WIRED | L6 import; L32-37: `<ProjectSelector projects={...} selectedId={...} onSelect={...} />` |

All 7 key links WIRED.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DSH-05 | 15-01, 15-02 | Project selector dropdown in occc header showing all available projects | SATISFIED | `ProjectSelector.tsx` rendered in `GlobalMetrics.tsx` header; `api/projects` discovery endpoint feeds the list |
| DSH-06 | 15-01 | `/api/swarm` route accepts `?project=<id>` and returns project-scoped state | SATISFIED | `swarm/route.ts` L124: `searchParams.get('project')`; per-project `stateCache` Map; 404 on unknown project |
| DSH-07 | 15-01 | SSE stream route `/api/swarm/stream` accepts `?project=<id>` and streams project-scoped events | SATISFIED | `stream/route.ts` L7: `searchParams.get('project')`; `resolveStateFilePath(projectId)` L55; `getSwarmState(projectId)` in poll loop |
| DSH-08 | 15-01, 15-02 | Task list, agent hierarchy, and metrics filter by selected project | SATISFIED | `page.tsx` passes `agents`, `metrics`, `state` from `useSwarmState(selectedProject)` to `AgentHierarchy`, `AgentDetail`, `GlobalMetrics` — all data is project-scoped via the hook |

No orphaned requirements — all four DSH-05 through DSH-08 IDs mapped to Phase 15 in REQUIREMENTS.md are accounted for across the two plans.

---

### Anti-Patterns Found

None. No TODO/FIXME/HACK/PLACEHOLDER comments found in any of the 8 key files. No empty implementations (`return null`, `return {}`, `return []`) in component or hook files. No console-log-only implementations.

---

### Commit Verification

Plan 01 commits verified in workspace submodule git history:
- `e73aa7b` — `feat(15-01): add shared project helpers and /api/projects discovery endpoint`
- `2feed29` — `feat(15-01): add project-scoping to /api/swarm and /api/swarm/stream routes`

Plan 02 commits verified in workspace submodule git history:
- `c909492` — `feat(15-02): add ProjectSelector component and project-aware useSwarmState hook`
- `45ccddf` — `feat(15-02): wire project selection through page.tsx and GlobalMetrics header`

Two additional fix commits also present:
- `02b9970` — `fix(15-02): add required version and metadata fields to emptySwarmState`
- `03ecb36` — `fix(15-02): handle missing state files gracefully in stream route`

---

### Human Verification Required

#### 1. Project Selector Visible in Header

**Test:** Start the dev server (`cd workspace/occc && bun run dev`). Open http://localhost:6987. Inspect the header area.
**Expected:** A native `<select>` dropdown with a colored status badge (teal/slate/red) appears between "OPENCLAW COMMAND" branding and the "LIVE" indicator. It lists at minimum "pumplai" (and "geriai" if its project.json is correctly structured).
**Why human:** Visual rendering of React components cannot be confirmed from source code alone.

#### 2. Project Switching Updates All Panels (No Page Reload)

**Test:** If two projects are available, select a different one from the dropdown.
**Expected:** A brief shimmer skeleton (~200-500ms) appears, then all panels (agent hierarchy, task detail, metrics bar) update to reflect the newly selected project. No stale data from the previous project is visible.
**Why human:** Dynamic state transitions and data-panel refresh require browser execution.

#### 3. localStorage Persistence Across Reloads

**Test:** Select a specific project in the dropdown. Press F5 or Cmd+R to reload the page.
**Expected:** The same project is pre-selected after reload. Verify via `localStorage.getItem('openclaw:selected-project')` in DevTools console.
**Why human:** localStorage read/write across page reload cannot be exercised without a running browser.

#### 4. SSE Stream Reconnects on Project Switch

**Test:** Open DevTools → Network → Filter by "EventStream". Switch projects in the UI.
**Expected:** The old SSE connection to `/api/swarm/stream?project=<old>` closes; a new connection opens to `/api/swarm/stream?project=<new>`. A new XHR to `/api/swarm?project=<new>` is also visible.
**Why human:** Network-level connection lifecycle requires live browser DevTools observation.

---

### Summary

The phase goal is fully implemented at the code level. All 11 observable truths map to substantive, wired implementations:

- The backend layer (`lib/projects.ts`, `api/projects`, `api/swarm`, `api/swarm/stream`) correctly scopes all data to a `?project=` query parameter, falls back to the first available project when the param is absent, returns 404 for unknown projects, and uses a per-project `Map` cache to prevent cross-project state bleed.
- The frontend layer (`ProjectSelector.tsx`, `useSwarmState.ts`, `GlobalMetrics.tsx`, `page.tsx`) correctly renders a styled native select in the header, threads `selectedProject` through all data hooks, triggers a loading skeleton on switch, reconnects SSE via `useEffect` cleanup, and persists the selection to `localStorage`.
- Both projects on disk (`pumplai`, `geriai`) are real directories with `project.json` files; `_templates` is correctly excluded.
- All 4 requirement IDs (DSH-05 through DSH-08) are satisfied with direct code evidence.

Four items require human browser verification: visual appearance of the dropdown, runtime project-switching behavior, localStorage persistence, and SSE reconnect in the Network tab.

---

_Verified: 2026-02-23T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
