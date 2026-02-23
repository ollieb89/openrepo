# Phase 15: Dashboard Project Switcher - Research

**Researched:** 2026-02-23
**Domain:** Next.js API route parameterization, React state management, SSE reconnection, filesystem project discovery
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Project selector UX:**
- Compact dropdown in the dashboard header, next to the OpenClaw logo/title
- Each project entry shows name + colored status badge (active/idle/error)
- Projects auto-discovered by scanning the `projects/` directory for `project.json` files — no manual config needed

**Switch transition:**
- Brief loading skeleton (~200-500ms) while new project data loads
- Old project data clears immediately on switch — no stale data visible
- Panels show loading state, then populate with new project's data

**Data scoping:**
- Strictly one project at a time — no aggregate/cross-project view
- SSE stream reconnects per project switch: close current connection, open new one with `?project=<id>`
- API routes accept `?project=<id>` parameter for scoping
- Unknown project ID returns 404; missing parameter defaults to first available project

### Claude's Discretion

- Loading skeleton design and animation
- Exact dropdown component styling and positioning
- How status badge color/state is determined from project data
- Default project selection logic on first load (first alphabetical, most recent, etc.)
- localStorage persistence of last-selected project

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DSH-05 | Project selector dropdown in occc header showing all available projects | New `/api/projects` endpoint + `ProjectSelector` component in `GlobalMetrics` header |
| DSH-06 | `/api/swarm` route accepts `?project=<id>` and returns project-scoped state | Modify `route.ts` to read `searchParams`, resolve state path via `get_state_path(project_id)` logic in TypeScript |
| DSH-07 | SSE stream route `/api/swarm/stream` accepts `?project=<id>` and streams project-scoped events | Modify `stream/route.ts` to accept project param; `useSwarmState` closes and reopens SSE when project changes |
| DSH-08 | Task list, agent hierarchy, and metrics filter by selected project | Project ID flows down from page-level state through all panel components via props/context |
</phase_requirements>

---

## Summary

The occc dashboard currently has a hardcoded single-project assumption baked into three layers: the API routes read a fixed state file path, the SSE stream watches a fixed file, and the UI has no concept of project selection. Phase 15 threads project awareness through all three layers without introducing a new state management library — the existing SWR + SSE hybrid pattern scales cleanly to per-project URLs.

The core insight is that project scoping is a URL parameter concern, not a global state concern. By accepting `?project=<id>` in the two existing API routes, the React side simply changes which URL it fetches/streams. SWR's cache key is the URL string, so switching projects automatically invalidates the cache and triggers a fresh fetch. The SSE reconnection is already implemented with cleanup logic in `useSwarmState.ts` — it just needs to be driven by a `projectId` prop rather than being hardcoded.

Project discovery (DSH-05) requires a new `/api/projects` endpoint that scans `projects/*/project.json` on the filesystem. This is a simple Node.js `fs.readdir` + `JSON.parse` operation, no new libraries needed. The dropdown sits in the existing `GlobalMetrics` header component, which already occupies the full header bar.

**Primary recommendation:** Keep the implementation purely inside the existing Next.js app with no new dependencies. The project selector is a controlled React dropdown backed by `useState` in `page.tsx`; the selected project ID is passed as a query parameter to all data hooks; SWR handles cache invalidation automatically.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js App Router | 16.1.6 (already installed) | API route query params, server-side file reads | Already in use; `searchParams` from `NextRequest` |
| React `useState` | 19.2.3 (already installed) | Project selector state in `page.tsx` | No external store needed for single string state |
| SWR | 2.4.0 (already installed) | Per-project data fetching with automatic cache invalidation | Cache key is the URL — changing `?project=` automatically invalidates |
| `EventSource` (browser API) | native | SSE connection per project | Already used in `useSwarmState.ts`; close + reopen on project change |
| `localStorage` | browser API | Persist last-selected project across page reloads | No library needed; simple get/set in `useEffect` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | 0.572.0 (already installed) | Dropdown chevron icon (`ChevronDown`) | Status badge icons for project selector |
| Node.js `fs/promises` | built-in | Scan `projects/` dir, read `project.json` files | Server-side in `/api/projects` route |
| Tailwind CSS v4 | already installed | Dropdown styling, status badge colors | Match existing design tokens |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `useState` in page.tsx | Zustand / Jotai global store | Store adds dependency and complexity; single string state does not warrant it |
| Native `<select>` dropdown | Radix UI / shadcn Select | Radix adds ~30KB and a new dep; native styled select fits the compact header requirement |
| Filesystem scan on every request | Caching `/api/projects` in memory | For <20 projects, filesystem scan is fast enough; caching adds complexity; can be added later |

