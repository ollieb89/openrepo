# Unified Shell Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire `openclaw/ui` (Lit/Vite) as the primary shell and mount `packages/dashboard` (Next.js) as a subsection at `/occc/*`, giving operators one coherent UI with a single browser origin.

**Architecture:** A reverse proxy routes `/` to the Lit/Vite app and `/occc/*` to the Next.js app. `openclaw/ui` grows an "Operations" nav group with plain external links. The dashboard replaces its full `Sidebar` + `Header` with a thin `OcccShell` (48px bar with a back link and breadcrumb). Both apps share canonical route metadata via matching key constants.

**Tech Stack:** Node.js `http-proxy` (dev proxy), nginx (prod), Lit/TypeScript (openclaw/ui), Next.js 15 + React 19 + Tailwind (dashboard), Vitest (tests for both)

**Design reference:** `docs/plans/2026-03-06-unified-shell-integration-design.md`

---

## Pre-flight: what is already done

Before starting, verify these are already in place:

- `packages/dashboard/next.config.js` has `basePath: '/occc'` — **already done**
- `packages/dashboard/src/lib/api-client.ts` exports `apiPath()`, `apiFetch()`, `apiJson()` with `/occc` prefix — **already done**

Run the dashboard to confirm it loads correctly at `http://localhost:6987/occc`:

```bash
cd packages/dashboard && pnpm dev
# visit http://localhost:6987/occc — should show dashboard (not 404)
```

If it 404s, the basePath is not aligned with the server port. That is a configuration problem to fix before continuing.

---

## Task 1: `occc-routes.ts` — canonical route metadata

**Files:**
- Create: `packages/dashboard/src/lib/occc-routes.ts`
- Create: `packages/dashboard/tests/lib/occc-routes.test.ts`

The keys in this file must exactly match the `key` field in `OCCC_NAV` (added in Task 5). Both are the single source of truth for their respective apps.

**Step 1: Write the failing test**

```typescript
// packages/dashboard/tests/lib/occc-routes.test.ts
import { describe, it, expect } from 'vitest';
import { OCCC_ROUTE_META, resolveSection } from '@/lib/occc-routes';

describe('OCCC_ROUTE_META', () => {
  it('contains all six required sections', () => {
    const keys = Object.keys(OCCC_ROUTE_META);
    expect(keys).toContain('mission-control');
    expect(keys).toContain('tasks');
    expect(keys).toContain('metrics');
    expect(keys).toContain('memory');
    expect(keys).toContain('topology');
    expect(keys).toContain('agents');
  });

  it('every entry has a non-empty label', () => {
    for (const [key, meta] of Object.entries(OCCC_ROUTE_META)) {
      expect(meta.label, `label for "${key}"`).toBeTruthy();
    }
  });
});

describe('resolveSection', () => {
  it('resolves top-level section paths', () => {
    expect(resolveSection('/mission-control')).toEqual({ key: 'mission-control', label: 'Mission Control' });
    expect(resolveSection('/tasks')).toEqual({ key: 'tasks', label: 'Tasks' });
    expect(resolveSection('/memory')).toEqual({ key: 'memory', label: 'Memory' });
  });

  it('resolves subroutes to their parent section', () => {
    expect(resolveSection('/memory/health')).toEqual({ key: 'memory', label: 'Memory' });
    expect(resolveSection('/tasks/review')).toEqual({ key: 'tasks', label: 'Tasks' });
    expect(resolveSection('/agents/some/deep/path')).toEqual({ key: 'agents', label: 'Agents' });
  });

  it('returns null for unknown paths', () => {
    expect(resolveSection('/unknown')).toBeNull();
    expect(resolveSection('/')).toBeNull();
    expect(resolveSection('')).toBeNull();
  });

  it('handles paths with and without leading slash', () => {
    expect(resolveSection('tasks')).toEqual({ key: 'tasks', label: 'Tasks' });
    expect(resolveSection('/tasks')).toEqual({ key: 'tasks', label: 'Tasks' });
  });
});
```

