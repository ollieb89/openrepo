---
name: tailwind-v4-shadcn
description: Use when installing, configuring, or extending Tailwind CSS v4 with shadcn/ui — covers Turborepo monorepo shared-package architecture, CSS config format (breaking changes from v3), components.json requirements, and correct class/token usage patterns
---

# shadcn/ui with Tailwind CSS v4

## Overview

shadcn/ui fully supports Tailwind v4 and React 19. The CSS-variable system changed significantly — `@theme inline` replaces `tailwind.config.js`, colors are OKLCH, and several utilities were updated.

In a **Turborepo monorepo**, styles and components live in shared packages consumed by all apps.

---

## Turborepo Monorepo Architecture

Two packages work together:

| Package | Purpose |
|---------|---------|
| `packages/tailwind-config` | Shared PostCSS plugin config + base brand tokens |
| `packages/ui` | shadcn components + full `@theme inline` CSS |

Apps **never duplicate** PostCSS config or CSS tokens — they import from these packages.

### `packages/tailwind-config`

Exports a reusable PostCSS config and optional base brand tokens.

**`packages/tailwind-config/package.json`**
```json
{
  "name": "@pumplai/tw-config",
  "type": "module",
  "exports": {
    ".": "./shared-styles.css",
    "./postcss": "./postcss.config.js"
  },
  "devDependencies": {
    "@tailwindcss/postcss": "^4.x",
    "postcss": "^8.x",
    "tailwindcss": "^4.x"
  }
}
```

**`packages/tailwind-config/postcss.config.js`**
```js
export const postcssConfig = {
  plugins: { "@tailwindcss/postcss": {} },
};
```

**`packages/tailwind-config/shared-styles.css`** — brand tokens only (no shadcn tokens here):
```css
@import "tailwindcss";

@theme {
  --color-brand-50: oklch(0.97 0.02 270);
  --color-brand-500: oklch(0.55 0.22 270);
  --color-brand-600: oklch(0.47 0.22 270);
  --font-sans: "Inter", sans-serif;
  --font-mono: "JetBrains Mono", monospace;
}
```

### `packages/ui` (shadcn components)

This is where shadcn components and their CSS live. The `globals.css` here is the single source of truth for all design tokens.

**`packages/ui/components.json`**
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": { "config": "", "css": "src/styles/globals.css", "baseColor": "zinc", "cssVariables": true },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@pumplai/ui/components",
    "utils": "@pumplai/ui/lib/utils",
    "hooks": "@pumplai/ui/hooks",
    "lib": "@pumplai/ui/lib",
    "ui": "@pumplai/ui/components"
  }
}
```

**`packages/ui/src/styles/globals.css`** — full shadcn token setup:
```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  /* ... chart-1..5, sidebar tokens */
}

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --border: oklch(0.922 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  /* full token list here */
}

.dark { /* dark mode tokens */ }

@layer base {
  * { @apply border-border outline-ring/50; }
  body { @apply bg-background text-foreground; }
}
```

**`packages/ui/package.json`** exports:
```json
{
  "exports": {
    "./styles.css": "./dist/index.css",
    "./*": "./dist/*.js"
  },
  "scripts": {
    "build:styles": "tailwindcss -i ./src/styles.css -o ./dist/index.css",
    "build:components": "tsc"
  },
  "dependencies": {
    "tw-animate-css": "^1.x",
    "class-variance-authority": "^0.7.x",
    "clsx": "^2.x",
    "tailwind-merge": "^2.x"
  }
}
```

### App Setup

Each app needs:
1. A `postcss.config.mjs` referencing the shared config
2. Its own `components.json` pointing aliases into `packages/ui`
3. A `globals.css` that imports from `packages/ui` (or imports tailwind + brand tokens separately)

**`apps/web/postcss.config.mjs`**
```js
import { postcssConfig } from "@pumplai/tw-config/postcss";
export default postcssConfig;
```

**`apps/web/components.json`** — must point CSS to `packages/ui`'s globals:
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "../../packages/ui/src/styles/globals.css",
    "baseColor": "zinc",
    "cssVariables": true
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "hooks": "@/hooks",
    "lib": "@/lib",
    "utils": "@pumplai/ui/lib/utils",
    "ui": "@pumplai/ui/components"
  }
}
```

**`apps/web/styles/globals.css`** — import tailwind + brand tokens; shadcn tokens come from the ui package styles:
```css
@import "tailwindcss";

@theme {
  --color-brand-50: oklch(0.97 0.02 270);
  --color-brand-500: oklch(0.55 0.22 270);
  --font-sans: "Inter", sans-serif;
}

body {
  font-family: var(--font-sans);
  @apply bg-background text-foreground antialiased;
}
```

Import the shared ui styles in the root layout:
```tsx
// apps/web/app/layout.tsx
import "@pumplai/ui/styles.css"  // shadcn tokens + component styles
import "../styles/globals.css"   // app-specific brand overrides
```

### Adding Components (Monorepo CLI)

**Always run shadcn CLI from the app directory**, not the repo root. The CLI detects the monorepo structure and routes components to `packages/ui` automatically.

```bash
cd apps/web
pnpm dlx shadcn@latest add button
# → installs component to packages/ui/src/components/button.tsx
# → updates import paths for apps/web automatically
```

### Importing Components in Apps

```tsx
// From the shared ui package (not @/components/ui/)
import { Button } from "@pumplai/ui/components/button"
import { cn } from "@pumplai/ui/lib/utils"
import { useTheme } from "@pumplai/ui/hooks/use-theme"
```

### Turbo Pipeline for Styles

`packages/ui` must build styles before apps build:

