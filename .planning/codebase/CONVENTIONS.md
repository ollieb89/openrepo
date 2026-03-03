# Coding Conventions

**Analysis Date:** 2025-02-21

## Naming Patterns

**Files:**
- TypeScript source files: `[name].ts` or `[name].tsx`
- Unit tests: `[name].test.ts` (co-located with source)
- End-to-end tests: `[name].e2e.test.ts`
- Live environment tests: `[name].live.test.ts`
- Python source files: `[name].py`
- Python tests: `test_[name].py`

**Functions:**
- TypeScript: `camelCase`
- Python: `snake_case`

**Variables:**
- TypeScript: `camelCase`
- Python: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

**Types:**
- TypeScript interfaces/types: `PascalCase`

## Code Style

**Formatting:**
- Tool: `oxfmt` (configured in `openclaw/.oxfmtrc.jsonc`)
- Command: `pnpm format` runs `oxfmt --write`
- Key settings: `experimentalSortImports: { newlinesBetween: false }`

**Linting:**
- Tool: `oxlint` (configured in `openclaw/.oxlintrc.json`)
- Command: `pnpm lint` runs `oxlint --type-aware`
- Rules:
  - `correctness`: error
  - `perf`: error
  - `suspicious`: error
  - `typescript/no-explicit-any`: error
  - `curly`: error

## Import Organization

**Order:**
- Handled automatically by `oxfmt` with `experimentalSortImports`.

**Path Aliases:**
- `openclaw/plugin-sdk`: Mapped to `src/plugin-sdk/index.ts`
- `openclaw/plugin-sdk/account-id`: Mapped to `src/plugin-sdk/account-id.ts`
- Configuration in `openclaw/vitest.config.ts` and `openclaw/tsconfig.json`.

## Error Handling

**Patterns:**
- Standard TypeScript `try/catch` blocks.
- Extensive use of `expect` assertions in tests.
- Custom error formatting tests found in `test/format-error.test.ts`.

## Logging

**Framework:** `tslog` (detected in `openclaw/package.json`)

**Patterns:**
- Centralized logging logic in `src/logging.ts` (though excluded from unit test coverage).

## Function Design

**Size:**
- Strict limit: Max **500 lines** of code per TypeScript file in `src/`.
- Enforced by `pnpm check:loc` (`scripts/check-ts-max-loc.ts`).

## Module Design

**Exports:**
- Defined in `openclaw/package.json` under `exports`.
- Main entry point: `dist/index.js`.
- Plugin SDK entry point: `dist/plugin-sdk/index.js`.

**Barrel Files:**
- Used for public API surface, e.g., `src/plugin-sdk/index.ts`.

---

*Convention analysis: 2025-02-21*