**Step 2: Run test to confirm it fails**

```bash
cd packages/dashboard && pnpm test -- tests/lib/occc-routes.test.ts
```

Expected: FAIL with "Cannot find module '@/lib/occc-routes'"

**Step 3: Write the implementation**

```typescript
// packages/dashboard/src/lib/occc-routes.ts

export type OcccSectionMeta = {
  label: string;
};

export const OCCC_ROUTE_META: Record<string, OcccSectionMeta> = {
  'mission-control': { label: 'Mission Control' },
  'tasks':           { label: 'Tasks' },
  'metrics':         { label: 'Metrics' },
  'memory':          { label: 'Memory' },
  'topology':        { label: 'Topology' },
  'agents':          { label: 'Agents' },
};

/**
 * Resolves a Next.js pathname (without /occc prefix — middleware receives stripped paths)
 * to its canonical section. Subroutes resolve to their top-level parent.
 *
 * Examples:
 *   '/memory'        → { key: 'memory', label: 'Memory' }
 *   '/memory/health' → { key: 'memory', label: 'Memory' }
 *   '/unknown'       → null
 */
export function resolveSection(
  pathname: string,
): { key: string; label: string } | null {
  const normalized = pathname.startsWith('/') ? pathname.slice(1) : pathname;
  if (!normalized) return null;

  // First segment identifies the section
  const firstSegment = normalized.split('/')[0];
  const meta = OCCC_ROUTE_META[firstSegment];
  if (!meta) return null;

  return { key: firstSegment, label: meta.label };
}
```

**Step 4: Run test to confirm it passes**

```bash
cd packages/dashboard && pnpm test -- tests/lib/occc-routes.test.ts
```

Expected: all 5 tests PASS

**Step 5: Commit**

```bash
git add packages/dashboard/src/lib/occc-routes.ts packages/dashboard/tests/lib/occc-routes.test.ts
git commit -m "feat(dashboard): add OCCC_ROUTE_META and resolveSection utility"
```

---

## Task 2: `OcccShell` component

**Files:**
- Create: `packages/dashboard/src/components/layout/OcccShell.tsx`

The shell renders a 48px top bar with a back link (`← OpenClaw` → `/`), a breadcrumb showing the current section, and a slot for optional section-local tabs. It uses `resolveSection` from Task 1.

This is a React client component — not unit-testable in isolation without a DOM. Manual verification via browser after Task 3.

**Step 1: Write the component**

```tsx
// packages/dashboard/src/components/layout/OcccShell.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { resolveSection } from '@/lib/occc-routes';

interface OcccShellProps {
  children: React.ReactNode;
}

export default function OcccShell({ children }: OcccShellProps) {
  const pathname = usePathname();

  // usePathname() returns the path WITH basePath stripped by Next.js in the browser.
  // resolveSection expects the path without /occc prefix.
  const section = resolveSection(pathname ?? '');
  const sectionLabel = section?.label ?? 'OpenClaw Control Center';

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* 48px top bar */}
      <header className="flex items-center gap-3 h-12 px-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shrink-0">
        <Link
          href="/"
          className="flex items-center gap-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
          aria-label="Back to OpenClaw"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M19 12H5" />
            <path d="M12 19l-7-7 7-7" />
          </svg>
          OpenClaw
        </Link>
        <span className="text-gray-300 dark:text-gray-600" aria-hidden="true">/</span>
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {sectionLabel}
        </span>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add packages/dashboard/src/components/layout/OcccShell.tsx
git commit -m "feat(dashboard): add OcccShell embedded layout component"
```

---

## Task 3: Wire `OcccShell` into `layout.tsx` and redirect root

**Files:**
- Modify: `packages/dashboard/src/app/layout.tsx`
- Modify: `packages/dashboard/src/app/page.tsx`