**Installation:** No new packages required. All needed libraries are already in `package.json`.

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── app/
│   ├── api/
│   │   ├── projects/
│   │   │   └── route.ts          # NEW: GET /api/projects — project discovery
│   │   ├── swarm/
│   │   │   ├── route.ts          # MODIFIED: add ?project= param support
│   │   │   └── stream/
│   │   │       └── route.ts      # MODIFIED: add ?project= param support
│   └── page.tsx                  # MODIFIED: add selectedProject state, pass to hooks
├── components/
│   ├── GlobalMetrics.tsx         # MODIFIED: add ProjectSelector dropdown
│   ├── ProjectSelector.tsx       # NEW: dropdown component
│   └── [existing components]    # MODIFIED: receive projectId prop if needed
├── hooks/
│   └── useSwarmState.ts          # MODIFIED: accept projectId param, reconnect SSE on change
└── lib/
    └── projects.ts               # NEW: shared Project type, path resolution helpers
```

### Pattern 1: Project-Scoped API Routes

**What:** API routes read `?project=<id>` from the URL, resolve the state file path, and return 404 on unknown project.

**When to use:** Both `/api/swarm` and `/api/swarm/stream`.

**Example:**
```typescript
// /api/swarm/route.ts (modified GET handler)
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const projectId = searchParams.get('project') || await getDefaultProject();

  if (!projectId) {
    return NextResponse.json({ error: 'No projects found' }, { status: 404 });
  }

  // Resolve state file path using same logic as Python's get_state_path()
  const stateFilePath = resolveStateFilePath(projectId);

  try {
    await fs.access(stateFilePath);
  } catch {
    return NextResponse.json(
      { error: 'Project not found', project: projectId },
      { status: 404 }
    );
  }

  // ... existing state reading logic, using stateFilePath instead of hardcoded path
}
```

### Pattern 2: Project-Aware SWR Keys

**What:** Pass `projectId` to `useSwarmState`; include it in the SWR key and SSE URL.

**When to use:** Any hook that fetches from `/api/swarm`.

**Example:**
```typescript
// hooks/useSwarmState.ts (modified signature)
export function useSwarmState(projectId: string): UseSwarmStateReturn {
  const url = `/api/swarm?project=${encodeURIComponent(projectId)}`;

  const { data, error, mutate, isLoading } = useSWR<SwarmStateResponse>(
    url,   // SWR cache key is URL — changing projectId invalidates cache automatically
    fetcher,
    {
      refreshInterval: 2000,
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
      dedupingInterval: 2000,
    }
  );

  // SSE: reconnect when projectId changes (useEffect dependency)
  const connectSSE = useCallback(() => {
    const eventSource = new EventSource(
      `/api/swarm/stream?project=${encodeURIComponent(projectId)}`
    );
    // ... existing connection logic unchanged
  }, [mutate, projectId]);  // projectId in dependency array triggers reconnect
```

### Pattern 3: Project Discovery Endpoint

**What:** New `/api/projects` route scans `projects/*/project.json` on the server filesystem.

**When to use:** Called once on page load; result drives the dropdown.

**Example:**
```typescript
// /api/projects/route.ts
import { promises as fs } from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';

const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';
const PROJECTS_DIR = path.join(OPENCLAW_ROOT, 'projects');

export interface ProjectInfo {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error';
}

export async function GET() {
  try {
    const entries = await fs.readdir(PROJECTS_DIR, { withFileTypes: true });
    const projects: ProjectInfo[] = [];

    for (const entry of entries) {
      if (!entry.isDirectory() || entry.name.startsWith('_')) continue;

      const manifestPath = path.join(PROJECTS_DIR, entry.name, 'project.json');
      try {
        const raw = await fs.readFile(manifestPath, 'utf8');
        const manifest = JSON.parse(raw);
        projects.push({
          id: manifest.id,
          name: manifest.name,
          status: 'idle', // Phase 15: status determined by checking state file existence
        });
      } catch {
        // Skip malformed manifests
      }
    }

    // Sort alphabetically by name
    projects.sort((a, b) => a.name.localeCompare(b.name));

    return NextResponse.json({ projects });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to read projects directory', projects: [] },
      { status: 500 }
    );
  }
}
```

### Pattern 4: Immediate Clear on Project Switch

**What:** When project changes, clear the SWR cache entry for the old project immediately before new data loads.

**When to use:** The page-level switch handler.

**Example:**
```typescript
// page.tsx
const [selectedProject, setSelectedProject] = useState<string>('');
const [isSwitching, setIsSwitching] = useState(false);

const handleProjectSwitch = useCallback((projectId: string) => {
  setIsSwitching(true);     // triggers skeleton immediately
  setSelectedProject(projectId);
  // SWR refetch happens automatically via key change
  // isSwitching cleared once useSwarmState returns new data (via useEffect on data)
}, []);
```

### Pattern 5: localStorage Persistence

**What:** Persist and restore the last-selected project ID across reloads.

**When to use:** On initial mount (read) and on every project switch (write).

**Example:**
```typescript
// page.tsx — initial project selection
useEffect(() => {
  const stored = localStorage.getItem('openclaw:selected-project');
  if (stored && projects.some(p => p.id === stored)) {
    setSelectedProject(stored);
  } else if (projects.length > 0) {
    setSelectedProject(projects[0].id); // default: first alphabetical
  }
}, [projects]);

// on switch
const handleProjectSwitch = (projectId: string) => {
  localStorage.setItem('openclaw:selected-project', projectId);
  setSelectedProject(projectId);
};
```

### Anti-Patterns to Avoid

- **Module-level cache in route.ts is per-project-unaware:** The existing `cachedState` variable in `/api/swarm/route.ts` is a module-level singleton. With multi-project support, this cache must be keyed by project ID (e.g., `Map<string, CachedState>`), not a single variable. Using the existing single-variable cache will cause project A data to bleed into project B responses.
- **Not aborting SSE on project switch:** If the old SSE connection is not explicitly closed before opening the new one, both streams run concurrently and the old project's events update the new project's UI. The cleanup in `useEffect` return must fire before the new connection opens.
- **Relative path construction for state files:** Do not reconstruct the state file path by string concatenation independently in TypeScript. Derive it from the same convention as Python's `get_state_path()`: `<OPENCLAW_ROOT>/workspace/.openclaw/<project_id>/workspace-state.json`. Use a shared `resolveStateFilePath(projectId)` function in `src/lib/projects.ts`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SWR cache invalidation on project switch | Manual cache clearing logic | SWR key change (URL with `?project=`) | SWR invalidates automatically when the key string changes — no manual work needed |
| SSE reconnection with backoff | Custom reconnect timer | Existing `useSwarmState` reconnect logic | The backoff timer is already implemented; just add `projectId` to the dependency array |
| Dropdown component | Custom click-outside detection, keyboard nav | Native `<select>` element styled with Tailwind | For a compact header dropdown with ~5 items, native `<select>` avoids all focus management complexity |

**Key insight:** The entire project-switch mechanism is URL parameter driven. SWR and the existing SSE cleanup logic handle all the hard parts already.

---

## Common Pitfalls

### Pitfall 1: Module-Level Cache Is Not Per-Project

**What goes wrong:** The existing `let cachedState: CachedState | null = null` in `route.ts` is a module singleton. When `?project=pumplai` and `?project=geriai` requests arrive, they share the same cache object. The second project's response returns the first project's data.

**Why it happens:** Module-level variables in Next.js API routes persist across requests within the same server process.

**How to avoid:** Replace with `const stateCache = new Map<string, CachedState>()` keyed by project ID.

**Warning signs:** `/api/swarm?project=geriai` returns PumplAI task IDs.

### Pitfall 2: SSE Stream Does Not Receive `request` in Next.js App Router

**What goes wrong:** The existing `stream/route.ts` `GET(request: Request)` signature works. When adding `?project=` support, the URL must be parsed from `request.url`, not from route params (this is a stream route, not a `[project]` dynamic route).

**Why it happens:** Dynamic route segments require the directory to be named `[project]`, which would change the URL structure from `/api/swarm/stream?project=x` to `/api/swarm/stream/x`. The decision is to use query params, not path params.

**How to avoid:** Parse with `new URL(request.url).searchParams.get('project')` in the stream handler — same as the non-stream route.

**Warning signs:** TypeScript error on `params` argument in stream route.

### Pitfall 3: Stale Project State During Loading Skeleton

**What goes wrong:** If the UI shows a loading skeleton but the old project's agents/tasks are still in the SWR cache, components may briefly render the old data after the skeleton disappears.

**Why it happens:** SWR's `isLoading` is only `true` on first load; subsequent fetches use `isValidating`. The page must use `isSwitching` state (set immediately on project switch, cleared when new data arrives) to control skeleton display.

**How to avoid:** Introduce a local `isSwitching` boolean controlled by the project switch handler. Clear it in a `useEffect` that watches `data` changes.

**Warning signs:** Momentary flash of old project's task count in the metrics bar after switching.

### Pitfall 4: `OPENCLAW_ROOT` Path Assumption

**What goes wrong:** The existing route hardcodes `/home/ollie/.openclaw`. In Docker deployment, the workspace is mounted at a different path. Adding more hardcoded paths for `projects/` directory will compound this.

**Why it happens:** Existing code uses `DEFAULT_STATE_FILE` constants with hardcoded paths as fallbacks.

**How to avoid:** Add `OPENCLAW_ROOT` env var support in the new `src/lib/projects.ts` helper. When constructing paths, use `process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw'` as the base. The Docker deployment already sets `STATE_FILE` via env var; extend this pattern.

**Warning signs:** `/api/projects` returns empty list or 500 in Docker; works locally.

### Pitfall 5: Projects Directory Contains Non-Project Subdirectories

**What goes wrong:** The `projects/` directory contains `_templates/` which must not appear in the project list.

**Why it happens:** The scanner iterates all subdirectories without filtering.

**How to avoid:** Skip directories starting with `_` (already shown in Pattern 3 example). Also skip directories that don't contain a `project.json` file.

**Warning signs:** Dropdown shows "_templates" as a selectable project.

---

## Code Examples

### Resolving State File Path in TypeScript

```typescript
// src/lib/projects.ts
const OPENCLAW_ROOT = process.env.OPENCLAW_ROOT || '/home/ollie/.openclaw';

export function resolveStateFilePath(projectId: string): string {
  // Mirrors Python get_state_path() convention:
  // <root>/workspace/.openclaw/<project_id>/workspace-state.json
  return path.join(OPENCLAW_ROOT, 'workspace', '.openclaw', projectId, 'workspace-state.json');
}

export function resolveProjectsDir(): string {
  return path.join(OPENCLAW_ROOT, 'projects');
}
```

Note: The legacy single-project state file lives at `workspace/.openclaw/workspace-state.json` (no project subdirectory). This path corresponds to no specific project ID and is the old v1.0 format. Phase 15 operates with per-project state files at `workspace/.openclaw/<project_id>/workspace-state.json`, which is the v1.1 convention established by Phase 11's `get_state_path()`.

### Per-Project Cache Map

```typescript
// /api/swarm/route.ts (modified)
const stateCache = new Map<string, CachedState>();
const CACHE_TTL_MS = 500;

export async function getSwarmState(projectId: string): Promise<{ ... }> {
  const now = Date.now();
  const cached = stateCache.get(projectId);

  if (cached && now - cached.timestamp < CACHE_TTL_MS) {
    return { agents: cached.agentNodes, metrics: cached.metrics, state: cached.state, lastUpdated: new Date(cached.mtime).toISOString() };
  }

  const stateFilePath = resolveStateFilePath(projectId);
  // ... read file, parse, build hierarchy, then:
  stateCache.set(projectId, { state, agents: agentConfigs, agentNodes, metrics, mtime, timestamp: now });
  // ...
}
```

### ProjectSelector Component (Skeleton)

```tsx
// src/components/ProjectSelector.tsx
'use client';

import React from 'react';
import { ChevronDown } from 'lucide-react';

interface Project {
  id: string;
  name: string;
  status: 'active' | 'idle' | 'error';
}

const statusBadgeClass: Record<Project['status'], string> = {
  active: 'bg-teal-100 text-teal-700',
  idle:   'bg-slate-100 text-slate-600',
  error:  'bg-red-100 text-red-700',
};

interface ProjectSelectorProps {
  projects: Project[];
  selectedId: string;
  onSelect: (id: string) => void;
}

export function ProjectSelector({ projects, selectedId, onSelect }: ProjectSelectorProps) {
  const selected = projects.find(p => p.id === selectedId);

  return (
    <div className="relative flex items-center space-x-2 ml-4">
      {selected && (
        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${statusBadgeClass[selected.status]}`}>
          {selected.status}
        </span>
      )}
      <div className="relative">
        <select
          value={selectedId}
          onChange={e => onSelect(e.target.value)}
          className="appearance-none pl-3 pr-7 py-1.5 text-sm font-medium bg-white border border-slate-200 rounded cursor-pointer text-slate-800 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          {projects.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
      </div>
    </div>
  );
}
```

### Project Status Derivation

The `status` field on a project entry should reflect whether that project has active L3 containers running. For Phase 15 scope, a reasonable heuristic is: check if the project's state file exists and has any `in_progress` tasks → `active`; has `failed` tasks and none in_progress → `error`; otherwise → `idle`.

```typescript
// In /api/projects/route.ts
async function deriveProjectStatus(projectId: string): Promise<Project['status']> {
  const stateFilePath = resolveStateFilePath(projectId);
  try {
    const raw = await fs.readFile(stateFilePath, 'utf8');
    const state = JSON.parse(raw);
    const tasks = Object.values(state.tasks || {}) as Array<{ status: string }>;
    if (tasks.some(t => t.status === 'in_progress')) return 'active';
    if (tasks.some(t => t.status === 'failed')) return 'error';
    return 'idle';
  } catch {
    return 'idle'; // no state file = no activity
  }
}
```

---

## Existing Codebase: Key Facts for Planning

These facts from the current codebase directly affect task design:

1. **`getSwarmState()` in `route.ts` is exported** and imported by `stream/route.ts`. Any refactoring of `getSwarmState` to accept `projectId` must maintain this import contract.

2. **`useSwarmState` currently takes no arguments.** All call sites in `page.tsx` will need to be updated to pass `projectId`.

3. **The `GlobalMetrics` component receives only `metrics: SwarmMetrics` as a prop.** To add the `ProjectSelector` into the header, either pass additional props to `GlobalMetrics`, or extract the header into `page.tsx` and compose `GlobalMetrics` and `ProjectSelector` side-by-side.

4. **The legacy state file** at `workspace/.openclaw/workspace-state.json` (no project subdirectory) is the v1.0 path still in use as the `DEFAULT_STATE_FILE` constant. Per-project paths (`workspace/.openclaw/<id>/workspace-state.json`) are the v1.1 convention. The `/api/swarm` route currently points at the legacy path. Phase 15 switches it to per-project paths.

5. **Two projects already exist:** `pumplai` (id: `pumplai`) and `geriai` (id: `geriai`). Only `pumplai` has a `soul-override.md`. The `pumplai` project is the `active_project` in `openclaw.json`.

6. **No per-project state files exist yet** under `workspace/.openclaw/pumplai/` — the legacy flat file is at `workspace/.openclaw/workspace-state.json`. The default project fallback in `/api/projects` should gracefully handle missing state files (return `idle` status, not error).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single global `EventSource` URL | `EventSource` URL parameterized by `projectId` | Phase 15 | SSE reconnects cleanly on project switch |
| Module-level `cachedState` singleton | `Map<projectId, CachedState>` | Phase 15 | Prevents cross-project cache bleed |
| Hardcoded `DEFAULT_STATE_FILE` | `resolveStateFilePath(projectId)` from shared lib | Phase 15 | Consistent with Python `get_state_path()` convention |

---

## Open Questions

1. **Per-project openclaw.json agent list**
   - What we know: `openclaw.json` has a flat `agents.list` array with all agents across all projects. `pumplai_pm` reports to `clawdia_prime` with `pumplai` workspace. `geriai_pm` does not exist in the list yet.
   - What's unclear: Should `/api/swarm?project=geriai` return agents filtered by project from `openclaw.json`, or return all agents? The `project.json` has `agents.l2_pm = "geriai_pm"` but `geriai_pm` is not in `openclaw.json:agents.list`.
   - Recommendation: Filter `openclaw.json` agents by cross-referencing `project.json:agents` values for the selected project. For `geriai`, the agent hierarchy panel will show 0 agents (correct — none configured yet). This avoids showing PumplAI agents when viewing GerIAI.

2. **Missing per-project state files**
   - What we know: `workspace/.openclaw/pumplai/workspace-state.json` may not exist (only the legacy flat file exists). The spec says unknown project ID returns 404.
   - What's unclear: Should a project with a valid `project.json` but no state file return 404 or an empty state?
   - Recommendation: Return an empty-but-valid JarvisState (zero tasks, current timestamp) when the state file does not exist. This is consistent with how a new project would appear before any L3 work runs. Reserve 404 for completely unknown project IDs (no `project.json`).

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection (`/home/ollie/.openclaw/workspace/occc/src/**`) — existing API route structure, SWR usage, SSE implementation, component props
- `orchestration/project_config.py` — Python `get_state_path()` convention used to derive TypeScript equivalent
- `projects/pumplai/project.json`, `projects/geriai/project.json` — actual project data structure
- `openclaw.json` — agent list and active_project field
- Next.js App Router documentation (verified against existing route files) — `searchParams` in `NextRequest`, dynamic vs query params

### Secondary (MEDIUM confidence)

- SWR documentation behavior: SWR cache key is the first argument to `useSWR`; changing the URL triggers automatic revalidation (verified against existing `useSwarmState.ts` which already relies on this)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies needed
- Architecture: HIGH — based on direct codebase inspection; patterns extend existing code rather than introducing new paradigms
- Pitfalls: HIGH — identified from direct reading of existing code (module-level cache, hardcoded paths, `_templates` directory)

**Research date:** 2026-02-23
**Valid until:** 2026-03-23 (stable stack — Next.js 16, React 19, SWR 2.4 are not fast-moving)