```json
// turbo.json
{
  "tasks": {
    "build": { "dependsOn": ["^build"], "outputs": [".next/**", "dist/**"] },
    "build:styles": { "outputs": ["dist/index.css"] }
  }
}
```

---

## Single-App CSS Configuration

For apps **not** using the shared ui package, configure CSS directly:

```css
@import "tailwindcss";
@import "tw-animate-css";

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --radius: 0.5rem;
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --radius-sm: calc(var(--radius) - 2px);
  --radius-md: var(--radius);
  --radius-lg: calc(var(--radius) + 2px);
}
```

**Key rule:** CSS variable definitions go **outside** `@layer base` in v4.

---

## Breaking Changes vs v3

| v3 | v4 |
|----|----|
| `tailwindcss-animate` | `tw-animate-css` |
| `tailwind.config.js` theme | `@theme inline` in CSS |
| `hsl(var(--color))` in chart | `var(--color)` directly |
| `w-4 h-4` | `size-4` |
| `React.forwardRef` in components | `React.ComponentProps<>` + `data-slot` |
| "default" style | "new-york" style |
| `<Toast>` component | `sonner` toast library |

---

## Component Patterns

### Button
```tsx
import { Button } from "@pumplai/ui/components/button"

<Button variant="default">Save</Button>
<Button variant="outline" size="sm">Cancel</Button>
<Button variant="destructive">Delete</Button>
// variants: default | destructive | outline | secondary | ghost | link
// sizes: default | sm | lg | icon
```

### Form with React Hook Form
```tsx
// ❌ Spreading fields passes null — breaks inputs
<Input {...field} />

// ✅ Destructure manually
const { value, onChange, onBlur, ref } = field
<Input value={value ?? ""} onChange={onChange} onBlur={onBlur} ref={ref} />
```

### Select — avoid empty string values
```tsx
// ❌ Radix Select rejects "" as value
<SelectItem value="">Any</SelectItem>

// ✅ Use sentinel value
<SelectItem value="__any__">Any</SelectItem>
// Then in handler: value === "__any__" ? null : value
```

### Dialog width
```tsx
// ❌ width override ignored
<DialogContent className="max-w-2xl">

// ✅ Must use sm: breakpoint prefix
<DialogContent className="sm:max-w-2xl">
```

### Sonner toast (replaces Toast component)
```tsx
import { toast } from "sonner"
import { Toaster } from "@pumplai/ui/components/sonner"  // add to layout

toast.success("Saved!")
toast.error("Failed to save")
toast.promise(saveData(), { loading: "Saving...", success: "Done!", error: "Failed" })
```

### Lucide icons — no dynamic imports
```tsx
// ❌ Dynamic import breaks in production
const Icon = dynamic(() => import("lucide-react").then(m => m[iconName]))

// ✅ Explicit static map
import { Plus, Trash, Edit } from "lucide-react"
const icons = { plus: Plus, trash: Trash, edit: Edit }
const Icon = icons[iconName]
```

---

## Semantic Token Usage

Always use semantic CSS tokens, never raw Tailwind colors:

```tsx
// ❌ Raw color — breaks dark mode and theming
<div className="bg-gray-100 text-gray-900">

// ✅ Semantic token
<div className="bg-muted text-muted-foreground">
<div className="bg-background text-foreground">
<div className="bg-primary text-primary-foreground">
```

## Component Sizing (v4 utility)

```tsx
// ❌ Old pattern
<div className="w-4 h-4">

// ✅ New size-* utility
<div className="size-4">
```

## Extending Component Variants

Edit component files directly in `packages/ui/src/components/`. Use `cva`:

```tsx
// packages/ui/src/components/button.tsx
const buttonVariants = cva("...", {
  variants: {
    variant: {
      default: "bg-primary text-primary-foreground ...",
      brand: "bg-brand-500 text-white hover:bg-brand-600",
    },
  },
})
```

---

## Quick Reference — Install Commands

```bash
# Run from app directory (CLI auto-routes to packages/ui in monorepo)
cd apps/web

# Foundation
pnpm dlx shadcn@latest add button input label card separator

# Forms
pnpm dlx shadcn@latest add form select checkbox textarea switch
pnpm add react-hook-form zod @hookform/resolvers

# Feedback
pnpm dlx shadcn@latest add sonner && pnpm add sonner

# Overlays
pnpm dlx shadcn@latest add dialog sheet

# Data display
pnpm dlx shadcn@latest add table tabs badge avatar dropdown-menu

# Navigation
pnpm dlx shadcn@latest add navigation-menu breadcrumb

# Advanced table
pnpm add @tanstack/react-table
```

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running `shadcn add` from repo root in monorepo | Run from `apps/<name>` directory |
| Importing from `@/components/ui/*` in monorepo | Import from `@pumplai/ui/components/*` |
| Each app has its own shadcn CSS tokens | Tokens live only in `packages/ui/src/styles/globals.css` |
| App `components.json` missing `utils` alias to ui package | Add `"utils": "@pumplai/ui/lib/utils"` |
| `tailwindcss-animate` | Switch to `tw-animate-css` |
| Defining CSS vars inside `@layer base` | Move them outside — they're raw custom properties, not utilities |
| `hsl(var(--chart-1))` in chart configs | Use `var(--chart-1)` directly |
| Using raw Tailwind colors (`bg-gray-*`) | Use semantic tokens (`bg-muted`) |
| Spreading react-hook-form field to Input | Destructure `{ value, onChange, onBlur, ref }` |
| Empty string in Radix Select | Use `"__any__"` sentinel |
| Dynamic Lucide icon import | Use explicit static map |
| Dialog width without `sm:` prefix | Add `sm:` prefix to `max-w-*` |
| App PostCSS duplicates `@tailwindcss/postcss` config | Import `postcssConfig` from `@pumplai/tw-config/postcss` |