**Step 1: Update `layout.tsx` — replace Sidebar + Header with OcccShell**

Read the current file first (already done above). Replace it entirely:

```tsx
// packages/dashboard/src/app/layout.tsx
import "./globals.css";
import "react-toastify/dist/ReactToastify.css";
import { ThemeProvider } from "@/context/ThemeContext";
import { ProjectProvider } from "@/context/ProjectContext";
import { AuthProvider } from "@/context/AuthContext";
import OcccShell from "@/components/layout/OcccShell";
import { ToastContainer } from "react-toastify";
import BackgroundSyncTrigger from "@/components/sync/BackgroundSyncTrigger";
import SuggestionToast from "@/components/sync/SuggestionToast";
import { EscalationAlertBanner } from "@/components/autonomy/EscalationAlertBanner";

export const metadata = {
  title: "OpenClaw Control Center",
  description: "OpenClaw operator control surface",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AuthProvider>
          <ThemeProvider>
            <BackgroundSyncTrigger />
            <SuggestionToast />
            <EscalationAlertBanner />
            <ProjectProvider>
              <OcccShell>
                {children}
              </OcccShell>
            </ProjectProvider>
            <ToastContainer position="bottom-right" autoClose={3000} theme="colored" />
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
```

**Step 2: Update `page.tsx` — redirect `/occc` → `/occc/mission-control`**

The current `page.tsx` renders an inference preview. Replace it with a redirect:

```tsx
// packages/dashboard/src/app/page.tsx
import { redirect } from 'next/navigation';

export default function RootPage() {
  redirect('/mission-control');
}
```

Note: `redirect('/mission-control')` in a Next.js app with `basePath: '/occc'` produces a redirect to `/occc/mission-control`. Do not add the basePath manually here.

**Step 3: Verify the dashboard still builds**

```bash
cd packages/dashboard && pnpm build 2>&1 | tail -20
```

Expected: build succeeds, no TypeScript errors.

**Step 4: Verify manually in dev**

```bash
cd packages/dashboard && pnpm dev
```

- Visit `http://localhost:6987/occc` — should redirect to `http://localhost:6987/occc/mission-control`
- Should show the mission-control page with the OcccShell top bar (← OpenClaw / Mission Control)
- No sidebar, no standalone header

**Step 5: Commit**

```bash
git add packages/dashboard/src/app/layout.tsx packages/dashboard/src/app/page.tsx
git commit -m "feat(dashboard): wire OcccShell into root layout, redirect / to mission-control"
```

---

## Task 4: `OCCC_NAV` and `OcccNavItem` in `openclaw/ui`

**Files:**
- Modify: `openclaw/ui/src/ui/navigation.ts`
- Modify: `openclaw/ui/src/ui/navigation.test.ts` (add tests)

**Step 1: Write the failing tests**

Open `openclaw/ui/src/ui/navigation.test.ts` and add at the end:

```typescript
// Add to existing navigation.test.ts

import { describe, it, expect } from 'vitest'; // already imported
import { OCCC_NAV } from './navigation.ts'; // add this import

describe('OCCC_NAV', () => {
  it('has six entries with required fields', () => {
    expect(OCCC_NAV).toHaveLength(6);
    for (const item of OCCC_NAV) {
      expect(item.key, 'key').toBeTruthy();
      expect(item.label, 'label').toBeTruthy();
      expect(item.icon, 'icon').toBeTruthy();
      expect(item.href, 'href').toBeTruthy();
    }
  });

  it('all hrefs start with /occc/', () => {
    for (const item of OCCC_NAV) {
      expect(item.href, `href for "${item.key}"`).toMatch(/^\/occc\//);
    }
  });

  it('keys are unique', () => {
    const keys = OCCC_NAV.map(item => item.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it('keys include the six canonical sections', () => {
    const keys = OCCC_NAV.map(item => item.key);
    for (const expected of ['mission-control', 'tasks', 'metrics', 'memory', 'topology', 'agents']) {
      expect(keys).toContain(expected);
    }
  });
});
```

