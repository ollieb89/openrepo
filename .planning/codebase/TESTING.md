# Testing Patterns

**Analysis Date:** 2025-02-21

## Test Framework

**TypeScript Runner:**
- Vitest (`openclaw/vitest.config.ts`)
- Config Files:
  - `openclaw/vitest.unit.config.ts`: Unit tests
  - `openclaw/vitest.e2e.config.ts`: End-to-end tests
  - `openclaw/vitest.live.config.ts`: Live environment tests
  - `openclaw/vitest.gateway.config.ts`: Gateway specific tests

**Python Runner:**
- Pytest (`pyproject.toml`)
- Config: Root `pyproject.toml` and `packages/orchestration/pyproject.toml`.

**Run Commands:**
```bash
pnpm test              # Run all tests (via scripts/test-parallel.mjs)
pnpm test:fast         # Run unit tests only
pnpm test:e2e          # Run end-to-end tests
pnpm test:live         # Run live tests (requires environment)
pytest tests/e2e       # Run Python E2E tests
```

## Test File Organization

**Location:**
- Unit Tests: Co-located with source (e.g., `openclaw/src/utils/boolean.test.ts`).
- Shared E2E/Integration Tests: `openclaw/test/`.
- Python E2E Tests: `tests/e2e/`.

**Naming:**
- `*.test.ts`: Unit/Integration
- `*.e2e.test.ts`: End-to-end
- `*.live.test.ts`: Live environment
- `test_*.py`: Python tests

## Test Structure

**Suite Organization:**
```typescript
import { describe, expect, it } from "vitest";
import { myFunction } from "./myFile.js";

describe("myFunction", () => {
  it("should perform action", () => {
    expect(myFunction()).toBe(true);
  });
});
```

**Patterns:**
- `pool: "forks"` used for parallelization in Vitest.
- `unstubEnvs: true` and `unstubGlobals: true` in `vitest.config.ts` to avoid cross-test pollution.

## Mocking

**Framework:** Vitest Built-in (`vi`)

**Patterns:**
```typescript
import { vi } from "vitest";

// Stub environment
vi.stubEnv("MY_VAR", "value");

// Mock module
vi.mock("./myModule.js", () => ({
  myFunction: vi.fn(),
}));
```

**What to Mock:**
- Network calls (using `undici` mocking or `MockLLMClient`).
- Process-level functions like `vi.stubEnv`.
- Native dependencies that are platform-specific (e.g., Baileys/Whiskeysockets).

## Fixtures and Factories

**Test Data:**
- Centralized fixtures in `openclaw/test/fixtures/`.
- Mock implementations in `openclaw/test/mocks/`.

**Python E2E Fixtures:**
- Defined in `tests/e2e/conftest.py`.
- `compose_stack`: Manages Docker Compose environment.
- `mock_llm`: Client for a mock LLM server.
- `autonomy_stack`: High-level fixture for E2E tests.

## Coverage

**Requirements:**
- Thresholds enforced in `vitest.config.ts`:
  - Lines: 70%
  - Functions: 70%
  - Branches: 55%
  - Statements: 70%

**View Coverage:**
```bash
pnpm test:coverage
```

## Test Types

**Unit Tests:**
- Fast, co-located with code. `src/**/*.test.ts`.

**Integration Tests:**
- Found in `openclaw/test/` and some `src/**/*.test.ts`.

**E2E Tests:**
- Docker-based tests in `tests/e2e/`.
- Framework: `testcontainers` and `Docker Compose` via Python `subprocess`.

## Common Patterns

**Async Testing:**
- Standard `async/await` in both Vitest and Pytest (using `pytest-asyncio`).

**Error Testing:**
- `expect(() => func()).toThrow()` in Vitest.
- Explicit error handling tests in `openclaw/test/format-error.test.ts`.

---

*Testing analysis: 2025-02-21*
