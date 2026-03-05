# Repository Guidelines for Agentic Coding

This file provides guidance for AI agents operating in this repository.

## Project Overview

This is a monorepo containing:
- **openclaw/** - Main TypeScript/Node.js application (AI gateway with messaging integrations)
- **packages/orchestration/** - Python orchestration engine
- **packages/dashboard/** - Next.js dashboard (React/TypeScript)
- **skills/** - L1/L2/L3 agent skills and routing
- **extensions/** - Channel plugins (Discord, Telegram, WhatsApp, etc.)
- **docker/** - Container definitions

## Build, Test, and Development Commands

### Node.js/TypeScript (openclaw, dashboard)

```bash
# Install dependencies
pnpm install

# Build & Type check
pnpm build                          # Full build
pnpm tsgo                          # TypeScript strict check

# Linting & Formatting
pnpm check                         # format:check + tsgo + lint
pnpm lint                          # oxlint (type-aware)
pnpm lint:fix                      # oxlint --fix + format
pnpm format                        # oxfmt (write)
pnpm format:check                  # oxfmt (check only)

# Testing (Vitest)
pnpm test                          # All unit tests
pnpm test:fast                    # Unit tests only
pnpm test:watch                   # Watch mode
pnpm test:e2e                     # End-to-end tests
pnpm test:live                    # Live tests (requires API keys)
pnpm test:coverage                # With coverage report
```

**Running a Single Test:**
```bash
vitest run src/utils/usage-format.test.ts
vitest run --config vitest.unit.config.ts src/my/test/file.test.ts
vitest run -t "test name pattern"
```

### Python (orchestration package)

```bash
uv sync                            # Install dependencies
uv run pyright packages/orchestration/  # Type check
uv run ruff check packages/orchestration/ # Lint
uv run ruff format packages/orchestration/ # Format
pytest                             # Run tests
pytest -k "test_name"             # Single test by pattern
```

### Docker Commands

```bash
docker build -t openclaw-l3-specialist:latest docker/l3-specialist/
pnpm test:docker:live-models
pnpm test:docker:live-gateway
```

## Code Style Guidelines

### General Principles

- **Language**: TypeScript (ESM) for JS/TS; Python for orchestration
- **Strict typing**: Avoid `any`; prefer explicit types
- **File size**: Keep files under ~500-700 LOC; split when needed
- **Comments**: Add brief comments for tricky/non-obvious logic only

### TypeScript Conventions

```typescript
// Imports: external > internal > relative
import { ExternalLib } from 'external-lib';
import { InternalModule } from '@/internal/module';
import { helper } from './helpers';

// Naming
- Functions/variables: camelCase
- Classes/Types/Interfaces: PascalCase
- Constants: SCREAMING_SNAKE_CASE
- Files: kebab-case.ts or PascalCase.tsx

// Interfaces vs Types
interface UserConfig {       // Objects with optional fields
  name: string;
  age?: number;
}
type UserStatus = 'active' | 'inactive';  // Unions, primitives

// Error handling
try {
  await riskyOperation();
} catch (err) {
  if (err instanceof SpecificError) {
    handleSpecific(err);
  } else {
    throw new AppError('Context', { cause: err });
  }
}

// Async functions - handle errors
async function fetchData(): Promise<Result> {
  try {
    const data = await externalCall();
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}
```

### Python Conventions (orchestration/)

```python
# Imports: stdlib > third-party > local
import os
from typing import Optional

import aiohttp
from loguru import logger

from orchestration.state import StateEngine

# Naming: snake_case (functions/variables), PascalCase (classes)
# Type hints: def process(items: list[str]) -> dict[str, int]:

# Error handling
try:
    result = await fetch_data()
except DataError as e:
    logger.error(f"Failed to fetch: {e}")
    raise
```

### React/Next.js (dashboard)

```tsx
import { useState, useEffect } from 'react';
import { Button } from '@/components/common';

interface Props {
  title: string;
  onSubmit: () => void;
}

export function TaskBoard({ title, onSubmit }: Props) {
  const [tasks, setTasks] = useState<Task[]>([]);
  return <div><h1>{title}</h1></div>;
}

// Hooks: useX naming
export function useTasks() { /* ... */ }
```

### Configuration Files (JSON)

- Keys: lower_snake_case
- Preserve existing ordering for diff readability
- Validate: `python -m json.tool <file>`

## Testing Guidelines

- Colocate tests: `src/utils/foo.ts` → `src/utils/foo.test.ts`
- E2E tests: `*.e2e.test.ts`
- Coverage threshold: 70% lines/branches/functions/statements
- Live tests: `CLAWDBOT_LIVE_TEST=1 pnpm test:live`

## Git & Commit Guidelines

- Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`
- Create commits: `scripts/committer "message" file1.ts file2.ts`

## Multi-Agent Safety

- Do NOT create/apply/drop git stash entries unless requested
- Do NOT create/remove git worktrees unless requested
- Do NOT switch branches unless requested
- Focus on your changes; don't touch unrelated WIP

## Security Guidelines

- Never commit secrets, credentials, or keys
- Use environment variables for sensitive values
- Keep `openclaw.json` trust paths minimal

## Troubleshooting

- Missing deps: `pnpm install` or `uv sync`
- Type errors: `pnpm tsgo` or `uv run pyright`
- Lint errors: `pnpm check`
- Config JSON: `python -m json.tool <file>`