**Step 2: Run test to confirm it fails**

```bash
cd openclaw/ui && pnpm test -- --run navigation.test.ts
```

Expected: FAIL with "OCCC_NAV is not exported from './navigation.ts'"

**Step 3: Add `OcccNavItem` type and `OCCC_NAV` to `navigation.ts`**

Open `openclaw/ui/src/ui/navigation.ts` and add after the `iconForTab` function (at the end of the file):

```typescript
// -- OCCC external navigation (cross-surface links to /occc/*) --

export type OcccNavItem = {
  key: string;       // canonical key — matches OCCC_ROUTE_META keys in dashboard
  label: string;     // display label and title attribute
  icon: IconName;
  href: string;      // full path e.g. "/occc/mission-control"
  match?: string[];  // optional subroute patterns for future breadcrumb use
};

export const OCCC_NAV: OcccNavItem[] = [
  { key: "mission-control", label: "Mission Control", icon: "radio",    href: "/occc/mission-control" },
  { key: "tasks",           label: "Tasks",           icon: "fileText", href: "/occc/tasks"           },
  { key: "metrics",         label: "Metrics",         icon: "barChart", href: "/occc/metrics"         },
  { key: "memory",          label: "Memory",          icon: "brain",    href: "/occc/memory"          },
  { key: "topology",        label: "Topology",        icon: "monitor",  href: "/occc/topology"        },
  { key: "agents",          label: "Agents",          icon: "folder",   href: "/occc/agents"          },
];
```

Note: `iconForTab` uses `"brain"` — verify this icon exists in `openclaw/ui/src/ui/icons.ts`. If `"brain"` is not in the `IconName` union, use `"zap"` for memory instead, or whichever icon name is available in the existing set.

**Step 4: Run test to confirm it passes**

```bash
cd openclaw/ui && pnpm test -- --run navigation.test.ts
```

Expected: all new tests PASS, all existing tests still PASS.

**Step 5: Commit**

```bash
git add openclaw/ui/src/ui/navigation.ts openclaw/ui/src/ui/navigation.test.ts
git commit -m "feat(ui): add OcccNavItem type and OCCC_NAV external nav entries"
```

---

## Task 5: `renderExternalNavItem` and "Operations" group in `openclaw/ui`

**Files:**
- Modify: `openclaw/ui/src/ui/app-render.helpers.ts`
- Modify: `openclaw/ui/src/ui/app-render.ts`

This task has no isolated unit test (Lit html template rendering is not testable in Node vitest without a DOM). Verification is manual in browser.

**Step 1: Add `renderExternalNavItem` to `app-render.helpers.ts`**

At the top of `app-render.helpers.ts`, add `OCCC_NAV` and `OcccNavItem` to the navigation import:

```typescript
// Change this line:
import { iconForTab, pathForTab, titleForTab, type Tab } from "./navigation.ts";
// To:
import { iconForTab, pathForTab, titleForTab, type Tab, OCCC_NAV, type OcccNavItem } from "./navigation.ts";
```

Then add the render function after `renderTab` (around line 83):

```typescript
export function renderExternalNavItem(item: OcccNavItem) {
  return html`
    <a
      href=${item.href}
      class="nav-item"
      title=${item.label}
    >
      <span class="nav-item__icon" aria-hidden="true">${icons[item.icon]}</span>
      <span class="nav-item__text">${item.label}</span>
    </a>
  `;
}

export function renderOperationsGroup() {
  return html`
    <div class="nav-group">
      <div class="nav-group__label">operations</div>
      ${OCCC_NAV.map(item => renderExternalNavItem(item))}
    </div>
  `;
}
```

**Step 2: Add the operations group to `app-render.ts`**

