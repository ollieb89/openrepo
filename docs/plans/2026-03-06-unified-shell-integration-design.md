# Unified Shell Integration Design

**Date:** 2026-03-06
**Status:** Approved
**Scope:** `openclaw/ui` + `packages/dashboard`

---

## Goal

One coherent operator experience where config, agents, status, and runtime controls live in the same product flow, without users context-switching between two separate UIs.

- **Primary:** unified UX/navigation
- **Secondary:** shared auth/session (deferred — see Section 6)
- **Tertiary:** unified deployment (falls out naturally via proxy)
- **Not a v1 goal:** eliminating Next.js

---

## Section 1 — Architecture & Routing

```
Browser
  │
  ▼
Reverse proxy  (single origin — e.g. localhost:7000)
  ├── /           → openclaw/ui   (Vite dev :5173 or built static)
  └── /occc/*     → Next.js dashboard  (port 6987)
         └── /occc/api/*  →  dashboard API routes (pass-through)
```

`openclaw/ui` is the entry point and primary shell. The dashboard is mounted as a subsection at `/occc`. All browser traffic goes through one origin — no CORS, shared cookies, shared auth surface.

### Base path rule

`next.config.js` is configured with `basePath: '/occc'`. Next.js believes it lives at `/occc` end-to-end. The proxy forwards `/occc/*` traffic to the Next.js process **without stripping the prefix**. Next.js generates asset URLs, `<Link href>` values, API calls, and redirects under `/occc`.

Do **not** treat the basePath as "conceptually stripped at the proxy" — it is real and flows end-to-end.

### Routing split (locked in)

| Path pattern | Destination |
|---|---|
| `/` | openclaw/ui (Vite) |
| `/occc/*` | Next.js dashboard |
| `/occc/api/*` | dashboard API routes (Next.js, pass-through) |
| `/occc` (exact) | redirect to `/occc/mission-control` |

### Watchpoints

- `fetch('/api/...')` calls in dashboard must use `/occc/api/...` or a shared `apiBase` constant
- `router.push('/')` in dashboard is fine via `<Link>` and `useRouter` (basePath-aware); raw `window.location` strings are not
- `<img>` absolute paths are not affected by basePath; must use relative paths or Next.js `<Image>`
- Auth callbacks and redirects must use `request.nextUrl.clone()` in middleware (see Section 6)
- **SSE/streaming** — proxy must pass through without buffering; both dev and prod proxy must handle this correctly

---

## Section 2 — Chrome Ownership on `/occc/*`

When a user navigates to `/occc/*` it is a full-page navigation — `openclaw/ui`'s DOM is gone. The proxy does not inject HTML.

**The dashboard owns its own chrome on `/occc/*` pages, under an explicit shared contract.**

### `OcccShell` — the embedded layout component

Every user-facing `/occc/*` page is wrapped by a new `OcccShell` component. It replaces the existing `Sidebar` + `Header` for embedded pages.

```
+-----------------------------------------------------------+
| <- OpenClaw   /   Mission Control         [section tabs]  |  <- 48px top bar
+-----------------------------------------------------------+
|                                                           |
|   page content                                            |
|                                                           |
+-----------------------------------------------------------+
```

- **"← OpenClaw"** links to `/` — primary escape hatch back to the shell
- **Breadcrumb** shows the current section name (resolved from `OCCC_ROUTE_META`)
- **Section tabs** — optional, per-page only (e.g. Memory has Table / Health / Settings tabs)
- **No sidebar** — the full `Sidebar` is removed from the embedded layout
- **No duplicate global nav** — `openclaw/ui`'s nav entries cover top-level routing

`OcccShell` adopts `openclaw/ui`'s visual language (same font stack, same neutral palette, same spacing scale) through a shared design contract, not shared code.

---

## Section 3 — `openclaw/ui` Nav Additions

### New type: `OcccNavItem`

Added to `openclaw/ui/src/ui/navigation.ts`:

```ts
export type OcccNavItem = {
  key: string;       // canonical key — matches OCCC_ROUTE_META keys in dashboard
  label: string;     // display label in nav and breadcrumb
  icon: IconName;
  href: string;      // full path e.g. "/occc/mission-control"
  match?: string[];  // optional subroute patterns for future breadcrumb resolution
                     // e.g. ["/occc/memory/health"] — not used by openclaw/ui v1
};
```

### `OCCC_NAV` — canonical nav metadata

```ts
export const OCCC_NAV: OcccNavItem[] = [
  { key: "mission-control", label: "Mission Control", icon: "radio",    href: "/occc/mission-control" },
  { key: "tasks",           label: "Tasks",           icon: "fileText", href: "/occc/tasks" },
  { key: "metrics",         label: "Metrics",         icon: "barChart", href: "/occc/metrics" },
  { key: "memory",          label: "Memory",          icon: "brain",    href: "/occc/memory" },
  { key: "topology",        label: "Topology",        icon: "monitor",  href: "/occc/topology" },
  { key: "agents",          label: "Agents",          icon: "folder",   href: "/occc/agents" },
];
```

### New render function: `renderExternalNavItem`

Added to `openclaw/ui/src/ui/app-render.helpers.ts`. Plain `<a href>` — no `@click` override, no SPA routing interception, identical visual styling to `renderTab()` items:

```ts
export function renderExternalNavItem(item: OcccNavItem) {
  return html`
    <a href=${item.href} class="nav-item" title=${item.label}>
      <span class="nav-item__icon" aria-hidden="true">${icons[item.icon]}</span>
      <span class="nav-item__text">${item.label}</span>
    </a>
  `;
}
```

An "operations" nav group is added in `app-render.ts` after the existing tab groups, rendered with `renderExternalNavItem`.

### What does NOT change

- `Tab` union type — not extended
- `TAB_GROUPS` — not modified
- `pathForTab`, `tabFromPath`, `inferBasePathFromPathname` — untouched
- Internal SPA routing logic — untouched

### Why `OCCC_NAV` is separate from `TAB_GROUPS`

`Tab` represents internal SPA state owned by `openclaw/ui`. OCCC links are cross-surface navigations to a different app section under the same origin. Merging them would require conditionals throughout the nav model. The separation keeps the boundary clean and the integration reversible.

---

## Section 4 — Dashboard Changes

### 4a — `next.config.js`

```js
basePath: '/occc',
```

One-line addition. All Next.js routing, asset URLs, API calls, and redirects will use `/occc` as the base. See Section 1 watchpoints for areas to audit.

### 4b — `OCCC_ROUTE_META` — shared canonical label source

New file `packages/dashboard/src/lib/occc-routes.ts`:

```ts
export const OCCC_ROUTE_META: Record<string, { label: string }> = {
  "mission-control": { label: "Mission Control" },
  "tasks":           { label: "Tasks" },
  "metrics":         { label: "Metrics" },
  "memory":          { label: "Memory" },
  "topology":        { label: "Topology" },
  "agents":          { label: "Agents" },
};
```

Keys are identical to `OCCC_NAV` keys in `openclaw/ui`. This is the single source of truth for section labels on the dashboard side. `OcccShell` reads the current pathname segment to look up the label. Subroutes like `/occc/memory/health` resolve to the `"memory"` label via segment matching.

### 4c — `OcccShell` component

New file `packages/dashboard/src/components/layout/OcccShell.tsx`. Reads the current pathname, resolves the section label from `OCCC_ROUTE_META`, and renders the 48px top bar described in Section 2.

### 4d — Root layout update

`packages/dashboard/src/app/layout.tsx` is updated to use `OcccShell` instead of `Sidebar` + `Header`. The existing `Sidebar` and `Header` components are **retained** in the codebase but no longer used by the root layout — they are removed in a follow-up cleanup once integration is validated.

### 4e — `/occc` redirect

`packages/dashboard/src/app/page.tsx` (the root, now at `/occc` due to basePath) redirects to `/occc/mission-control`.

---

## Section 5 — Proxy Setup