In `app-render.ts`, find where `TAB_GROUPS` nav is rendered (the section that calls `renderTab` for each group). This is typically in the sidebar/nav section of the main app template. Add a call to `renderOperationsGroup()` after the existing tab groups.

First, add to the imports at the top of `app-render.ts`:

```typescript
import { renderChatControls, renderTab, renderThemeToggle, renderOperationsGroup } from "./app-render.helpers.ts";
```

Then in the nav template, add `${renderOperationsGroup()}` after the last tab group block.

**Step 3: Verify in browser**

```bash
cd openclaw/ui && pnpm dev
```

Visit `http://localhost:5173`. The sidebar should show a new "operations" section with six entries: Mission Control, Tasks, Metrics, Memory, Topology, Agents. Clicking any should navigate the browser to the dashboard (which must be running on port 6987 to respond, but the link itself should work regardless).

**Step 4: Commit**

```bash
git add openclaw/ui/src/ui/app-render.helpers.ts openclaw/ui/src/ui/app-render.ts
git commit -m "feat(ui): add renderExternalNavItem and Operations nav group for /occc/* links"
```

---

## Task 6: Dev proxy script

**Files:**
- Create: `scripts/dev-proxy.js`

The proxy needs the `http-proxy` npm package. Check if it exists in the workspace root:

```bash
ls node_modules/http-proxy 2>/dev/null || echo "not found"
```

If not found, install it at workspace root (or under a new `scripts/package.json` if the workspace doesn't allow root deps):

```bash
# At repo root
npm install --save-dev http-proxy
# or if using pnpm:
pnpm add -D http-proxy -w
```

**Step 1: Write a test for the routing logic**

The proxy routing decision is pure logic — extract it so it can be tested:

```javascript
// scripts/dev-proxy.test.js (or .ts)
import { describe, it, expect } from 'vitest';
import { shouldRouteToDashboard } from './dev-proxy.js';

describe('shouldRouteToDashboard', () => {
  it('routes /occc paths to dashboard', () => {
    expect(shouldRouteToDashboard('/occc/mission-control')).toBe(true);
    expect(shouldRouteToDashboard('/occc/api/tasks')).toBe(true);
    expect(shouldRouteToDashboard('/occc')).toBe(true);
    expect(shouldRouteToDashboard('/occc/')).toBe(true);
  });

  it('routes everything else to UI', () => {
    expect(shouldRouteToDashboard('/')).toBe(false);
    expect(shouldRouteToDashboard('/agents')).toBe(false);
    expect(shouldRouteToDashboard('/overview')).toBe(false);
    expect(shouldRouteToDashboard('')).toBe(false);
  });
});
```

Run to confirm failure:

```bash
node --experimental-vm-modules node_modules/.bin/vitest run scripts/dev-proxy.test.js
```

Expected: FAIL with "Cannot find module './dev-proxy.js'"

**Step 2: Write `scripts/dev-proxy.js`**

```javascript
#!/usr/bin/env node
/**
 * Dev proxy for unified shell integration.
 * Routes /occc/* to Next.js dashboard, everything else to Vite UI.
 *
 * Usage:
 *   node scripts/dev-proxy.js
 *
 * Environment variables (all optional, defaults shown):
 *   UI_PORT=5173        Vite dev server port
 *   DASHBOARD_PORT=6987 Next.js dev server port
 *   PROXY_PORT=7000     This proxy's listening port
 */

import http from 'http';
import httpProxy from 'http-proxy';

const UI_PORT        = parseInt(process.env.UI_PORT        || '5173', 10);
const DASHBOARD_PORT = parseInt(process.env.DASHBOARD_PORT || '6987', 10);
const PROXY_PORT     = parseInt(process.env.PROXY_PORT     || '7000', 10);

/**
 * Determines whether a request path should be proxied to the dashboard.
 * Exported for testing.
 */
export function shouldRouteToDashboard(urlPath) {
  return urlPath === '/occc' || urlPath.startsWith('/occc/') || urlPath.startsWith('/occc?');
}

const proxy = httpProxy.createProxyServer({});

// Suppress unhandled proxy errors (upstream not ready yet)
proxy.on('error', (err, req, res) => {
  console.error(`[proxy] error for ${req.url}:`, err.message);
  if (res && !res.headersSent) {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('Upstream unavailable — is the dev server running?');
  }
});

const server = http.createServer((req, res) => {
  if (shouldRouteToDashboard(req.url || '')) {
    proxy.web(req, res, {
      target: `http://localhost:${DASHBOARD_PORT}`,
      // No buffer — required for SSE/streaming to pass through correctly
      buffer: undefined,
      timeout: 0,
    });
  } else {
    proxy.web(req, res, {
      target: `http://localhost:${UI_PORT}`,
    });
  }
});

// Forward WebSocket upgrades (needed for Vite HMR)
server.on('upgrade', (req, socket, head) => {
  if (shouldRouteToDashboard(req.url || '')) {
    proxy.ws(req, socket, head, { target: `http://localhost:${DASHBOARD_PORT}` });
  } else {
    proxy.ws(req, socket, head, { target: `http://localhost:${UI_PORT}` });
  }
});

server.listen(PROXY_PORT, () => {
  console.log(`[dev-proxy] listening on http://localhost:${PROXY_PORT}`);
  console.log(`[dev-proxy] /       → http://localhost:${UI_PORT}  (openclaw/ui)`);
  console.log(`[dev-proxy] /occc/* → http://localhost:${DASHBOARD_PORT}  (dashboard)`);
});
```

**Step 3: Run the routing test to confirm it passes**

```bash
node --experimental-vm-modules node_modules/.bin/vitest run scripts/dev-proxy.test.js
```

Expected: all tests PASS.

**Step 4: Smoke test the proxy manually**

In three separate terminals:

```bash
# Terminal 1
cd openclaw/ui && pnpm dev

# Terminal 2
cd packages/dashboard && pnpm dev

# Terminal 3
node scripts/dev-proxy.js
```

Then:
- `curl -I http://localhost:7000/` — should get a response from Vite (HTML)
- `curl -I http://localhost:7000/occc/mission-control` — should get a response from Next.js (HTML or redirect)
- `curl -I http://localhost:7000/occc/api/health` — should get `200` from dashboard health route

**Step 5: Commit**

```bash
git add scripts/dev-proxy.js scripts/dev-proxy.test.js
git commit -m "feat: add dev proxy for unified shell (port 7000)"
```

---

## Task 7: Makefile target and nginx config

**Files:**
- Modify: `Makefile`
- Create: `config/nginx/occc.conf`

**Step 1: Add `dev-proxy` target to Makefile**

Find the `.PHONY` line at the top of `Makefile` and add `dev-proxy`. Then add the target after the existing `dashboard` target:

```makefile
dev-proxy: ## Start unified dev proxy at :7000 (runs UI, dashboard, and proxy together)
	@echo "Starting unified dev environment at http://localhost:7000"
	@echo "  openclaw/ui    → :5173"
	@echo "  dashboard      → :6987"
	@echo "  proxy          → :7000"
	@export OPENCLAW_ROOT="$(CURDIR)"; \
	cd openclaw/ui && pnpm dev & \
	cd packages/dashboard && pnpm dev & \
	node scripts/dev-proxy.js
```

**Step 2: Create `config/nginx/occc.conf`**

```bash
mkdir -p config/nginx
```