### Dev proxy (`scripts/dev-proxy.js`)

A minimal Node.js script using `http-proxy`. Runs alongside `vite dev` and `next dev`.

Port defaults (all configurable via env vars):

| Variable | Default | Purpose |
|---|---|---|
| `UI_PORT` | `5173` | Vite dev server |
| `DASHBOARD_PORT` | `6987` | Next.js dev server |
| `PROXY_PORT` | `7000` | Unified entrypoint |

Routing:

```
/occc/*  →  http://localhost:${DASHBOARD_PORT}   (path forwarded as-is)
/*       →  http://localhost:${UI_PORT}
```

Requirements:
- SSE/streaming: no response buffering (`timeout: 0`)
- Vite HMR WebSocket: `server.on('upgrade', ...)` handled separately
- Cookies forwarded without modification
- Dev proxy behavior must mirror nginx closely enough that basePath bugs surface in dev

A `Makefile` target `make dev-proxy` starts all three processes.

### Prod nginx (`config/nginx/occc.conf`)

```nginx
server {
  listen 7000;

  location /occc/ {
    proxy_pass              http://127.0.0.1:6987;
    proxy_set_header        Host                    $host;
    proxy_set_header        X-Forwarded-For         $proxy_add_x_forwarded_for;
    proxy_set_header        X-Forwarded-Host        $host;
    proxy_set_header        X-Forwarded-Proto       $scheme;

    # SSE / streaming
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
    proxy_http_version      1.1;
    proxy_set_header        Upgrade                 $http_upgrade;
    proxy_set_header        Connection              "upgrade";
  }
}
```

No path rewriting — `/occc` prefix is preserved end-to-end to match `basePath: '/occc'`.

---

## Section 6 — Auth/Session

### v1 stance: auth is intentionally not unified

> `openclaw/ui` and the dashboard keep their existing auth models. The reverse proxy provides a shared browser origin, which eliminates CORS and simplifies future convergence, but no shared session, SSO, or token exchange is introduced in this phase.

| System | Auth model |
|---|---|
| `openclaw/ui` | Device-based (`device-auth.ts`, `device-identity.ts`) |
| dashboard | Gateway token (`OPENCLAW_GATEWAY_TOKEN` env var) |

### What shared origin provides

- Browser cookies are same-origin — dashboard cookies are scoped to `localhost:7000`, not `localhost:6987`
- No CORS preflight between surfaces
- Shared `localStorage` namespace — **available if explicitly chosen later, but v1 must not depend on cross-app `localStorage` reads for auth behavior** (creates hidden coupling)

### Middleware note

`packages/dashboard/src/middleware.ts` matches `PUBLIC_ROUTES` against stripped paths — Next.js middleware receives paths without the basePath prefix. The strings `/login`, `/api/auth/token`, `/api/health` remain correct in the middleware code.

Any redirect in middleware must use `request.nextUrl.clone()` (basePath-aware) rather than hardcoded path strings like `/login`.

### v2 direction

Proxy-level access control (`OPENCLAW_GATEWAY_TOKEN` enforced at nginx) is a natural v2 outer access gate — it covers "are you allowed into the operator surface at all?" and is not a full auth unification strategy.

---

## Implementation Sequence

1. **`next.config.js`** — add `basePath: '/occc'`; verify dashboard runs clean under the new base
2. **Dev proxy** — write `scripts/dev-proxy.js`; validate routing, streaming, cookies at `localhost:7000`
3. **`OCCC_ROUTE_META` + `OcccShell`** — strip dashboard sidebar/header, add compact embedded shell
4. **`OCCC_NAV` + `renderExternalNavItem`** — add "operations" group to `openclaw/ui` nav
5. **`/occc` redirect** — `packages/dashboard/src/app/page.tsx`
6. **`config/nginx/occc.conf`** — prod nginx config + `make dev-proxy` target
7. **Validation** — verify all Section 1 watchpoints; spot-check SSE, cookies, asset paths, middleware redirects
8. **Cleanup** — remove `Sidebar` and `Header` from dashboard once integration is stable