```nginx
# config/nginx/occc.conf
# Unified shell proxy for OpenClaw operator UI.
#
# Routes:
#   /       → openclaw/ui  (Vite build or preview, port 5173)
#   /occc/* → Next.js dashboard (port 6987)
#
# SSE/streaming: buffering is disabled for /occc/ to support real-time feeds.
# No path rewriting — /occc prefix is preserved end-to-end (matches basePath: '/occc').

server {
    listen 7000;

    location /occc/ {
        proxy_pass              http://127.0.0.1:6987;
        proxy_set_header        Host                    $host;
        proxy_set_header        X-Forwarded-For         $proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Host        $host;
        proxy_set_header        X-Forwarded-Proto       $scheme;

        # SSE / streaming — must not buffer
        proxy_buffering         off;
        proxy_cache             off;
        proxy_read_timeout      3600s;
    }

    location / {
        proxy_pass              http://127.0.0.1:5173;
        proxy_set_header        Host                    $host;
        proxy_set_header        X-Forwarded-For         $proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Host        $host;
        proxy_set_header        X-Forwarded-Proto       $scheme;

        # WebSocket (Vite HMR in dev, or if serving a built app with WS)
        proxy_http_version      1.1;
        proxy_set_header        Upgrade                 $http_upgrade;
        proxy_set_header        Connection              "upgrade";
    }
}
```

**Step 3: Commit**

```bash
git add Makefile config/nginx/occc.conf
git commit -m "feat: add make dev-proxy target and nginx occc.conf for unified shell"
```

---

## Task 8: Validation checklist

Run through each item manually after all tasks are complete. Both servers must be running via `make dev-proxy` (or the three-terminal method from Task 6).

### Routing

- [ ] `http://localhost:7000/` loads openclaw/ui (Lit shell, nav visible)
- [ ] `http://localhost:7000/occc` redirects to `http://localhost:7000/occc/mission-control`
- [ ] `http://localhost:7000/occc/mission-control` loads dashboard mission-control page
- [ ] `http://localhost:7000/occc/tasks` loads dashboard tasks page
- [ ] All six OCCC_NAV entries in openclaw/ui sidebar navigate correctly

### OcccShell chrome

- [ ] Dashboard pages show 48px top bar (no sidebar, no standalone header)
- [ ] "← OpenClaw" link navigates back to `http://localhost:7000/`
- [ ] Breadcrumb shows correct section label (e.g. "Memory" when on `/occc/memory`)
- [ ] Subroute breadcrumb resolves correctly (e.g. `/occc/memory/health` shows "Memory")

### API routes

- [ ] `http://localhost:7000/occc/api/health` returns `200`
- [ ] Dashboard pages load data correctly (no 404 or CORS errors in browser console)

### SSE/streaming

- [ ] If the dashboard has SSE feeds (e.g. `/occc/api/swarm/stream`), open the mission-control page and confirm no console errors related to streaming

### Auth

- [ ] If `OPENCLAW_GATEWAY_TOKEN` is set in `.env.local`, confirm dashboard API routes still reject requests without the token
- [ ] Confirm no cross-origin cookie errors in browser console

### Asset paths

- [ ] Dashboard static assets (`/_next/static/...`) load correctly via the proxy
- [ ] No broken images or 404 asset errors in browser devtools Network tab

---

## Task 9: Cleanup (after validation)

Only do this task after Task 8 passes fully.

**Files:**
- The `Sidebar` and `Header` components can be deleted if no other code imports them.

**Step 1: Check for remaining imports**

```bash
grep -r "from.*layout/Sidebar\|from.*layout/Header" packages/dashboard/src/ --include="*.tsx" --include="*.ts"
```

If the only reference was `layout.tsx` (which we already changed), both components are safe to delete.

**Step 2: Delete the components**

```bash
rm packages/dashboard/src/components/layout/Sidebar.tsx
rm packages/dashboard/src/components/layout/Header.tsx
```

**Step 3: Verify the build still passes**

```bash
cd packages/dashboard && pnpm build 2>&1 | tail -10
```

Expected: build succeeds.

**Step 4: Commit**

```bash
git add -A
git commit -m "chore(dashboard): remove Sidebar and Header (replaced by OcccShell)"
```
